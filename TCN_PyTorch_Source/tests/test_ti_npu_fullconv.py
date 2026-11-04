"""全卷积转换必须保留时序/符号/旧模型兼容，并导出完整四通道图。"""
from contextlib import redirect_stdout
from copy import deepcopy
from dataclasses import asdict
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import torch
from torch import nn

from ndp_tcn.convert_fullconv import convert, parser as conversion_parser
from ndp_tcn.data import FEATURE_NAMES, Scalers
from ndp_tcn.export_onnx import audit_ti_fullconv_operator_profile, export, parser as export_parser
from ndp_tcn.model import build_model, load_model_config, model_source
from ndp_tcn.predict import ResidualPredictor
from ndp_tcn.predict_onnx import OnnxResidualPredictor
from ndp_tcn.ti_npu_fullconv_model import TiNpuFullConvConfig, convert_legacy_model
from ndp_tcn.ti_npu_model import TiNpuConfig, pack_input_tensor
from ndp_tcn.train import parser as train_parser, train
from test_ndp_data import make_case


HAS_ONNX = all(importlib.util.find_spec(n) is not None for n in ("onnx", "onnxruntime", "onnxscript"))


class FullConvModelTests(unittest.TestCase):
    def setUp(self):
        torch.set_num_threads(1)
        torch.manual_seed(2026)

    def test_equivalent_conversion_preserves_channel_time_order_and_signed_output(self):
        source = build_model(TiNpuConfig(), backend="ti_npu").eval()
        # Deliberately unequal channel/time coefficients expose a Flatten-order mistake.
        with torch.no_grad():
            source.core.hidden.weight.copy_(torch.linspace(-.3, .5, 16*64).reshape(16, 64))
            source.core.output.bias.fill_(-2.)
        before = deepcopy(source.state_dict())
        converted = convert_legacy_model(source)
        windows = torch.randn(31, 8, 9)
        with torch.inference_mode():
            old = source(windows)
            actual = converted(windows)
            all_four = converted.core(pack_input_tensor(windows))
        torch.testing.assert_close(old, actual, atol=1e-6, rtol=1e-5)
        self.assertTrue((actual < 0).any())
        self.assertEqual(tuple(all_four.shape), (31, 4, 1, 1))
        for index in range(4):
            torch.testing.assert_close(all_four[:, index, 0, 0], actual[:, 0], rtol=0, atol=0)
        self.assertFalse(any(isinstance(m, (nn.Linear, nn.Flatten)) for m in converted.core.modules()))
        for key, value in before.items():
            torch.testing.assert_close(source.state_dict()[key], value, rtol=0, atol=0)
        fused = deepcopy(converted).eval().structural_reparam()
        torch.testing.assert_close(fused(windows), old, atol=1e-6, rtol=1e-5)

    def test_already_fused_legacy_model_converts(self):
        source = build_model(TiNpuConfig(), backend="ti_npu").eval().structural_reparam()
        converted = convert_legacy_model(source).eval()
        windows = torch.randn(5, 8, 9)
        torch.testing.assert_close(converted(windows), source(windows), atol=1e-6, rtol=1e-5)
        self.assertIsInstance(converted.core.bn0, nn.Identity)

    def test_profile_validation_and_backend_routes(self):
        for changes in ({"d_model": 15}, {"head_hidden": 17}, {"output_channels": 1},
                        {"variant": "ti_npu"}, {"seq_len": 4}, {"in_channels": 18}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                TiNpuFullConvConfig(**changes)
        config = TiNpuFullConvConfig()
        self.assertEqual(load_model_config(asdict(config), "ti_npu_fullconv"), config)
        model = build_model(config, "ti_npu_fullconv")
        with self.assertRaises(RuntimeError):
            model.structural_reparam()
        with self.assertRaises(ValueError):
            model(torch.randn(1, 10, 9))

    def test_train_new_backend_and_reload_its_own_scaler_checkpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_case(root / "train.npz", 1)
            make_case(root / "selection.npz", 9, offset=20)
            split = root / "split.json"
            split.write_text(json.dumps({"train": ["train.npz"], "val": [],
                "test": ["selection.npz"], "selection_split": "test"}), encoding="utf-8")
            args = train_parser().parse_args(["--backend", "ti_npu_fullconv", "--data-dir", str(root),
                "--split", str(split), "--epochs", "1", "--batch-size", "3", "--threads", "1",
                "--device", "cpu", "--ti-blocks", "1", "--max-train-batches", "1"])
            with patch("ndp_tcn.outputs.RESULTS_ROOT", root / "results"), redirect_stdout(io.StringIO()):
                path = train(args)
            predictor = ResidualPredictor(path)
            self.assertEqual(predictor.backend, "ti_npu_fullconv")
            self.assertEqual(predictor.scalers.to_dict()["fit_case_ids"], [1])
            self.assertTrue(path.parent.name.startswith("train_ti_npu_fullconv_"))
            with np.load(root / "selection.npz", allow_pickle=False) as values:
                self.assertTrue(np.isfinite(predictor.predict(values["X"][0])["residual_V_per_s"]))
            self.assertTrue((path.parent / "README_CN.md").is_file())


class FullConvConversionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.root = Path(cls.temp.name)
        torch.set_num_threads(1)
        torch.manual_seed(27)
        n, length, dt = 6, 8, 1 / 30000
        raw = np.arange((n+length-1)*9, dtype=np.float32).reshape(-1, 9) * .1
        raw[:, 5], raw[:, 8] = 12, 48
        index = np.arange(length-1, length-1+n, dtype=np.int64)
        cls.windows = raw[index[:, None]+np.arange(-length+1, 1)]
        y = np.arange(n, dtype=np.float32)[:, None]*10
        z2 = cls.windows[:, -1, 7].astype(float)
        schema = {"feature_names": list(FEATURE_NAMES), "history_steps": length,
            "horizon_steps_to_target_interval_start": 1, "sample_interval_s": dt,
            "b0_per_phase": 20000, "label_definition": "interval_residual_v1", "label_unit": "V/s"}
        metadata = dict(schema, case_id=3, source_sha256=f"{3:064x}", X_shape=list(cls.windows.shape), y_shape=list(y.shape))
        cls.case = cls.root / "case3.npz"
        np.savez_compressed(cls.case, X=cls.windows, y=y, source_z2_V_per_s=z2,
            source_index=index, target_interval_index=index+1, source_time_s=index*dt,
            target_start_time_s=(index+1)*dt, target_end_time_s=(index+2)*dt,
            target_disturbance_V_per_s=z2+y[:, 0], feature_names=np.asarray(FEATURE_NAMES),
            metadata_json=np.asarray(json.dumps(metadata)))
        config = TiNpuConfig()
        model = build_model(config, "ti_npu").eval()
        scalers = Scalers(np.arange(9, dtype=float), np.arange(1, 10, dtype=float),
                          np.asarray([100.]), np.asarray([1000.]), (1,))
        cls.source = cls.root / "source.pt"
        torch.save({"checkpoint_version": 1, "model_backend": "ti_npu", "epoch": 55,
            "model_config": asdict(config), "model_state_dict": model.state_dict(), "scalers": scalers.to_dict(),
            "data_schema": schema, "run": {"created_at": "2026-10-30T12:00:00+08:00",
                "model_backend": "ti_npu", "model_source_sha256": hashlib.sha256(model_source("ti_npu").read_bytes()).hexdigest(),
                "selection_split": "test", "split_manifest": {"train": ["case1.npz"], "val": [], "test": [cls.case.name]},
                "data_identity": {cls.case.name: {"case_id": 3, "source_sha256": metadata["source_sha256"]}}}}, cls.source)
        cls.source_hash = hashlib.sha256(cls.source.read_bytes()).hexdigest()
        args = conversion_parser().parse_args(["--checkpoint", str(cls.source), "--data-dir", str(cls.root),
            "--output-dir", str(cls.root / "converted"), "--threads", "1"])
        with redirect_stdout(io.StringIO()):
            cls.converted = convert(args)

    def test_conversion_retains_provenance_and_raw_signal_contract(self):
        old, new = ResidualPredictor(self.source), ResidualPredictor(self.converted)
        self.assertEqual(new.backend, "ti_npu_fullconv")
        self.assertEqual(old.schema, new.schema)
        self.assertEqual(old.scalers.to_dict(), new.scalers.to_dict())
        self.assertEqual(old.checkpoint["run"]["split_manifest"], new.checkpoint["run"]["split_manifest"])
        self.assertEqual(new.checkpoint["run"]["epochs_trained_in_this_run"], 0)
        self.assertEqual(new.checkpoint["epoch"], 55)
        self.assertEqual(new.checkpoint["run"]["source_training_created_at"], "2026-10-30T12:00:00+08:00")
        self.assertEqual(hashlib.sha256(self.source.read_bytes()).hexdigest(), self.source_hash)
        report = json.loads((self.converted.parent / "conversion_report.json").read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "fp32_equivalence_verified")
        self.assertEqual(report["verification_samples"], 6)
        self.assertTrue(report["public_predictor_reload_verified"])
        self.assertFalse(report["ti_npu_ready"])

    @unittest.skipUnless(HAS_ONNX, "ONNX dependencies are unavailable")
    def test_full_output_graph_export_and_public_runtime(self):
        import onnx

        args = export_parser().parse_args(["--checkpoint", str(self.converted), "--data-dir", str(self.root),
            "--output-dir", str(self.root / "onnx"), "--threads", "1"])
        with redirect_stdout(io.StringIO()):
            directory = export(args)
        graph = onnx.load(directory / "model.onnx")
        report = audit_ti_fullconv_operator_profile(graph)
        self.assertTrue(report["passed"], report)
        self.assertEqual(len(report["convolutions"]), 4)
        self.assertFalse({"Gemm", "MatMul", "Flatten", "Slice", "Gather", "Reshape"} & {n.op_type for n in graph.graph.node})
        runtime = OnnxResidualPredictor(directory / "model.onnx", threads=1)
        self.assertEqual(runtime.contract_version, 3)
        self.assertEqual(runtime.contract["output_shape"], [1, 4, 1, 1])
        original = ResidualPredictor(self.source)
        expect = np.asarray([[original.predict(w)["residual_V_per_s"]] for w in self.windows])
        np.testing.assert_allclose(runtime.predict_array(self.windows), expect, atol=.05, rtol=1e-5)
        with np.load(directory / "golden_vectors.npz", allow_pickle=False) as values:
            self.assertEqual(values["expected_normalized_core_output"].shape, (6, 4, 1, 1))
        bad = deepcopy(graph)
        next(n for n in bad.graph.node if n.op_type == "Conv").op_type = "Gemm"
        self.assertFalse(audit_ti_fullconv_operator_profile(bad)["passed"])
        bad = deepcopy(graph)
        output = bad.graph.output[0].name
        final = next(n for n in bad.graph.node if output in n.output)
        final.output[list(final.output).index(output)] = "before_forbidden_relu"
        bad.graph.node.append(onnx.helper.make_node("Relu", ["before_forbidden_relu"], [output]))
        self.assertFalse(audit_ti_fullconv_operator_profile(bad)["passed"])
        mismatch = deepcopy(graph)
        contract = dict(runtime.contract, effective_output_channel=1)
        onnx.helper.set_model_props(mismatch, {"ndp_tcn_contract": json.dumps(contract)})
        onnx.save(mismatch, self.root / "wrong_output_contract.onnx")
        with self.assertRaisesRegex(ValueError, "four-channel output contract"):
            OnnxResidualPredictor(self.root / "wrong_output_contract.onnx")


if __name__ == "__main__":
    unittest.main()
