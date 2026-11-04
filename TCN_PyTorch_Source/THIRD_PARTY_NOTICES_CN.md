# 第三方代码与来源

ModernTCN 源自 Donghao Luo / Xue Wang 的 ICLR 2024 项目，原仓库地址为
https://github.com/luodhhh/ModernTCN 。本包保留本地已使用的长时预测子项目及其依赖，
保留原 README、requirements 与 MIT LICENSE（Copyright (c) 2024 luodhhh）。
原 README 还描述分类等其他子项目和插图，本源码子集没有收录这些无关任务及图片。

本地 models/ModernTCN.py、run.py 已增加九通道扰动残差任务；
models/ModernTCNResidual.py 是项目历史适配实现。因此本包不能称为未修改的官方源码。
ndp_tcn/ti_npu_fullconv_model.py 是当前面向 TI 的四层全卷积 PyTorch 实现，
不同于原 ModernTCN 大核/分组 FFN 主干；历史 baseline 与当前网络在说明中分别标注。

PyTorch、NumPy、ONNX 与 TI 量化工具本身通过依赖安装，不在本源码包中重新发布其安装文件。
本包中“PyTorch 源码”指本项目使用 PyTorch 编写的网络和训练程序，不是 PyTorch 框架源码。
本次打包未替用户新增整项目开源许可证；ModernTCN 的原 MIT 许可证保持有效并保留原文。
