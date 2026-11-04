"""全卷积 TI 候选网络；网络 core 无全连接/展平/输出切片，硬件映射仍须 NNC 核查。"""
from collections import OrderedDict
from copy import deepcopy
from dataclasses import dataclass

import torch
from torch import nn

from .ti_npu_model import TiNpuTemporalNet, pack_input_tensor


@dataclass(frozen=True)
class TiNpuFullConvConfig:
    seq_len: int = 8
    in_channels: int = 9
    padded_channels: int = 12
    variant: str = "ti_npu_fullconv"
    d_model: int = 16
    num_blocks: int = 2
    kernel_size: int = 3
    head_hidden: int = 16
    output_channels: int = 4

    def __post_init__(self):
        for name in ("seq_len", "in_channels", "padded_channels", "d_model", "num_blocks",
                     "kernel_size", "head_hidden", "output_channels"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"{name} must be a positive integer.")
        if (self.variant != "ti_npu_fullconv" or self.in_channels != 9
                or self.padded_channels != 12 or self.output_channels != 4):
            raise ValueError("Full-convolution profile requires 9 raw/12 packed channels and 4 outputs.")
        if self.d_model % 4 or self.head_hidden % 4:
            raise ValueError("Every convolution channel count must be a multiple of four.")
        if self.kernel_size < 2 or self.output_steps < 1:
            raise ValueError("Valid temporal convolutions must retain at least one time position.")

    @property
    def output_steps(self):
        return self.seq_len - self.num_blocks * (self.kernel_size - 1)


class TiNpuFullConvNet(nn.Module):
    """core: [B,12,L,1] -> [B,4,1,1]; PC 训练包装层只读取有效第0通道。"""

    def __init__(self, config: TiNpuFullConvConfig, merged=False):
        super().__init__()
        if not isinstance(config, TiNpuFullConvConfig):
            raise TypeError("TiNpuFullConvNet requires TiNpuFullConvConfig.")
        self.config = config
        layers = OrderedDict()
        channels = config.padded_channels
        for index in range(config.num_blocks):
            layers[f"conv{index}"] = nn.Conv2d(channels, config.d_model,
                (config.kernel_size, 1), stride=1, padding=0, groups=1, bias=merged)
            layers[f"bn{index}"] = nn.Identity() if merged else nn.BatchNorm2d(config.d_model)
            layers[f"relu{index}"] = nn.ReLU()
            channels = config.d_model
        layers["hidden"] = nn.Conv2d(channels, config.head_hidden,
                                     (config.output_steps, 1), bias=True)
        layers["head_relu"] = nn.ReLU()
        # 四路完整输出，末端没有 Slice/Gather；有效通道0允许负值。
        layers["output"] = nn.Conv2d(config.head_hidden, config.output_channels, 1, bias=True)
        self.core = nn.Sequential(layers)
        with torch.no_grad():
            self.core.output.weight[1:].copy_(self.core.output.weight[:1].expand_as(self.core.output.weight[1:]))
            self.core.output.bias[1:].copy_(self.core.output.bias[:1].expand_as(self.core.output.bias[1:]))

    def forward(self, windows):
        if windows.ndim != 3 or windows.shape[1:] != (self.config.seq_len, 9):
            raise ValueError(f"Expected normalized [B,{self.config.seq_len},9] windows.")
        return self.core(pack_input_tensor(windows))[:, 0, 0, 0].unsqueeze(1)

    def structural_reparam(self):
        if self.training:
            raise RuntimeError("Call eval() before fusing Conv2d and BatchNorm2d.")
        for index in range(self.config.num_blocks):
            conv_name, bn_name = f"conv{index}", f"bn{index}"
            norm = self.core._modules[bn_name]
            if isinstance(norm, nn.BatchNorm2d):
                self.core._modules[conv_name] = nn.utils.fuse_conv_bn_eval(
                    self.core._modules[conv_name], norm)
                self.core._modules[bn_name] = nn.Identity()
        return self


def convert_legacy_model(source):
    """保留原权重：NCHW Flatten 顺序对应 [out,channel,time,1] 卷积核。"""
    if not isinstance(source, TiNpuTemporalNet):
        raise TypeError("Conversion requires a legacy TiNpuTemporalNet.")
    old = source.config
    config = TiNpuFullConvConfig(seq_len=old.seq_len, d_model=old.d_model,
        num_blocks=old.num_blocks, kernel_size=old.kernel_size, head_hidden=old.head_hidden)
    merged = isinstance(source.core.bn0, nn.Identity)
    result = TiNpuFullConvNet(config, merged=merged)
    for index in range(old.num_blocks):
        for prefix in ("conv", "bn"):
            name = f"{prefix}{index}"
            result.core._modules[name] = deepcopy(source.core._modules[name])
    with torch.no_grad():
        result.core.hidden.weight.copy_(source.core.hidden.weight.reshape_as(result.core.hidden.weight))
        result.core.hidden.bias.copy_(source.core.hidden.bias)
        result.core.output.weight.copy_(source.core.output.weight[:, :, None, None].repeat(4, 1, 1, 1))
        result.core.output.bias.copy_(source.core.output.bias.repeat(4))
    return result.to(next(source.parameters()).device).train(source.training)
