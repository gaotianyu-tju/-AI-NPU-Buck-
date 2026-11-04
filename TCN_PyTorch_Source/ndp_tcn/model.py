"""当前训练直接构建原 models.ModernTCN.Model；保留旧实验权重的加载接口。"""
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace

from .ti_npu_model import TiNpuConfig, TiNpuTemporalNet
from .ti_npu_fullconv_model import TiNpuFullConvConfig, TiNpuFullConvNet

MODEL_SOURCE = (Path(__file__).resolve().parents[1] / "ModernTCN-main" /
                "ModernTCN-main" / "ModernTCN-Long-term-forecasting" /
                "models" / "ModernTCNResidual.py")
_NAME = "ndp_tcn_modern_residual"
if _NAME not in sys.modules:
    spec = importlib.util.spec_from_file_location(_NAME, MODEL_SOURCE)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load residual model from {MODEL_SOURCE}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[_NAME] = module
    spec.loader.exec_module(module)

ResidualConfig = sys.modules[_NAME].ResidualConfig
ResidualModernTCN = sys.modules[_NAME].ResidualModernTCN

ORIGINAL_SOURCE = MODEL_SOURCE.with_name("ModernTCN.py")
TI_NPU_SOURCE = Path(__file__).resolve().with_name("ti_npu_model.py")
TI_NPU_FULLCONV_SOURCE = Path(__file__).resolve().with_name("ti_npu_fullconv_model.py")


def model_source(backend):
    if backend == "original":
        return ORIGINAL_SOURCE
    if backend == "legacy":
        return MODEL_SOURCE
    if backend == "ti_npu":
        return TI_NPU_SOURCE
    if backend == "ti_npu_fullconv":
        return TI_NPU_FULLCONV_SOURCE
    raise ValueError(f"Unknown model backend: {backend}")


def load_model_config(values, backend):
    """按 checkpoint 的后端恢复配置，防止不同架构同形状参数被误用。"""
    model_source(backend)
    if backend == "ti_npu_fullconv":
        return TiNpuFullConvConfig(**values)
    return TiNpuConfig(**values) if backend == "ti_npu" else ResidualConfig(**values)


def build_model(config, backend="original", merged=False):
    """original 直接调用已修改的 baseline；legacy 仅用于历史实验复现。"""
    model_source(backend)  # Validate before importing or constructing a model.
    if backend == "ti_npu":
        return TiNpuTemporalNet(config, merged=merged)
    if backend == "ti_npu_fullconv":
        return TiNpuFullConvNet(config, merged=merged)
    if backend == "legacy":
        return ResidualModernTCN(config, merged=merged)
    if config.variant != "baseline":
        raise ValueError("The original ModernTCN residual task uses variant=baseline.")
    project = str(ORIGINAL_SOURCE.parents[1])
    if project not in sys.path:
        sys.path.insert(0, project)
    name = "ndp_tcn_original_moderntcn"
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, ORIGINAL_SOURCE)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load original ModernTCN from {ORIGINAL_SOURCE}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    settings = SimpleNamespace(
        task_name="residual", seq_len=config.seq_len, enc_in=config.in_channels,
        pred_len=1, c_out=1, stem_ratio=1, downsample_ratio=2,
        ffn_ratio=config.ffn_ratio, num_blocks=[config.num_blocks],
        large_size=[config.large_kernel], small_size=[config.small_kernel],
        dims=[config.d_model], dw_dims=[config.d_model],
        small_kernel_merged=merged, dropout=config.dropout,
        head_dropout=config.dropout, head_hidden=config.head_hidden,
        patch_size=config.patch_size, patch_stride=config.patch_stride,
        use_multi_scale=False, revin=False, affine=False, subtract_last=False,
        freq="h", individual=False, decomposition=False, kernel_size=25,
    )
    return sys.modules[name].Model(settings)
