"""TI 时序 CNN 的布局、符号、融合和训练/重载接口回归。"""
from contextlib import redirect_stdout
from copy import deepcopy
from dataclasses import asdict
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import torch
from torch import nn

from ndp_tcn.model import (ResidualConfig, TiNpuConfig, build_model,
                           load_model_config, model_source)
from ndp_tcn.predict import ResidualPredictor
from ndp_tcn.ti_npu_model import TiNpuTemporalNet, pack_input_tensor
from ndp_tcn.train import parser, train
from test_ndp_data import make_case


class TiNpuModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)

    def test_packing_preserves_time_channels_and_adds_normalized_zeros(self):
        windows = torch.arange(2*8*9, dtype=torch.float32).reshape(2, 8, 9)
        windows.requires_grad_()
        packed = pack_input_tensor(windows)
        self.assertEqual(packed.shape, (2, 12, 8, 1))
        self.assertTrue(packed.is_contiguous())
        torch.testing.assert_close(packed[:, :9, :, 0], windows.transpose(1, 2), rtol=0, atol=0)
        self.assertEqual(torch.count_nonzero(packed[:, 9:]).item(), 0)
        packed.sum().backward()
        torch.testing.assert_close(windows.grad, torch.ones_like(windows))
        with self.assertRaises(ValueError):
            pack_input_tensor(torch.zeros(2, 9, 8))

    def test_core_profile_forward_backward_and_signed_output(self):
        config = TiNpuConfig()
        model = build_model(config, backend="ti_npu")
        self.assertIsInstance(model, TiNpuTemporalNet)
        x = torch.randn(1, 8, 9)
        y = model(x)
        self.assertEqual(y.shape, (1, 1))
        y.square().mean().backward()
        self.assertTrue(all(p.grad is not None and torch.isfinite(p.grad).all() for p in model.parameters()))
        convs = [m for m in model.modules() if isinstance(m, nn.Conv2d)]
        self.assertEqual(len(convs), 2)
        self.assertTrue(all(m.groups == 1 and m.kernel_size == (3, 1) and m.padding == (0, 0) for m in convs))
        self.assertFalse(any(isinstance(m, (nn.GELU, nn.Conv1d)) for m in model.modules()))
        model.eval()
        torch.testing.assert_close(model(x), model.core(pack_input_tensor(x)), rtol=0, atol=0)
        with torch.no_grad():
            for parameter in model.parameters():
                parameter.zero_()
            model.core.output.bias.fill_(-2)
        self.assertEqual(float(model(x)[0, 0].detach()), -2)

    def test_conv_bn_fusion_is_eval_only_equivalent_and_reloadable(self):
        config = TiNpuConfig()
        original = TiNpuTemporalNet(config)
        with self.assertRaises(RuntimeError):
            original.structural_reparam()
        for _ in range(3):
            original(torch.randn(3, 8, 9))
        original.eval()
        before = {name: value.clone() for name, value in original.state_dict().items()}
        fused = deepcopy(original).structural_reparam()
        x = torch.randn(4, 8, 9)
        torch.testing.assert_close(fused(x), original(x), rtol=1e-5, atol=1e-6)
        self.assertFalse(any(isinstance(m, nn.BatchNorm2d) for m in fused.modules()))
        fused.structural_reparam()
        restored = build_model(config, backend="ti_npu", merged=True).eval()
        restored.load_state_dict(fused.state_dict(), strict=True)
        torch.testing.assert_close(restored(x), fused(x), rtol=0, atol=0)
        for name, value in original.state_dict().items():
            torch.testing.assert_close(value, before[name], rtol=0, atol=0)

    def test_config_guards_and_original_configuration_compatibility(self):
        for change in ({"d_model": 15}, {"head_hidden": 8}, {"seq_len": 4},
                       {"in_channels": 12}, {"padded_channels": 16},
                       {"num_blocks": True}, {"variant": "baseline"},
                       {"seq_len": 5, "d_model": 4}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                TiNpuConfig(**change)
        original = ResidualConfig(variant="baseline")
        self.assertEqual(load_model_config(asdict(original), "original"), original)
        self.assertEqual(load_model_config(asdict(original), "legacy"), original)
        ti = TiNpuConfig(seq_len=16)
        self.assertEqual(load_model_config(asdict(ti), "ti_npu"), ti)
        self.assertEqual(model_source("ti_npu").name, "ti_npu_model.py")
        self.assertNotEqual(model_source("original"), model_source("ti_npu"))
        self.assertEqual(parser().parse_args([]).backend, "original")

    def test_ti_training_checkpoint_readme_and_predictor_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_case(root/"train.npz", 1)
            make_case(root/"test.npz", 9, offset=20)
            manifest = {"train": ["train.npz"], "val": [], "test": ["test.npz"], "selection_split": "test"}
            split = root/"split.json"
            split.write_text(json.dumps(manifest), encoding="utf-8")
            args = parser().parse_args(["--backend", "ti_npu", "--data-dir", str(root), "--split", str(split),
                "--ti-width", "8", "--ti-blocks", "1", "--epochs", "1", "--batch-size", "3",
                "--threads", "1", "--device", "cpu"])
            with patch("ndp_tcn.outputs.RESULTS_ROOT", root/"results"), redirect_stdout(io.StringIO()):
                checkpoint = train(args)
            self.assertTrue(checkpoint.parent.name.startswith("train_ti_npu_"))
            saved = torch.load(checkpoint, weights_only=True)
            self.assertEqual(saved["model_backend"], "ti_npu")
            self.assertEqual(saved["model_config"]["variant"], "ti_npu")
            self.assertEqual(saved["run"]["model_source_sha256"], hashlib.sha256(model_source("ti_npu").read_bytes()).hexdigest())
            self.assertEqual(saved["scalers"]["fit_case_ids"], [1])
            self.assertTrue(saved["test_used_for_selection"])
            predictor = ResidualPredictor(checkpoint)
            with np.load(root/"test.npz", allow_pickle=False) as case:
                value = predictor.predict(case["X"][0], float(case["source_time_s"][0]))
            self.assertTrue(np.isfinite(value["residual_V_per_s"]))
            readme = (checkpoint.parent/"README_CN.md").read_text(encoding="utf-8")
            self.assertIn("TI 时序 CNN", readme)
            self.assertIn("NCHW", readme)
            self.assertNotIn("FFN 比例", readme)
            self.assertNotIn("patch 大小", readme)


if __name__ == "__main__":
    unittest.main()
