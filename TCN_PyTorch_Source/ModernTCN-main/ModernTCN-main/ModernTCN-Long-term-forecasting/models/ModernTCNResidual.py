"""九通道历史到单个带符号扰动残差的 ModernTCN 任务适配。

主干沿用本仓库 models/ModernTCN.py 的 Block：可重参数化大核逐通道
卷积、按变量分组的 FFN1、按特征分组的 FFN2 和残差连接。
原始来源：https://github.com/luodhhh/ModernTCN 。

本文件只依赖 torch。采用单 stage、联合回归头和外部固定标准化；不使用
原预测头或 RevIN 反归一化。dual 版本额外保留近期原采样率的短时分支。
完整输入窗口必须截至推理源时刻；窗口内对称卷积不等于逐点流式因果卷积。
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import math

import torch
from torch import nn
import torch.nn.functional as F


@dataclass(frozen=True)
class ResidualConfig:
    seq_len: int = 8
    in_channels: int = 9
    variant: str = "dual"
    d_model: int = 32
    num_blocks: int = 2
    ffn_ratio: int = 2
    large_kernel: int = 7
    small_kernel: int = 3
    patch_size: int = 4
    patch_stride: int = 2
    short_len: int = 4
    short_channels: int = 32
    head_hidden: int = 64
    dropout: float = 0.1

    def __post_init__(self):
        for name in ("seq_len", "in_channels", "d_model", "num_blocks", "ffn_ratio",
                     "large_kernel", "small_kernel", "patch_size", "patch_stride",
                     "short_len", "short_channels", "head_hidden"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"{name} must be a positive integer.")
        if self.seq_len < 4:
            raise ValueError("seq_len must be at least 4.")
        if self.in_channels != 9:
            raise ValueError("This task requires the agreed 9 input channels.")
        if self.variant not in ("baseline", "dual"):
            raise ValueError("variant must be 'baseline' or 'dual'.")
        if self.large_kernel % 2 != 1 or self.small_kernel % 2 != 1:
            raise ValueError("Both temporal kernels must be odd.")
        if self.small_kernel > self.large_kernel:
            raise ValueError("small_kernel must not exceed large_kernel.")
        if self.patch_size < self.patch_stride:
            raise ValueError("patch_size must be at least patch_stride.")
        if math.ceil(self.seq_len / self.patch_stride) < 2:
            raise ValueError("At least two temporal patches are required for batch-one training.")
        if self.short_len > self.seq_len:
            raise ValueError("short_len must not exceed seq_len.")
        if not math.isfinite(self.dropout) or not 0 <= self.dropout < 1:
            raise ValueError("dropout must be finite and in [0, 1).")


def _conv_bn(channels: int, kernel_size: int):
    return nn.Sequential(
        nn.Conv1d(channels, channels, kernel_size, padding=kernel_size // 2,
                  groups=channels, bias=False),
        nn.BatchNorm1d(channels),
    )


def _fuse_conv_bn(conv: nn.Conv1d, bn: nn.BatchNorm1d):
    scale = bn.weight / torch.sqrt(bn.running_var + bn.eps)
    bias = conv.bias if conv.bias is not None else torch.zeros_like(bn.running_mean)
    return conv.weight * scale[:, None, None], bn.bias + (bias-bn.running_mean)*scale


class ReparamDepthwiseConv(nn.Module):
    """与原版的大/小核并联结构等价，融合时保留设备与 dtype。"""

    def __init__(self, channels, large_kernel, small_kernel, merged=False):
        super().__init__()
        self.channels = channels
        self.large_kernel = large_kernel
        self.small_kernel = small_kernel
        if merged:
            self.reparam = nn.Conv1d(channels, channels, large_kernel,
                                     padding=large_kernel // 2, groups=channels)
        else:
            self.large = _conv_bn(channels, large_kernel)
            self.small = _conv_bn(channels, small_kernel)

    def forward(self, x):
        if hasattr(self, "reparam"):
            return self.reparam(x)
        return self.large(x) + self.small(x)

    def merge_kernel(self):
        if self.training:
            raise RuntimeError("Kernel merging requires eval mode and fixed BN statistics.")
        if hasattr(self, "reparam"):
            return
        with torch.no_grad():
            weight, bias = _fuse_conv_bn(self.large[0], self.large[1])
            small_weight, small_bias = _fuse_conv_bn(self.small[0], self.small[1])
            edge = (self.large_kernel - self.small_kernel) // 2
            # F.pad retains the original tensor's device and floating-point dtype.
            weight = weight + F.pad(small_weight, (edge, edge))
            bias = bias + small_bias
            conv = nn.Conv1d(self.channels, self.channels, self.large_kernel,
                             padding=self.large_kernel // 2, groups=self.channels)
            conv = conv.to(device=weight.device, dtype=weight.dtype)
            conv.weight.copy_(weight)
            conv.bias.copy_(bias)
            self.reparam = conv
            del self.large
            del self.small


class ModernResidualBlock(nn.Module):
    """保留原 ModernTCN 的时间、特征和变量交互顺序。"""

    def __init__(self, config: ResidualConfig, merged=False):
        super().__init__()
        m, d, f = config.in_channels, config.d_model, config.d_model * config.ffn_ratio
        self.dw = ReparamDepthwiseConv(m*d, config.large_kernel, config.small_kernel, merged)
        self.norm = nn.BatchNorm1d(d)
        self.ffn1 = nn.Sequential(
            nn.Conv1d(m*d, m*f, 1, groups=m),
            nn.Dropout(config.dropout),
            nn.GELU(),
            nn.Conv1d(m*f, m*d, 1, groups=m),
            nn.Dropout(config.dropout),
        )
        self.ffn2 = nn.Sequential(
            nn.Conv1d(d*m, config.ffn_ratio*d*m, 1, groups=d),
            nn.Dropout(config.dropout),
            nn.GELU(),
            nn.Conv1d(config.ffn_ratio*d*m, d*m, 1, groups=d),
            nn.Dropout(config.dropout),
        )

    def forward(self, x):
        residual = x
        b, m, d, p = x.shape
        x = self.dw(x.reshape(b, m*d, p))
        x = self.norm(x.reshape(b*m, d, p)).reshape(b, m*d, p)
        x = self.ffn1(x).reshape(b, m, d, p)
        x = x.permute(0, 2, 1, 3).reshape(b, d*m, p)
        x = self.ffn2(x).reshape(b, d, m, p).permute(0, 2, 1, 3)
        return residual + x


class ShortResolutionBranch(nn.Module):
    """近期窗口的两层 stride=1 卷积，不压缩时间轴。"""

    def __init__(self, in_channels, channels):
        super().__init__()
        self.project = nn.Conv1d(in_channels, channels, 1)
        self.conv1 = nn.Conv1d(channels, channels, 3)
        self.conv2 = nn.Conv1d(channels, channels, 3)
        self.activation = nn.GELU()

    def forward(self, x):
        x = self.project(x)
        residual = x
        x = self.activation(self.conv1(F.pad(x, (2, 0))))
        x = self.conv2(F.pad(x, (2, 0)))
        return self.activation(x + residual)


class ResidualModernTCN(nn.Module):
    """forward: [batch, seq_len, 9] -> [batch, 1]，输出保持正负号。"""

    def __init__(self, config: ResidualConfig, merged=False):
        super().__init__()
        if not isinstance(config, ResidualConfig):
            raise TypeError("config must be a ResidualConfig instance.")
        self.config = config
        self.is_merged = bool(merged)
        self.patch_count = math.ceil(config.seq_len / config.patch_stride)
        required_length = (self.patch_count-1)*config.patch_stride + config.patch_size
        self.right_padding = required_length - config.seq_len
        self.stem = nn.Sequential(
            nn.Conv1d(1, config.d_model, config.patch_size, stride=config.patch_stride),
            nn.BatchNorm1d(config.d_model),
        )
        self.blocks = nn.ModuleList([
            ModernResidualBlock(config, merged=merged) for _ in range(config.num_blocks)
        ])
        head_inputs = config.in_channels * config.d_model * self.patch_count
        if config.variant == "dual":
            self.short_branch = ShortResolutionBranch(config.in_channels, config.short_channels)
            head_inputs += config.short_channels * config.short_len
        else:
            self.short_branch = None
        self.head = nn.Sequential(
            nn.Linear(head_inputs, config.head_hidden),
            nn.GELU(),
            nn.Dropout(config.dropout),
            nn.Linear(config.head_hidden, 1),
        )

    def forward(self, x):
        if x.ndim != 3 or x.shape[1] != self.config.seq_len or x.shape[2] != self.config.in_channels:
            raise ValueError(f"Expected [batch, {self.config.seq_len}, {self.config.in_channels}] input.")
        b, length, m = x.shape
        # Per-variable patch embedding preserves the original ModernTCN representation.
        features = x.transpose(1, 2).reshape(b*m, 1, length)
        if self.right_padding:
            # Only repeat the latest point already present in the input history.
            features = F.pad(features, (0, self.right_padding), mode="replicate")
        features = self.stem(features)
        features = features.reshape(b, m, self.config.d_model, self.patch_count)
        for block in self.blocks:
            features = block(features)
        features = features.reshape(b, -1)
        if self.short_branch is not None:
            short = x[:, -self.config.short_len:, :].transpose(1, 2)
            short = self.short_branch(short).reshape(b, -1)
            features = torch.cat((features, short), dim=1)
        return self.head(features)

    def merged_copy(self):
        """返回 eval 融合副本；原模型仍可继续训练或保存未融合权重。"""
        if self.training:
            raise RuntimeError("Call model.eval() before merged_copy().")
        model = deepcopy(self)
        for module in model.modules():
            if isinstance(module, ReparamDepthwiseConv):
                module.merge_kernel()
        model.is_merged = True
        model.eval()
        return model
