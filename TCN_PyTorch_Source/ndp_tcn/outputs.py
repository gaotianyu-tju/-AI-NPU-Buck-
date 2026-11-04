"""统一结果目录、UTC+08 时间戳及中文实验配置说明。"""
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import math
from pathlib import Path
import re


RESULTS_ROOT = Path(__file__).resolve().parent / "results"
SINGAPORE = timezone(timedelta(hours=8), name="Asia/Singapore")


def now_singapore():
    """使用明确的 UTC+08 时区，不依赖机器时区或系统 tzdata。"""
    return datetime.now(timezone.utc).astimezone(SINGAPORE)


def _safe_prefix(prefix):
    prefix = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", str(prefix)).strip(" .")
    return prefix or "output"


def _candidate(root, stem, suffix, index):
    extra = f"_{index:02d}" if index else ""
    return root / f"{stem}{extra}{suffix}"


def create_run_directory(explicit=None, prefix="train"):
    """默认创建带时间戳的目录；显式路径保持原义，已有目录一律不覆盖。"""
    if explicit is not None:
        path = Path(explicit).resolve()
        path.mkdir(parents=True, exist_ok=False)
        return path
    root = Path(RESULTS_ROOT).resolve()
    root.mkdir(parents=True, exist_ok=True)
    stem = f"{_safe_prefix(prefix)}_{now_singapore():%Y%m%d_%H%M%S}"
    index = 0
    while True:
        path = _candidate(root, stem, "", index)
        try:
            path.mkdir()
            return path
        except FileExistsError:
            index += 1


@contextmanager
def open_result_file(explicit=None, *, prefix, suffix, binary=False):
    """原子创建结果文件，返回 (实际路径, 文件对象)；同秒冲突自动编号。"""
    if not isinstance(suffix, str) or not re.fullmatch(r"\.[A-Za-z0-9]+", suffix):
        raise ValueError("suffix must be one file extension such as .json or .npz.")
    mode = "xb" if binary else "x"
    options = {} if binary else {"encoding": "utf-8"}
    if explicit is not None:
        path = Path(explicit).resolve()
        if path.suffix.lower() != suffix.lower():
            raise ValueError(f"Output filename must end with {suffix}.")
        path.parent.mkdir(parents=True, exist_ok=True)
        stream = path.open(mode, **options)
    else:
        root = Path(RESULTS_ROOT).resolve()
        root.mkdir(parents=True, exist_ok=True)
        stem = f"{_safe_prefix(prefix)}_{now_singapore():%Y%m%d_%H%M%S}"
        index = 0
        while True:
            path = _candidate(root, stem, suffix, index)
            try:
                stream = path.open(mode, **options)
                break
            except FileExistsError:
                index += 1
    try:
        yield path, stream
    finally:
        # 保留写入失败时的现场；下一次自动输出会使用另一个名称。
        stream.close()


def _show(value):
    if value is None:
        return "未记录"
    if isinstance(value, bool):
        return "是" if value else "否"
    return str(value).replace("|", "\\|").replace("\n", " ")


def _table(rows):
    return ["| 配置项 | 值 |", "|---|---|"] + [f"| {key} | {_show(value)} |" for key, value in rows]


def write_run_readme(output_dir, run, history=None, checkpoint_name="best.pt"):
    """根据实际记录生成/更新本次运行的 README_CN.md，不虚构缺失的配置。"""
    directory = Path(output_dir).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    model = run.get("model_config", {})
    schema = run.get("data_schema", {})
    training = run.get("training", {})
    manifest = run.get("split_manifest", {})
    identities = run.get("data_identity", {})
    counts = run.get("sample_counts", {})
    backend = run.get("model_backend", training.get("backend"))
    ti_profile = backend in ("ti_npu", "ti_npu_fullconv")
    fullconv = backend == "ti_npu_fullconv"
    selection_split = run.get("selection_split", manifest.get("selection_split"))
    if "selection_split" not in run and "selection_split" not in manifest and manifest.get("val"):
        selection_split = "val"
    selection_enabled = run.get("selection_enabled", selection_split is not None)
    test_selected = bool(run.get("test_used_for_selection") or selection_split == "test")
    title = "# 本次 TI 时序 CNN 实验配置与结果" if ti_profile else "# 本次 ModernTCN 实验配置与结果"
    lines = [title, "",
             "本说明根据本次运行保存的配置与历史记录自动生成。", ""]
    if run.get("smoke_run"):
        lines += ["**本次仅为流程检查（smoke_run=true），不能作为完整训练性能结果。**", ""]
    if run.get("archive_source"):
        lines += [f"归档来源：`{run['archive_source']}`。",
                  "本目录时间戳表示归档时间，原始配置与权重中的训练路径保留原值；归档不是重新训练。", ""]
    if run.get("archive_note"):
        lines += [str(run["archive_note"]), ""]
    lines += ["## 1. 运行身份", ""] + _table([
        ("运行创建时间", run.get("created_at")),
        ("输出时间戳时区", run.get("output_timezone", "Asia/Singapore（UTC+08:00）")),
        ("说明更新时间", now_singapore().isoformat(timespec="seconds")),
        ("当前结果目录", directory),
        ("配置记录的训练输出目录", training.get("output_dir")),
        ("网络实现", run.get("model_backend", training.get("backend"))),
        ("网络版本", model.get("variant")),
        ("参数量", run.get("parameter_count")),
        ("PyTorch 版本", run.get("torch_version")),
        ("实际计算设备", run.get("device_used")),
        ("配置要求的设备", training.get("device")),
    ])
    lines += ["", "## 2. 输入、输出与网络", "",
              "输入按时间从旧到新排列，输出为一个带正负号的扰动残差。", "",
              "通道顺序：`" + ", ".join(schema.get("feature_names", [])) + "`。",
              "Vo、VREF、Vin 单位 V；ILA～ILD 和 IREF 单位 A；z2 与预测残差单位 V/s。",
              "IREF 是四相共用的每相电流参考，不乘 4。", ""]
    model_rows = [
        ("历史长度 L", schema.get("history_steps", model.get("seq_len"))),
        ("输入通道数", model.get("in_channels")),
        ("预测区间起点步距 h", schema.get("horizon_steps_to_target_interval_start")),
        ("采样间隔（s）", schema.get("sample_interval_s")),
        ("b0（每相参考约定）", schema.get("b0_per_phase")),
        ("标签定义", schema.get("label_definition")),
        ("卷积通道数" if ti_profile else "特征维度 d_model", model.get("d_model")),
        ("有效时间卷积层数" if ti_profile else "单 stage 中 Block 数", model.get("num_blocks")),
        ("联合回归头中间维度", model.get("head_hidden")),
    ]
    if ti_profile:
        model_rows += [
            ("核心输入布局", f"[B,{_show(model.get('padded_channels'))},{_show(model.get('seq_len'))},1] NCHW"),
            ("时间卷积核", f"({_show(model.get('kernel_size'))},1)"),
            ("卷积 groups / stride / padding", "1 / 1 / 0"),
            ("隐藏激活 / 输出激活", "ReLU / 无（保留正负残差）"),
        ]
    else:
        model_rows += [
            ("FFN 比例", model.get("ffn_ratio")),
            ("大核 / 小核", f"{_show(model.get('large_kernel'))} / {_show(model.get('small_kernel'))}"),
            ("patch 大小 / 步长", f"{_show(model.get('patch_size'))} / {_show(model.get('patch_stride'))}"),
            ("Dropout", model.get("dropout")),
        ]
    lines += _table(model_rows)
    if fullconv:
        lines += ["", "本次为全卷积 TI 网络，输入仍为九路信号和原历史长度，不增加物理特征。",
                  "标准化后补齐到12路；核心只保留卷积及激活，不含 Flatten/Linear。",
                  "两层卷积回归头替代旧全连接头，导出直接返回[B,4,1,1]，有效输出通道为0；训练/评价在导出核心外选择该通道。",
                  "FP32结构不是NPU执行证明，必须通过专用NNC硬件映射检查；任何网络层CPU回退均不合格。",
                  "NPU启动、中断和输入输出转换的主机开销单独披露，板端输出和30kHz时限需实测。"]
    elif ti_profile:
        lines += ["", "本次为 TI 层配置约束下重新训练的时序 CNN，不是原 ModernTCN 权重的等价算子替换。",
                  "先按原 scaler 标准化九路信号，再重排为 NCHW，并补三个标准化零通道；补零和重排在导出核心图外执行。",
                  "核心为 Conv2d + BatchNorm2d + ReLU 堆叠，随后 Flatten、Linear、ReLU、Linear；末层保留正负输出。",
                  "本训练说明只记录 FP32 结构与训练结果，不能据此声称 TI 专用量化、NNC 编译、板端运行或时限已通过。"]
    lines += ["", "标签为 `y[k] = f_interval[k+h] - z2[k]`，其中",
              "`f_interval[j] = (Vo[j+1]-Vo[j])/dt[j] - b0*IREF[j]`。",
              "预测目标是 `[t[k+h], t[k+h+1])` 区间；输入窗口截至源时刻 k。",
              "输入与标签分别使用训练工况拟合的固定标准化参数；推理自动恢复物理单位。", "",
              "## 3. 数据划分与模型选择", "",
              f"数据目录：`{_show(training.get('data_dir'))}`。",
              f"划分配置：`{_show(training.get('split'))}`，本实验具体归属以 config.json 保存的清单为准。", "",
              "| 集合 | 工况编号 | 文件数 | 窗口数 |", "|---|---|---:|---:|"]
    for split in ("train", "val", "test"):
        names = manifest.get(split, [])
        case_ids = [identities.get(name, identities.get(Path(name).name, {})).get("case_id") for name in names]
        ids = "、".join(_show(value) for value in case_ids) if names else "无"
        n = counts.get(split, counts.get("selection") if split == selection_split else None)
        if not names:
            n = 0
        lines.append(f"| {split} | {ids} | {len(names)} | {_show(n)} |")
    lines += ["", f"选优集合：`{selection_split}`；策略：`{_show(run.get('selection_policy'))}`。"]
    if test_selected:
        lines += ["名为 test 的集合参与逐轮评价、checkpoint 选择与早停，实际承担验证/选优作用。",
                  "**这些分数不是独立测试成绩。** 梯度更新和标准化拟合仍只使用 train。"]
    elif selection_enabled:
        lines += ["根据验证工况 RMSE 的算术平均选择模型；测试集合不参与此选优流程。"]
    else:
        lines += ["本次未设置选优集合，按预设轮数训练并保留最后一轮；不依据训练损失挑选最佳轮次。"]
    if selection_enabled:
        lines += ["选优指标为各工况 RMSE 的算术平均，越小越好，单位 V/s。"]
    lines += ["", "## 4. 训练配置", ""] + _table([
        ("优化器", training.get("optimizer", "AdamW（当前训练实现）")),
        ("损失函数", training.get("loss")),
        ("学习率", training.get("lr")),
        ("Weight decay", training.get("weight_decay")),
        ("Batch size", training.get("batch_size")),
        ("预设最多轮数", training.get("epochs")),
        ("早停 patience", training.get("patience") if selection_enabled else "不启用（固定轮数）"),
        ("采样方式", training.get("sampling")),
        ("随机种子", training.get("seed")),
        ("CPU 线程数", training.get("threads")),
        ("每轮批数上限（流程检查）", "不限制（完整训练）" if "max_train_batches" in training and training["max_train_batches"] is None else training.get("max_train_batches")),
    ])
    if training.get("loss") == "weighted_huber":
        lines += [f"", f"瞬态权重系数：{_show(training.get('transient_weight'))}。"]
    lines += ["", "## 5. 实际运行结果", ""]
    if history is None:
        lines += ["这是训练开始阶段的配置记录，结束摘要尚未写入。"]
    elif not history:
        lines += ["尚无已完成轮次记录。"]
    else:
        lines += [f"实际记录轮数：**{len(history)}**。"]
        candidates = []
        for item in history:
            metrics = item.get("selection_metrics") or item.get("validation")
            score = metrics.get("macro_rmse_V_per_s") if metrics else None
            if isinstance(score, (int, float)) and math.isfinite(score):
                candidates.append((score, item))
        chosen = min(candidates, key=lambda pair: pair[0])[1] if selection_enabled and candidates else None
        if selection_enabled and chosen is not None:
            metrics = chosen.get("selection_metrics") or chosen["validation"]
            lines += [f"最佳轮次：**{_show(chosen.get('epoch'))}**。",
                      f"选优集工况平均 RMSE：**{metrics['macro_rmse_V_per_s']:.6f} V/s**。",
                      f"该轮全部评价样本的 RMSE：{_show(metrics.get('rmse_V_per_s'))} V/s。"]
        elif selection_enabled:
            lines += ["历史中没有可核对的有效选优指标，不能确定最佳轮次。"]
        else:
            lines += [f"保存最后记录轮次：**{_show(history[-1].get('epoch'))}**。"]
        lines += [f"模型文件名：`{checkpoint_name}`。"]
    lines += ["", "## 6. 文件与来源", ""]
    for name, purpose in (
        (checkpoint_name, "模型配置、权重和标准化参数"),
        ("config.json", "完整实验配置、数据身份、模型源码哈希与选优策略"),
        ("scalers.json", "仅从训练工况拟合的标准化参数"),
        ("history.json", "每轮训练与选优记录"),
        ("selection_metrics.json", "最佳轮次的选优指标"),
        ("validation_metrics.json", "实际 val 模式下的最佳指标"),
        ("selection_recheck.json", "重新加载模型后的选优集复核"),
        ("integration_verification.json", "已执行的集成验证记录"),
    ):
        if (directory / name).is_file():
            lines.append(f"- [{name}]({name})：{purpose}。")
    lines += ["", f"网络源码 SHA-256：`{_show(run.get('model_source_sha256'))}`。",
              "原始工况 SHA-256 与文件清单保存在 config.json 的 data_identity 和 split_manifest 中。",
              "本说明描述离线网络实验；不据此声称已完成 Simulink 闭环、ONNX 或端侧实时性验证。", ""]
    if (directory / checkpoint_name).is_file() and selection_split in ("val", "test"):
        data_option = (f' --data-dir "{Path(training["data_dir"]).as_posix()}"'
                       if training.get("data_dir") else "")
        lines += ["在 VS Code 终端、项目根目录 E:\\bisai 中复核本次模型：", "", "```text",
                  f'python -m ndp_tcn.evaluate --checkpoint "{(directory / checkpoint_name).as_posix()}"{data_option} --split {selection_split}',
                  "```", "", "省略 --output 时，复核结果自动写入 ndp_tcn/results 中带时间戳的新文件。", ""]
    path = directory / "README_CN.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
