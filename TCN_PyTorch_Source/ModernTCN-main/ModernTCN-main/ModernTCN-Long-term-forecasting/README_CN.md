# ModernTCN：四相 Buck 九通道扰动残差任务

本次直接修改本工程原有的 `models/ModernTCN.py` 和 `run.py`。
使用原 ModernTCN 的卷积主干，联合九路历史信号预测一个带正负号的扰动残差。
当前版本采用单主干，没有额外短时分支。原来的时间序列预测任务仍使用原运行参数。
当前默认数据按完整工况 4∶1 划分：8 个工况训练，2 个仍命名为 `test` 的工况用于每轮验证并选择 `best.pt`。
后两组实际承担选优作用，当前没有独立测试集。
训练、评价和批量推理默认保存到 `E:\bisai\ndp_tcn\results` 并自动添加 UTC+08 时间戳。
每次训练自动生成中文实验配置与结果说明；当前完整实验配置见 [结果目录说明](../../../ndp_tcn/results/README_CN.md)。
原网络的 ONNX 导出与 TMS320F28P55x 部署路线见 [ONNX 中文说明](../../../ndp_tcn/README_ONNX_CN.md)。
后续新增的 TI 算子适配网络使用 `--backend ti_npu`，独立于本文 original baseline，需重新训练；
新结构与当前部署阶段见 [TI NPU 网络说明](../../../ndp_tcn/README_TI_NPU_CN.md)。原 `run.py` 保留原 baseline 入口。
新后端默认模型已完成 17 轮训练，2,465 参数，FP32 选优集 RMSE 为 5252.399358 V/s。
当前推荐 [QAT 最佳模型](../../../ndp_tcn/results/ti_qat_20261031_210117/) 及其 [TI 编译库](../../../ndp_tcn/results/ti_compile_20261031_210247/)，
QAT RMSE 为 5783.914384 V/s；2 层 GCONV 使用 NPU、2 层 FC 使用 C28 CPU，板上未验证。新环境全套 88 项测试通过。

## 网络改了什么

```text
输入 [B, L, 9]
    → 每通道 patch 嵌入
    → 原 ModernTCN Stage / Block
    → 合并九通道特征
    → 联合回归头
输出 [B, 1]
```

- 通道顺序固定为 `Vo, ILA, ILB, ILC, ILD, VREF, IREF, z2, Vin`。
- `ILA～ILD` 是四相实测电流；`IREF` 是四相共用的每相电流参考，不乘 4。
- 默认单 stage、2 个 Block、特征维度 32、大/小核 7/3、FFN 比例 2、patch=4、stride=2、回归头中间维度 64、dropout=0.1。
- 当前数据历史长度 L=8，因此得到 4 个时间 patch。不同 L 必须匹配重新生成的数据和训练权重。
- 原逐变量预测头改为九通道联合单输出头。末层没有限制正负的激活函数。
- 残差任务关闭 RevIN 和时序分解，输入与标签使用仅从训练工况拟合的固定标准化参数。
- 保留原 Block 中的大核/小核逐通道卷积、分组 FFN 和残差连接；调整单 stage 初始化及窗口末尾填充。

原工程的 `Model(configs)` 在 `configs.task_name == 'residual'` 时启用上述路径。
`ndp_tcn/model.py` 只负责将配置映射到这个原 `Model`；NPZ 读取、训练和推理工具复用项目根目录的 `ndp_tcn/`。
之前独立文件 `ModernTCNResidual.py` 保留用于加载旧实验权重，当前 `run.py` 残差训练不使用它的网络实现。

## 1. VS Code 运行准备

在 VS Code 打开 `E:\bisai` 文件夹，使用 TCN 环境并打开集成终端。
下列所有命令都在 `E:\bisai` 目录执行，直接使用 `python`：

```text
python -c "import sys; print(sys.executable)"
python -c "import torch; print(torch.__version__)"
```

第一条应指向 TCN 环境，本机为 `C:\Users\User\.conda\envs\TCN\python.exe`；第二条确认 PyTorch 可以导入。
原 FP32 实验使用 Python 3.11、PyTorch、NumPy、SciPy 和 einops；同名 TCN 后续切换到 Python 3.10 以适配 TI 工具。
当前依赖和验证状态见 [TI 说明](../../../ndp_tcn/README_TI_NPU_CN.md#6-当前实际状态)，不要把旧实验环境表当作当前版本清单。
这些是终端命令；如果出现 `>>>`，先输入 `exit()` 退出 Python 交互模式。

## 2. 训练

现有 NPZ 标签已经可用，无需重新生成。训练读取前 8 个工况更新权重，每轮用后 2 个工况评价并选优：

```text
python -m ndp_tcn.train --epochs 50 --batch-size 128 --lr 0.001 --patience 10
```

这个简短入口默认直接构造本工程修改后的 `models/ModernTCN.py`。下面是原 `run.py` 的等价入口，两条选一运行：

```text
python ModernTCN-main/ModernTCN-main/ModernTCN-Long-term-forecasting/run.py --task_name residual --epochs 50 --batch-size 128 --lr 0.001 --patience 10
```

默认读取 `E:\bisai\data\train_example_labeled`，划分清单为 `E:\bisai\configs\ndp_tcn_split.json`。
按完整工况划分：训练 1～8，共 27,142 个窗口；测试 9、10，共 854 个窗口；验证列表为 `val=[]`。
4∶1 是 8 个训练文件和 2 个测试文件的比例，不是窗口数量的 80%/20%。测试工况均为 210 Hz，占空比分别为 10% 与 90%。
配置显式设置 `selection_split="test"`，test 中这两组的分数用于选择模型，不能当作独立测试成绩。
默认 MSE、AdamW、学习率 0.001、weight decay=0.0001、batch=128、最多 50 轮、patience=10、seed=2026、CPU 线程数 2。
有 GPU 时 `--device auto` 会选择 CUDA；当前机器环境为 CPU 版 PyTorch。
每轮完整评价工况 9、10，按两个工况 RMSE 的算术平均最小值保存最佳模型。
这两组只参与推理评价和模型选择；梯度更新与标准化拟合仍然只使用训练工况 1～8。

`epochs` 是训练轮数上限，`batch-size` 是每批窗口数，`lr` 是学习率。
选优指标连续 `patience=10` 轮不改善时提前停止，训练损失只用于监控。
默认自动创建 `E:\bisai\ndp_tcn\results\train_YYYYMMDD_HHMMSS`，时间为 Asia/Singapore（UTC+08）；
同秒重名自动追加 `_01`、`_02` 等后缀。终端打印实际目录，每次训练无需手动改名。
下面的 `train_YYYYMMDD_HHMMSS` 是占位名称，执行评价和推理前，替换为这次训练实际打印的目录名，并使用同一个 `best.pt`。

当前结果包含 `best.pt`、`selection_metrics.json`、`config.json`、`scalers.json`、`history.json` 和自动生成的中文 `README_CN.md`。
README 在训练开始时记录实际配置，在结束后更新训练轮数、最佳轮次和结果；简化流程检查会单独标明。
`selection_policy=test_macro_rmse`，`test_used_for_selection=true`、`independent_test_available=false`。
逐轮指标保存在 `selection_metrics` 字段中；`validation` 保持 null，因为 val 列表仍为空。
如果显式用旧的非空 val 清单训练，仍按 val 指标选优；使用上一版固定轮数清单仍保存 `final.pt`。
新权重记录 `model_backend=original` 和原模型源码的 SHA-256；旧权重仍按其原实现加载，不能混用参数。

## 3. 复核选优集效果

训练完成后，重新加载同一运行目录的最佳权重，复核参与选优的两组工况：

```text
python -m ndp_tcn.evaluate --checkpoint ndp_tcn/results/train_YYYYMMDD_HHMMSS/best.pt --split test
```

指标包含各工况和总体 RMSE、MAE。误差越小越好，单位是 V/s，不是输出电压误差的 V。
报告标记 `role=model_selection`、`independent_test_result=false`，说明这是选优集复核。
当前须显式使用 `--split test`；默认 val 对当前空验证集会明确报错。
评价读取 checkpoint 内保存的划分，不用当前 JSON 覆盖旧模型的划分。
省略 `--output` 时自动保存为 `ndp_tcn/results/evaluate_test_YYYYMMDD_HHMMSS.json`，终端会显示实际路径。

## 4. 批量推理

推理根据历史信号生成预测，不计算训练梯度，也不读取标签 `y`：

```text
python -m ndp_tcn.predict --checkpoint ndp_tcn/results/train_YYYYMMDD_HHMMSS/best.pt --input-npz data/train_example_labeled/pulse_f210Hz_D10_P200to400W_L8_h1_residual.npz
```

这里使用测试工况 9（210 Hz / 10%）。脚本读取输入文件的 `X`、元数据和源时间，自动应用训练时保存的标准化参数。
每个窗口是按时间从旧到新排列的 8 个采样点，每点为前面约定的 9 个通道。

| 结果字段 | 含义 |
|---|---|
| `residual_V_per_s` | 每个窗口预测的单个扰动残差 |
| `future_disturbance_V_per_s` | 源时刻 `z2` 加上预测残差 |
| `source_z2_V_per_s`、`source_time_s` | 输入窗口末尾的观测值和时刻 |
| `target_start_time_s`、`target_end_time_s` | 预测目标区间的开始与结束时间 |

批量推理自动保存为 `ndp_tcn/results/predict_输入文件名主体_YYYYMMDD_HHMMSS.npz`；同秒重名自动避让。
兼容旧脚本时仍可显式填写训练的 `--output-dir` 或评价、推理的 `--output`，此时精确使用指定路径，不自动追加时间戳，且拒绝覆盖已有目标。

## 5. 用已有权重直接推理

当前已训练权重归档在 `E:\bisai\ndp_tcn\results\archive_20261031_201225\best.pt`，来自已完成的 8/2 选优实验。
如果只想体验预测，可以跳过训练，直接执行这一条独立命令：

```text
python -m ndp_tcn.predict --checkpoint ndp_tcn/results/archive_20261031_201225/best.pt --input-npz data/train_example_labeled/pulse_f210Hz_D10_P200to400W_L8_h1_residual.npz
```

这条命令使用已经训练好的当前模型。若要修改训练设置，运行前面的新训练命令并使用另一个结果目录。
归档来源是 `E:\bisai\runs\original_baseline_test_selection_20261031`，原目录保留；归档时间不表示重新训练时间。
归档文件保持原字节，config/checkpoint 中仍记录当时的输出路径，`archive_manifest.json` 保存复制来源与哈希。
旧 6/2/2 权重仍在原目录保留，修改划分 JSON 不会改变已有权重的实验来源。

## 6. 如何理解预测

预测输出先恢复为 V/s，再与输入窗口末尾的 `z2` 相加，得到目标区间的扰动估计。
当前标签 `y[k] = f_interval[k+1] - z2[k]`，其中
`f_interval[j] = (Vo[j+1]-Vo[j])/dt[j] - b0*IREF[j]`。
输入截至当前拍，目标是下一拍开始的区间 `[t[k+1], t[k+2])`。
`Vo、VREF、Vin` 单位 V；电流通道单位 A；`z2` 与输出残差单位 V/s。

这些工具执行预测，不直接输出 PWM 或替换电流 PI。后续闭环必须处理预测目标时间、执行延迟、限幅与超时回退。
已完成 FP32 ONNX 导出与 PC 一致性验证；TI 板端部署、闭环电压改善和 30 kHz 实时控制时限尚未验证。

## 7. 已有验证记录与备份

此前选优流程改动全部 40 项测试通过；新增测试核对按指定集合选择最低 RMSE 轮次，评价时不更新权重/BN 状态，以及训练数据和标准化隔离。
当前完整 test 选优训练已完成，现归档于 `E:\bisai\ndp_tcn\results\archive_20261031_201225`。
最多 50 轮、patience=10，实际第 16 轮早停，保留第 6 轮 `best.pt`；选优集工况平均 RMSE 为 4420.745 V/s，
全样本 RMSE 为 4423.745 V/s。已确认保存轮次对应全部训练记录中的最低分，重载后的平均 RMSE 差值为 0.0 V/s。
工况 9 的 CLI 推理生成 427 条预测；该目录的 `integration_verification.json`、`selection_recheck.json`
和 `case9_predictions.npz` 保存验证记录。这些是选优集成绩，不是独立测试成绩。

上一版 8/2 固定轮数流程使用真实数据完成了 1 轮、2 个训练 batch 的冒烟检查：原 `run.py` 正常保存 `final.pt`，
未生成 `best.pt` 或 `validation_metrics.json`；标准化只使用工况 1～8，权重重载及训练工况单窗口推理成功。
记录位于 `E:\bisai\runs\smoke_8train2test_20261031\integration_verification.json`。
该版全部 37 项测试通过，包含此前 32 项和新增的 5 项空验证集/训练/评价检查；旧 6/2/2 权重仍能加载。
当时仅验证固定轮数流程，未完成完整训练，也没有计算测试集指标。

以下是此前 6/2/2 划分的历史记录：

此前网络改动已通过全部 32 项测试，覆盖不同窗口长度、单样本梯度、输出和数据契约、
float32/float64 大小核融合及权重恢复，原多变量预测模式也通过针对性检查。
旧 baseline/dual 权重均能按其原实现加载。

已实际从本工程 `run.py` 完成训练，结果位于 `E:\bisai\runs\original_baseline_20261031`：
180193 个参数，16 轮后早停，最佳为第 6 轮；验证工况平均 RMSE 为 1757.51 V/s，
验证全部样本 RMSE 为 1178.89 V/s。重新加载最佳权重的工况平均 RMSE 差值小于 6e-9 V/s，
验证工况 6 的批量推理生成 899 条预测；未评价测试集。
此处是离线预测结果，不构成端侧实时性或闭环效果证明。
该目录的 `integration_verification.json` 保存历史集成验证记录，`best.pt` 是仍可加载的旧权重。

修改前备份：`E:\bisai\backups\20261031_185820_before_original_moderntcn_integration`，
15 个已有文件复制后均校验 SHA-256；本中文说明与新的原模型测试文件是本次新增文件。
恢复前先备份当前状态，再按照 `manifest.json` 逐文件恢复；保留对应源码版本的权重。
原始 MAT、已生成标签和之前的实验输出不需要随代码回退。

2026-10-31：将当前九通道单残差任务并入原 ModernTCN 主干及原运行入口。

2026-10-31：更新为 VS Code 集成终端的 `python ...` 使用流程，统一新实验目录，补充现有权重直接推理示例。
该次只改说明和终端约定，没有修改模型或重新训练。更新前 4 个文档文件已复制并核对 SHA-256，
备份位于 `E:\bisai\backups\20261031_193610_before_vscode_usage_docs`。
该次已在 TCN 环境核对训练、评价、推理三个模块以及原残差任务入口的 `--help`，均正常启动。
需要恢复说明时，先保存当前文档，再按该备份的 `manifest.json` 恢复相应文件。
完整数据约定、推理时间和历史实验说明见 [项目训练说明](../../../ndp_tcn/README_CN.md)。

2026-10-31：按完整工况改为 8 个训练、2 个测试；支持空验证集、固定轮数训练与 `final.pt`。
历史 6/2/2 清单保存在 `configs/ndp_tcn_split_legacy_6_2_2.json`（相对 `E:\bisai`）。
该次修改前备份为 `E:\bisai\backups\20261031_194938_before_train_test_4to1`，8 个已有文件已校验 SHA-256。
恢复前先保存当前版本，再按清单恢复划分配置、数据/训练/评价代码及中文说明，保留原始数据和已有权重。

2026-10-31：按用户要求逐轮用 test 中的工况 9、10 验证，按工况平均 RMSE 选 `best.pt`，恢复早停。
当前没有独立测试集，代码与结果显式记录 test 的选优角色；网络结构、标签和文件归属不变。
上一版固定轮数配置另存为 `configs/ndp_tcn_split_8_2_fixed_epochs.json`（相对 `E:\bisai`）。
本次修改前备份为 `E:\bisai\backups\20261031_195642_before_test_checkpoint_selection`，7 个已有文件已校验 SHA-256。
恢复前先保存当前版本，再按清单恢复配置、代码和中文说明；保留各版本的数据与权重。

2026-10-31：输出管理改为默认 `ndp_tcn/results` 加 UTC+08 时间戳，每次训练自动生成并更新中文实验 README。
新增 `ndp_tcn/outputs.py`，调整训练、评价、推理入口和中文说明；原网络结构、标签及当前 test 选优策略不变。
本次未重新执行完整训练；已有完整实验复制归档，8 个原文件已逐一验证 SHA-256 一致。
最新输出管理验证见 [结果目录说明](../../../ndp_tcn/results/README_CN.md)。
本次全部 50 项测试通过；原入口在子目录完成 1 轮、1 个训练 batch 的流程检查，默认路径正确，归档模型评价和 427 条批量推理均成功。
修改前备份为 `E:\bisai\backups\20261031_200929_before_timestamped_results`，7 个已有文件已核对哈希。
恢复前先保存当前文件，再按清单恢复对应入口与说明，并处理新增输出工具；保留数据及实验结果，不把代码恢复当作权重恢复。

2026-10-31：新增 `ndp_tcn/export_onnx.py`、`predict_onnx.py` 与可选依赖，使用现有原工程权重导出静态 FP32 ONNX，
默认保存到 `ndp_tcn/results/onnx_时间戳`，附部署契约、数值核验结果和中文说明。导出只融合模型副本，不修改原模型源码或训练 checkpoint。
入口为 `python -m ndp_tcn.export_onnx --checkpoint ndp_tcn/results/archive_20261031_201225/best.pt`，工作目录仍为 `E:\bisai`。
原 baseline 的 PC 导出和推理核验见 [ONNX 中文说明](../../../ndp_tcn/README_ONNX_CN.md)；
后续新网络的 TI 量化与硬 NPU 编译见 [TI 说明](../../../ndp_tcn/README_TI_NPU_CN.md)，板端运行和闭环接入尚未验证。
正式导出为 [onnx_20261031_203712](../../../ndp_tcn/results/onnx_20261031_203712/)，已检查 854 个窗口，
ONNX 与原 PyTorch 最大差值为 0.0391694033 V/s；本次全部 60 项测试通过。
修改前备份为 `E:\bisai\backups\20261031_203111_before_onnx_export`，5 个已有文件已核对哈希；新增文件单独记录，恢复前先保存当前版本。

2026-10-31：为绕开普通分组 FFN 与 GELU 的 TI NPU 映射限制，新增独立的标准 Conv2d/BN/ReLU/FC 后端。
在 `E:\bisai` 执行 `python -m ndp_tcn.train --backend ti_npu` 训练，自动保存为 `results/train_ti_npu_时间戳`（位于 ndp_tcn 内）。
原模型源码与旧权重保留作 baseline，新结构及实际实验/编译状态见 [TI NPU 说明](../../../ndp_tcn/README_TI_NPU_CN.md)。
本次修改前备份为 `E:\bisai\backups\20261031_204055_before_ti_npu_network`，15 个已有文件已核对哈希。
恢复前先保存当前版本，再恢复匹配的配置、加载及导出代码；不要混用不同结构的权重。
