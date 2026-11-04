"""面向 TI NPU 层配置的轻量时序 CNN；FP32 结构合规不等于已完成 TI 编译。"""
from collections import OrderedDict
from dataclasses import dataclass

import torch
from torch import nn


@dataclass(frozen=True)
class TiNpuConfig:
    seq_len: int = 8
    in_channels: int = 9
    padded_channels: int = 12
    variant: str = "ti_npu"
    d_model: int = 16
    num_blocks: int = 2
    kernel_size: int = 3
    head_hidden: int = 16

    def __post_init__(self):
        for name in ("seq_len", "in_channels", "padded_channels", "d_model", "num_blocks",
                     "kernel_size", "head_hidden"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"{name} must be a positive integer.")
        if self.variant != "ti_npu" or self.in_channels != 9 or self.padded_channels != 12:
            raise ValueError("The TI profile requires variant=ti_npu and 9 raw/12 packed channels.")
        if self.d_model % 4 or self.padded_channels % 4:
            raise ValueError("TI convolution channel counts must be multiples of four.")
        if self.kernel_size < 2:
            raise ValueError("TI temporal GCONV uses a kernel height of at least two.")
        remaining = self.seq_len-self.num_blocks*(self.kernel_size-1)
        if remaining < 1:
            raise ValueError("Valid convolutions would exhaust the history length.")
        if self.d_model*remaining < 16 or self.head_hidden < 16:
            raise ValueError("Each 8-bit TI fully-connected layer needs at least 16 input features.")

    @property
    def output_steps(self):
        return self.seq_len-self.num_blocks*(self.kernel_size-1)


def pack_input_tensor(windows, padded_channels=12):
    """标准化后在 CPU/训练包装层重排和补零；不把这一步放入 NPU 图。"""
    if windows.ndim != 3 or windows.shape[2] != 9:
        raise ValueError("Expected normalized windows [B,L,9].")
    if padded_channels != 12:
        raise ValueError("The TI input contract uses exactly 12 packed channels.")
    values = windows.transpose(1, 2).unsqueeze(-1)
    zeros = windows.new_zeros((windows.shape[0], padded_channels-9, windows.shape[1], 1))
    return torch.cat((values, zeros), dim=1).contiguous()


class TiNpuTemporalNet(nn.Module):
    """训练接口 [B,L,9]，导出 core 接口 [B,12,L,1]，单个有符号残差输出。"""

    def __init__(self, config: TiNpuConfig, merged=False):
        super().__init__()
        if not isinstance(config, TiNpuConfig):
            raise TypeError("TiNpuTemporalNet requires TiNpuConfig.")
        self.config = config
        layers = OrderedDict()
        channels = config.padded_channels
        for index in range(config.num_blocks):
            layers[f"conv{index}"] = nn.Conv2d(channels, config.d_model,
                (config.kernel_size, 1), stride=1, padding=0, groups=1, bias=merged)
            layers[f"bn{index}"] = nn.Identity() if merged else nn.BatchNorm2d(config.d_model)
            layers[f"relu{index}"] = nn.ReLU()
            channels = config.d_model
        layers["flatten"] = nn.Flatten(start_dim=1)
        layers["hidden"] = nn.Linear(config.d_model*config.output_steps, config.head_hidden)
        layers["head_relu"] = nn.ReLU()
        # 残差允许正负值；此处不能加 ReLU 或非负截断。
        layers["output"] = nn.Linear(config.head_hidden, 1)
        self.core = nn.Sequential(layers)

    def forward(self, windows):
        if windows.ndim != 3 or windows.shape[1:] != (self.config.seq_len, 9):
            raise ValueError(f"Expected normalized [B,{self.config.seq_len},9] windows.")
        return self.core(pack_input_tensor(windows, self.config.padded_channels))

    def structural_reparam(self):
        """只对调用方持有的 eval 模型融合 Conv+BN；导出方应先 deepcopy。"""
        if self.training:
            raise RuntimeError("Call eval() before fusing TI Conv2d and BatchNorm2d.")
        for index in range(self.config.num_blocks):
            conv_name, bn_name = f"conv{index}", f"bn{index}"
            norm = self.core._modules[bn_name]
            if isinstance(norm, nn.BatchNorm2d):
                self.core._modules[conv_name] = nn.utils.fuse_conv_bn_eval(
                    self.core._modules[conv_name], norm)
                self.core._modules[bn_name] = nn.Identity()
        return self
