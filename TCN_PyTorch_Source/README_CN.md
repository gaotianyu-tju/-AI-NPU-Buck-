# 比赛提交：TCN / ModernTCN 的 PyTorch 源码

打包时间：2026-11-03T03:25:01.923816+08:00，Asia/Singapore（UTC+08:00）。
按本次要求只提交 Python / PyTorch 源码及必要的配置、依赖与说明；不含模型权重、训练数据、
CCS 工程、TI 编译库、ONNX 模型文件、仿真电路和历史实验输出。
用户已报告完成板端部署；本包用于提交神经网络源码，不重新验证或变更板端工程。

## 1. 先看这些文件

| 文件 | 内容 |
|---|---|
| [ndp_tcn/ti_npu_fullconv_model.py](ndp_tcn/ti_npu_fullconv_model.py) | 当前四层全卷积网络，主类 TiNpuFullConvNet |
| [ndp_tcn/ti_npu_model.py](ndp_tcn/ti_npu_model.py) | 旧 TI 时序 CNN、输入补零/布局转换；当前源码依赖此文件 |
| [ModernTCN.py](ModernTCN-main/ModernTCN-main/ModernTCN-Long-term-forecasting/models/ModernTCN.py) | 最初使用并适配残差任务的 ModernTCN baseline |
| [ModernTCNResidual.py](ModernTCN-main/ModernTCN-main/ModernTCN-Long-term-forecasting/models/ModernTCNResidual.py) | 历史独立适配；模型工厂仍需其配置定义 |
| [ndp_tcn/model.py](ndp_tcn/model.py) | 按 backend 创建当前网络或 baseline |
| [ndp_tcn/train.py](ndp_tcn/train.py) | PyTorch 训练、验证选优、checkpoint 保存 |
| [ndp_tcn/predict.py](ndp_tcn/predict.py) | 加载 checkpoint、标准化、滑动窗口预测与单位恢复 |
| [ndp_tcn/evaluate.py](ndp_tcn/evaluate.py) | 工况级模型评价 |
| [ndp_tcn/data.py](ndp_tcn/data.py) | NPZ 读取、工况划分和标准化 |
| [prepare_residual_labels.py](prepare_residual_labels.py) | 从 MAT 生成监督标签 |
| [prepare_horizon_experiment.py](prepare_horizon_experiment.py) | H15/16/20 标签及分组划分 |
| [ndp_tcn/ti_qat.py](ndp_tcn/ti_qat.py) | 基于 PyTorch 的 TI 量化感知训练 |
| [ndp_tcn/export_onnx.py](ndp_tcn/export_onnx.py) | PyTorch 模型导出代码；本包未附 ONNX 产物 |
| [configs/split_h15.json](configs/split_h15.json) | 当前 H15 实验实际 602训练 / 71验证 / 77测试划分 |

当前默认结构有 2516 个参数；两层时间卷积和两层卷积回归头，输入通道依次 12→16→16→16→4，
时间核依次为 3、3、4、1。训练时含 BatchNorm，推理导出可融合；隐藏层为 ReLU，末层允许负数。
H15、H16、H20 共用网络结构，由标签和训练权重确定预测步长，不通过更改网络文件切换已有权重的 H。
原 ModernTCN baseline 与当前 ti_npu_fullconv 是两个可选 backend，不能混称同一网络结构。

## 2. 输入输出约定

- 原始窗口：[B,8,9]，按旧到新排列。通道固定为 Vo、ILA、ILB、ILC、ILD、VREF、IREF、z2、Vin。
- 电压单位 V、电流单位 A、z2 和残差单位 V/s。IREF 是四相共用的每相参考，不乘4。
- train/predict 在网络外使用训练集 scaler 标准化；网络 forward 接收标准化的 [B,8,9]。
- 核心将输入补到12通道，NCHW [B,12,8,1]；输出 [B,4,1,1]，有效槽为0。
  PyTorch 训练包装层读取第0槽，返回 [B,1]。四槽不是四个预测步长。
- 采样 30kHz，b0=20000。标签 y[k]=f_interval[k+H]-z2[k]，
  f_interval[j]=(Vo[j+1]-Vo[j])/dt[j]-b0*IREF[j]。
- H15 的目标区间为 [t[k+15],t[k+16])，起点约在500μs之后；未来量只用于标签。
- 物理残差=normalized_output*y_scale+y_mean；未来总扰动=源拍z2+物理残差。

## 3. 安装及源码检查

解压整个 TCN_PyTorch_Source 文件夹，在 VS Code 打开该文件夹，并选择 Python 3.10 的 TCN 环境。
终端工作目录是解压后的源码根目录；不要只取单个网络文件运行，否则可能缺少同目录模块。

```text
python -m pip install -r requirements.txt
python check_source.py
python -m ndp_tcn.train --help
python -m ndp_tcn.predict --help
```

check_source.py 校验文件 SHA-256、Python 语法，并用随机输入检查 ModernTCN baseline、
旧 TI CNN、当前全卷积网络的前向/反向传播；不依赖权重或数据，不更新正式模型。
只查文件完整性可运行 python check_source.py --hash-only。

需要运行可选的 ONNX / TI QAT Python 代码时再安装：

```text
python -m pip install -r requirements_onnx_qat.txt
```

environment/requirement_original_full.txt 是本机原完整环境锁定参考，其中包含本次未提交的
TI 编译流程依赖；基本网络审阅和 PyTorch 训练使用根 requirements.txt 即可。
本机使用 torch 2.11.0+cpu，本轮未在新电脑联网安装或测试 GPU 环境。

## 4. 有数据后重新训练

本包只含源码，下面的训练需要另行准备原始数据及标签。沿用历史批次身份和750工况划分时，
请使用 prepare_training_750.py / prepare_horizon_experiment.py 保留 case_id、batch_id 和负载族信息，
不要用16组回放数据或随意构造编号替代完整训练集。
prepare_horizon_experiment.py 的默认源目录为 data/train_500、data/数据集新，
还需要 data/train_500_labeled 的旧标签元信息；可通过 --old-sources、--new-sources、--old-labels 指定。
这些输入均未包含在本次源码包中。

若已有匹配的 H15 全量标签，放在 data/h15_labeled 后可执行：

```text
python -m ndp_tcn.train --backend ti_npu_fullconv --data-dir data/h15_labeled --split configs/split_h15.json --epochs 100 --patience 20 --batch-size 256 --lr 0.001 --weight-decay 0.0001 --loss mse --sampling case --seed 2026 --device cpu --threads 2
```

输出自动放入本源码目录下 ndp_tcn/results/train_ti_npu_fullconv_时间戳，使用 UTC+08。
--epochs 是最多轮数，patience=20 允许提前停止。上述配置对应 H15 的训练方式，
不代表本次重新训练过。原 pilot / 500 / 750 的其他划分保留在 configs，不能混用于 H15 数据。

训练结束后，用刚生成目录的 best.pt 执行评价和推理：

```text
python -m ndp_tcn.evaluate --checkpoint ndp_tcn/results/你的本次训练目录/best.pt --data-dir data/h15_labeled --split test
python -m ndp_tcn.predict --checkpoint ndp_tcn/results/你的本次训练目录/best.pt --input-npz data/h15_labeled/你的工况.npz
```

以上两个“你的...”是需替换为实际文件名的占位符；评价与推理必须衔接同一次训练。
默认评价/推理也在 ndp_tcn/results 自动创建时间戳结果。若只审阅代码，运行源码检查即可。

## 5. 来源、验证与留档

所有既有 .py 文件按原样复制，模型结构与训练逻辑没有改动；原项目代码、权重、数据均保留。
ModernTCN 只收录本项目实际依赖的 Long-term-forecasting 子项目，原作者、MIT许可证和修改说明见
[THIRD_PARTY_NOTICES_CN.md](THIRD_PARTY_NOTICES_CN.md)。
本次新增 README、依赖入口和 check_source.py，以便比赛审阅；它们此前不存在，没有修改前版本。
MANIFEST.json 记录每个交付文件的 SHA-256 及原路径；压缩包本身是本次提交快照，不冒充修改前备份。
本包不覆盖旧代码，无需恢复；若以后把包内文件覆盖回项目，应先保存当前版本并逐项核对来源。

打包校验记录见同级交付目录的 validation.json：包含解压后的语法、导入、前向/反向、CLI及ZIP校验。
本次不重新训练、不推理已训练权重、不运行硬件；不把随机输入检查作为模型精度或板端实测。
原配置中的绝对路径只用于保留历史来源；本说明命令使用当前解压目录下的相对路径。

2026-11-03：按“只要 PyTorch 源文件”整理比赛源码包，保留当前 TCN、ModernTCN baseline 及训练链。
