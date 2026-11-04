"""验证原 ModernTCN 的九通道残差任务，以及原预测路径兼容性。"""
import copy
from types import SimpleNamespace
import unittest

import torch

from ndp_tcn.model import ResidualConfig, build_model


class OriginalModernTCNTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(2)

    def setUp(self):
        torch.manual_seed(31)

    def test_original_modules_shapes_and_gradients(self):
        for length in (4, 8, 9, 32):
            with self.subTest(length=length):
                model = build_model(ResidualConfig(seq_len=length, variant='baseline',
                                                   d_model=8, head_hidden=16, dropout=0))
                self.assertEqual(type(model).__name__, 'Model')
                self.assertEqual(type(model.model.stages[0].blocks[0]).__name__, 'Block')
                self.assertEqual(len(model.model.downsample_layers), 1)
                self.assertFalse(hasattr(model.model, 'te_patch'))
                self.assertFalse(model.model.revin)
                self.assertEqual(len(model.model.lat_layer), 0)
                x = torch.randn(1, length, 9, requires_grad=True)
                out = model(x)
                self.assertEqual(tuple(out.shape), (1, 1))
                out.square().sum().backward()
                self.assertGreater(x.grad.abs().sum().item(), 0)
                for name, parameter in model.named_parameters():
                    self.assertIsNotNone(parameter.grad, name)
                    self.assertTrue(torch.isfinite(parameter.grad).all(), name)

    def test_signed_output_and_contract(self):
        model = build_model(ResidualConfig(variant='baseline')).eval()
        self.assertEqual(sum(p.numel() for p in model.parameters()), 180193)
        with torch.no_grad():
            model.model.head[-1].weight.zero_()
            model.model.head[-1].bias.fill_(-3)
            torch.testing.assert_close(model(torch.randn(2, 8, 9)), torch.full((2, 1), -3.))
        for shape in ((8, 9), (1, 8, 8), (1, 9, 9)):
            with self.subTest(shape=shape), self.assertRaises(ValueError):
                model(torch.randn(*shape))
        with self.assertRaises(ValueError):
            build_model(ResidualConfig(variant='dual'))

    def test_residual_settings_reject_wrong_target(self):
        model_type = type(build_model(ResidualConfig(variant='baseline')))
        for changes in ({'enc_in': 8}, {'seq_len': 3}, {'revin': True},
                        {'decomposition': True}, {'pred_len': 2},
                        {'dims': [8, 8]}, {'large_size': [6]},
                        {'patch_size': 1, 'patch_stride': 2}, {'dropout': 1}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                model_type(SimpleNamespace(task_name='residual', **changes))

    def test_fusion_eval_only_idempotent_and_reload(self):
        for dtype in (torch.float32, torch.float64):
            with self.subTest(dtype=dtype):
                config = ResidualConfig(variant='baseline', seq_len=9, d_model=8,
                                        head_hidden=16, dropout=0)
                model = build_model(config).to(dtype=dtype)
                for _ in range(3):
                    model(torch.randn(3, 9, 9, dtype=dtype))
                with self.assertRaises(RuntimeError):
                    model.structural_reparam()
                model.eval()
                merged = copy.deepcopy(model)
                merged.structural_reparam()
                merged.structural_reparam()
                restored = build_model(config, merged=True).to(dtype=dtype).eval()
                restored.load_state_dict(merged.state_dict(), strict=True)
                x = torch.randn(2, 9, 9, dtype=dtype)
                with torch.inference_mode():
                    torch.testing.assert_close(merged(x), model(x), rtol=2e-5, atol=2e-6)
                    torch.testing.assert_close(restored(x), merged(x))
                self.assertEqual(merged.model.stages[0].blocks[0].dw.lkb_reparam.weight.dtype, dtype)

    def test_forecasting_path_retains_multichannel_output(self):
        model_type = type(build_model(ResidualConfig(variant='baseline')))
        cfg = SimpleNamespace(stem_ratio=1, downsample_ratio=2, ffn_ratio=2,
                              num_blocks=[1, 1], large_size=[7, 7], small_size=[3, 3],
                              dims=[8, 8], dw_dims=[8, 8], enc_in=3,
                              small_kernel_merged=False, dropout=0, head_dropout=0,
                              use_multi_scale=False, revin=True, affine=True,
                              subtract_last=False, freq='h', seq_len=16,
                              individual=False, pred_len=2, kernel_size=3,
                              patch_size=4, patch_stride=2, decomposition=False)
        for decomposition in (False, True):
            cfg.decomposition = decomposition
            model = model_type(cfg).eval()
            with torch.inference_mode():
                self.assertEqual(tuple(model(torch.randn(2, 16, 3)).shape), (2, 2, 3))


if __name__ == '__main__':
    unittest.main()
