"""按完整工况训练；根据清单显式指定的集合评价并选择 checkpoint。"""
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import random
import time

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler

from .data import Scalers, NPZWindows, load_splits, read_case_metadata
from .metrics import evaluate_model
from .model import ResidualConfig, TiNpuConfig, TiNpuFullConvConfig, build_model, model_source
from .outputs import create_run_directory, now_singapore, write_run_readme

ROOT = Path(__file__).resolve().parents[1]


def dump_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def resolve_selection_split(manifest):
    """旧清单保留原行为；只有显式 selection_split=test 才用测试槽位选优。"""
    selection_split = manifest.get("selection_split", "val" if manifest.get("val") else None)
    if selection_split not in (None, "val", "test"):
        raise ValueError("selection_split must be 'val', 'test', or null.")
    if selection_split is not None and not manifest.get(selection_split):
        raise ValueError(f"The configured selection split '{selection_split}' is empty.")
    return selection_split


def target_changes(cases):
    """仅离线损失使用：目标区间扰动变化，不送入网络输入。"""
    changes = []
    for case in cases:
        f = case.y[:, 0].astype(float) + np.asarray(case.source_z2).reshape(-1)
        change = np.zeros(len(f), dtype=np.float64)
        if len(f) > 1:
            contiguous = np.isclose(np.diff(case.target_start),
                                    case.metadata["sample_interval_s"], rtol=1e-4, atol=1e-10)
            change[1:] = np.where(contiguous, np.abs(np.diff(f)), 0.0)
        changes.append(change)
    return np.concatenate(changes)


class LossWeightedWindows(Dataset):
    def __init__(self, base, weights):
        self.base, self.weights = base, torch.as_tensor(weights, dtype=torch.float32)

    def __len__(self):
        return len(self.base)

    def __getitem__(self, index):
        x, y, case_index = self.base[index]
        return x, y, case_index, self.weights[index]


def train(args):
    if args.epochs < 1 or args.batch_size < 1 or args.patience < 1 or args.threads < 1:
        raise ValueError("epochs, batch_size, patience and threads must be positive.")
    if args.max_train_batches is not None and args.max_train_batches < 1:
        raise ValueError("max_train_batches must be positive.")
    if args.transient_weight < 0:
        raise ValueError("transient_weight must be nonnegative.")
    torch.set_num_threads(args.threads)
    torch.manual_seed(args.seed)
    random.seed(args.seed)
    np.random.seed(args.seed)
    device = torch.device("cuda" if args.device == "auto" and torch.cuda.is_available()
                          else "cpu" if args.device == "auto" else args.device)
    manifest = json.loads(args.split.read_text(encoding="utf-8-sig"))
    selection_split = resolve_selection_split(manifest)
    test_used_for_selection = selection_split == "test"
    splits = load_splits(args.data_dir, manifest, include_test=test_used_for_selection)
    train_cases, val_cases = splits["train"], splits["val"]
    selection_cases = splits[selection_split] if selection_split is not None else []
    selection_enabled = bool(selection_cases)
    validation_enabled = selection_split == "val"
    selection_policy = ("test_macro_rmse" if test_used_for_selection else
                        "validation_macro_rmse" if validation_enabled else "fixed_epochs")
    checkpoint_name = "best.pt" if selection_enabled else "final.pt"
    scalers = Scalers.fit(train_cases)
    base = NPZWindows(train_cases, scalers)
    changes = target_changes(train_cases)
    weight_scale = max(float(np.quantile(changes, .95)), 1e-8)
    weights = (1.0 + args.transient_weight * np.clip(changes/weight_scale, 0, 1)
               if args.loss == "weighted_huber" else np.ones(len(base)))
    dataset = LossWeightedWindows(base, weights)
    generator = torch.Generator().manual_seed(args.seed)
    sampler = (WeightedRandomSampler(torch.as_tensor(base.sample_weights, dtype=torch.double),
                                      len(base), replacement=True, generator=generator)
               if args.sampling == "case" else None)
    loader = DataLoader(dataset, batch_size=args.batch_size, sampler=sampler,
                        shuffle=sampler is None, num_workers=0, drop_last=False,
                        generator=generator)
    seq_len = train_cases[0].X.shape[1]
    if args.backend in ("ti_npu", "ti_npu_fullconv"):
        config_type = TiNpuFullConvConfig if args.backend == "ti_npu_fullconv" else TiNpuConfig
        config = config_type(seq_len=seq_len, d_model=args.ti_width,
                             num_blocks=args.ti_blocks, kernel_size=args.ti_kernel,
                             head_hidden=args.ti_head_hidden)
    else:
        config = ResidualConfig(seq_len=seq_len, variant=args.variant,
                                d_model=args.d_model, num_blocks=args.blocks,
                                large_kernel=args.large_kernel, small_kernel=3,
                                patch_size=args.patch_size, patch_stride=args.patch_stride,
                                short_len=min(args.short_len, seq_len),
                                short_channels=args.d_model, dropout=args.dropout)
    model = build_model(config, backend=args.backend).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    criterion = (nn.MSELoss(reduction="none") if args.loss == "mse"
                 else nn.HuberLoss(delta=1.0, reduction="none"))
    args.output_dir = create_run_directory(args.output_dir,
                                           prefix=f"train_{args.backend}" if args.backend.startswith("ti_npu") else "train")
    checkpoint_path = args.output_dir/checkpoint_name
    print(f"Output directory: {args.output_dir}", flush=True)
    metadata = train_cases[0].metadata
    schema = {
        "feature_names": list(metadata["feature_names"]),
        "history_steps": seq_len,
        "horizon_steps_to_target_interval_start": metadata["horizon_steps_to_target_interval_start"],
        "sample_interval_s": metadata["sample_interval_s"],
        "b0_per_phase": metadata["b0_per_phase"],
        "label_definition": metadata["label_definition"],
        "label_unit": "V/s",
        "input_timing": "window ends after current IREF and z2 have been computed; prediction targets a subsequent interval",
    }
    identities = {}
    for split_name in ("train", "val", "test"):
        for filename in manifest[split_name]:
            identity = read_case_metadata(args.data_dir/filename)
            identities[filename] = {"case_id": identity["case_id"],
                                    "source_sha256": identity["source_sha256"]}
    run = {
        "created_at": now_singapore().isoformat(timespec="seconds"),
        "output_timezone": "Asia/Singapore",
        "output_directory": str(args.output_dir),
        "device_used": str(device),
        "sample_counts": {"train": len(base), "selection": sum(len(case.X) for case in selection_cases)},
        "model_config": asdict(config), "data_schema": schema,
        "training": {k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()},
        "parameter_count": sum(p.numel() for p in model.parameters()),
        "model_backend": args.backend,
        "model_source_sha256": hashlib.sha256(model_source(args.backend).read_bytes()).hexdigest(),
        "split_manifest": manifest, "data_identity": identities,
        "torch_version": str(torch.__version__),
        "train_files": [str(c.path) for c in train_cases],
        "val_files": [str(c.path) for c in val_cases],
        "validation_enabled": validation_enabled,
        "selection_enabled": selection_enabled,
        "selection_split": selection_split,
        "selection_files": [str(c.path) for c in selection_cases],
        "selection_policy": selection_policy,
        "test_used_for_selection": test_used_for_selection,
        "independent_test_available": bool(manifest["test"]) and not test_used_for_selection,
        "transient_change_scale_V_per_s": weight_scale,
        "smoke_run": args.max_train_batches is not None,
        "test_evaluated": False,
    }
    dump_json(args.output_dir/"config.json", run)
    dump_json(args.output_dir/"scalers.json", scalers.to_dict())
    write_run_readme(args.output_dir, run, checkpoint_name=checkpoint_name)
    best, bad_epochs, history = float("inf"), 0, []
    if test_used_for_selection:
        print("The named test split is used for per-epoch checkpoint selection; "
              "its results have a validation role, not an independent-test role.", flush=True)
    elif not selection_enabled:
        print(f"No validation split: training for {args.epochs} fixed epochs; "
              "patience is ignored; saving final.pt; test is held out.", flush=True)
    for epoch in range(1, args.epochs+1):
        started = time.perf_counter()
        model.train()
        numerator, denominator, steps = 0.0, 0.0, 0
        for x, y, _, weight in loader:
            x, y, weight = x.to(device), y.to(device), weight.to(device)
            optimizer.zero_grad(set_to_none=True)
            pred = model(x)
            per_sample = criterion(pred, y).mean(dim=1)
            loss = (per_sample*weight).sum()/weight.sum()
            if not torch.isfinite(loss):
                raise RuntimeError("Non-finite training loss.")
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0, error_if_nonfinite=True)
            optimizer.step()
            numerator += float((per_sample.detach()*weight).sum().cpu())
            denominator += float(weight.sum().cpu())
            steps += 1
            if args.max_train_batches is not None and steps >= args.max_train_batches:
                break
        selection_metrics = (evaluate_model(model, selection_cases, scalers, args.batch_size, device)
                             if selection_enabled else None)
        if selection_enabled:
            selection_metrics.update({"split": selection_split, "role": "model_selection",
                                      "used_for_checkpoint_selection": True,
                                      "independent_test_result": False})
        if test_used_for_selection and not run["test_evaluated"]:
            # Only set this after evaluation has actually completed.
            run["test_evaluated"] = True
            dump_json(args.output_dir/"config.json", run)
        score = selection_metrics["macro_rmse_V_per_s"] if selection_enabled else None
        if selection_enabled and not np.isfinite(score):
            raise RuntimeError("Non-finite checkpoint-selection metric.")
        val = selection_metrics if validation_enabled else None
        record = {"epoch": epoch, "train_loss_normalized": numerator/denominator,
                  "train_batches": steps, "validation": val,
                  "selection_split": selection_split, "selection_metrics": selection_metrics,
                  "seconds": time.perf_counter()-started}
        history.append(record)
        dump_json(args.output_dir/"history.json", history)
        save_checkpoint = score < best if selection_enabled else epoch == args.epochs
        if save_checkpoint:
            checkpoint = {"checkpoint_version": 1, "model_config": asdict(config),
                          "model_backend": args.backend,
                          "model_state_dict": model.state_dict(), "scalers": scalers.to_dict(),
                          "data_schema": schema, "epoch": epoch, "validation": val,
                          "selection_policy": selection_policy,
                          "selection_split": selection_split, "selection_metrics": selection_metrics,
                          "test_used_for_selection": test_used_for_selection,
                          "test_evaluated": run["test_evaluated"],
                          "independent_test_available": run["independent_test_available"],
                          "run": run}
            torch.save(checkpoint, checkpoint_path)
        if selection_enabled:
            if save_checkpoint:
                best, bad_epochs = score, 0
                dump_json(args.output_dir/"selection_metrics.json", selection_metrics)
                if validation_enabled:
                    dump_json(args.output_dir/"validation_metrics.json", val)
            else:
                bad_epochs += 1
        metric_name = "test_for_selection_macro_RMSE" if test_used_for_selection else "val_macro_RMSE"
        validation_log = f"{metric_name}={score:.3f} V/s " if selection_enabled else ""
        print(f"epoch={epoch} loss={record['train_loss_normalized']:.6f} "
              f"{validation_log}elapsed={record['seconds']:.2f}s", flush=True)
        if selection_enabled and bad_epochs >= args.patience:
            break
    test_status = ("test evaluated for checkpoint selection, not independent testing"
                   if run["test_evaluated"] else "test not evaluated")
    write_run_readme(args.output_dir, run, history=history, checkpoint_name=checkpoint_name)
    print(f"Saved: {checkpoint_path}; parameters={run['parameter_count']}; {test_status}.")
    return checkpoint_path


def parser(original_only=False):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data-dir", type=Path, default=ROOT/"data"/"train_example_labeled")
    p.add_argument("--split", type=Path, default=ROOT/"configs"/"ndp_tcn_split.json")
    p.add_argument("--output-dir", type=Path, default=None,
                   help="省略时自动创建 ndp_tcn/results/train_时间戳；指定时使用该精确目录")
    if original_only:
        p.set_defaults(backend="original", variant="baseline", short_len=4)
    else:
        p.add_argument("--backend", choices=["original", "legacy", "ti_npu", "ti_npu_fullconv"], default="original",
                       help="original 为原 ModernTCN；legacy 复现旧实验；ti_npu 为旧CNN；ti_npu_fullconv 为全卷积候选")
        p.add_argument("--variant", choices=["baseline", "dual"], default="baseline")
    p.add_argument("--ti-width", type=int, default=16, help="ti_npu 的卷积通道数，须为 4 的倍数")
    p.add_argument("--ti-blocks", type=int, default=2, help="ti_npu 的有效卷积层数")
    p.add_argument("--ti-kernel", type=int, default=3, help="ti_npu 时间卷积核长度")
    p.add_argument("--ti-head-hidden", type=int, default=16, help="TI 回归隐藏宽度；全卷积后端须为4的倍数")
    p.add_argument("--epochs", type=int, default=100)
    p.add_argument("--patience", type=int, default=20,
                   help="按清单指定的选优集指标早停；没有选优集时按 epochs 固定训练")
    p.add_argument("--batch-size", type=int, default=128)
    p.add_argument("--lr", type=float, default=.001)
    p.add_argument("--weight-decay", type=float, default=.0001)
    p.add_argument("--loss", choices=["mse", "huber", "weighted_huber"], default="mse")
    p.add_argument("--transient-weight", type=float, default=3.0)
    p.add_argument("--sampling", choices=["case", "uniform"], default="case")
    p.add_argument("--d-model", type=int, default=32)
    p.add_argument("--blocks", type=int, default=2)
    p.add_argument("--large-kernel", type=int, default=7)
    p.add_argument("--patch-size", type=int, default=4)
    p.add_argument("--patch-stride", type=int, default=2)
    if not original_only:
        p.add_argument("--short-len", type=int, default=4)
    p.add_argument("--dropout", type=float, default=.1)
    p.add_argument("--seed", type=int, default=2026)
    p.add_argument("--device", choices=["cpu", "cuda", "auto"], default="auto")
    p.add_argument("--threads", type=int, default=2)
    p.add_argument("--max-train-batches", type=int, default=None,
                   help="仅冒烟验证时限制每轮训练批数；配置的选优集仍完整评价")
    return p


if __name__ == "__main__":
    train(parser().parse_args())
