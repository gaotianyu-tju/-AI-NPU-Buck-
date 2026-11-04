"""显式评价所选工况，并记录该集合是否已经用于 checkpoint 选择。"""
import argparse
import json
from pathlib import Path

import torch

from .data import load_splits
from .metrics import evaluate_model
from .predict import ResidualPredictor
from .outputs import open_result_file


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--checkpoint", type=Path, required=True)
    p.add_argument("--data-dir", type=Path,
                   default=Path(__file__).resolve().parents[1]/"data"/"train_example_labeled")
    p.add_argument("--split", choices=["train", "val", "test"], default="val")
    p.add_argument("--output", type=Path, default=None,
                   help="省略时在 ndp_tcn/results 自动生成带时间戳的 JSON 文件")
    p.add_argument("--batch-size", type=int, default=256)
    p.add_argument("--threads", type=int, default=2)
    args = p.parse_args()
    if args.output is not None and args.output.exists():
        raise FileExistsError("Choose a new metrics output path.")
    if args.batch_size < 1 or args.threads < 1:
        raise ValueError("batch-size and threads must be positive.")
    torch.set_num_threads(args.threads)
    predictor = ResidualPredictor(args.checkpoint)
    manifest = predictor.checkpoint["run"]["split_manifest"]
    if args.split == "val" and not manifest.get("val"):
        raise ValueError("This checkpoint has no validation split. "
                         "Use --split test for the named test split (check its model-selection role), "
                         "or --split train for training-set diagnostics.")
    splits = load_splits(args.data_dir, manifest, include_test=args.split == "test")
    if not splits[args.split]:
        raise ValueError(f"The requested {args.split} split is empty.")
    for case in splits[args.split]:
        predictor.validate_schema(case.metadata)
        expected = predictor.checkpoint["run"]["data_identity"][case.path.name]
        if (case.metadata["case_id"] != expected["case_id"] or
                case.metadata["source_sha256"] != expected["source_sha256"]):
            raise ValueError(f"Case identity differs from saved experiment: {case.path.name}")
    report = evaluate_model(predictor.model, splits[args.split], predictor.scalers,
                            args.batch_size, predictor.device)
    run = predictor.checkpoint["run"]
    selection_split = run.get("selection_split", predictor.checkpoint.get("selection_split"))
    # Old checkpoints predate explicit selection metadata and used validation when present.
    if selection_split is None and predictor.checkpoint.get("validation") is not None:
        selection_split = "val"
    test_used_for_selection = bool(run.get("test_used_for_selection", False)
                                   or selection_split == "test")
    used_for_selection = args.split == selection_split
    independent_test_result = args.split == "test" and not test_used_for_selection
    role = ("model_selection" if used_for_selection else "independent_test"
            if independent_test_result else "training_diagnostic" if args.split == "train" else "evaluation")
    report.update({"split": args.split, "checkpoint": str(args.checkpoint.resolve()),
                   "smoke_checkpoint": run.get("smoke_run", False),
                   "role": role, "selection_split": selection_split,
                   "used_for_checkpoint_selection": used_for_selection,
                   "test_used_for_selection": test_used_for_selection,
                   "independent_test_result": independent_test_result})
    with open_result_file(args.output, prefix=f"evaluate_{args.split}",
                          suffix=".json") as (output_path, stream):
        json.dump(report, stream, ensure_ascii=False, indent=2)
    print(f"{args.split} ({role}): macro RMSE={report['macro_rmse_V_per_s']:.3f} V/s; saved {output_path}")
    return output_path


if __name__ == "__main__":
    main()
