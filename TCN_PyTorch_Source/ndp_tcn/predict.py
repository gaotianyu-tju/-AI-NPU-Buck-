"""从历史窗口推理，输出物理残差、未来扰动及目标区间；不生成控制指令。"""
import argparse
from collections import deque
import hashlib
import json
from pathlib import Path

import numpy as np
import torch

from .data import Scalers
from .metrics import predict_array
from .model import build_model, load_model_config, model_source
from .outputs import open_result_file


FEATURE_NAMES = ("Vo", "ILA", "ILB", "ILC", "ILD", "VREF", "IREF", "z2", "Vin")


class ResidualPredictor:
    def __init__(self, checkpoint_path, device="cpu"):
        self.device = torch.device(device)
        self.checkpoint = torch.load(checkpoint_path, map_location=self.device, weights_only=True)
        if self.checkpoint.get("checkpoint_version") != 1:
            raise ValueError("Unsupported checkpoint version.")
        # 之前的权重没有 backend 字段，仍使用它们实际训练时的实现。
        self.backend = self.checkpoint.get("model_backend", "legacy")
        recorded_backend = self.checkpoint.get("run", {}).get("model_backend", self.backend)
        if recorded_backend != self.backend:
            raise ValueError("Checkpoint model backend does not match its training record.")
        expected_hash = self.checkpoint.get("run", {}).get("model_source_sha256")
        actual_hash = hashlib.sha256(model_source(self.backend).read_bytes()).hexdigest()
        if expected_hash != actual_hash:
            raise ValueError("Model implementation differs from checkpoint; restore the matching source before loading.")
        self.schema = self.checkpoint["data_schema"]
        if tuple(self.schema["feature_names"]) != FEATURE_NAMES:
            raise ValueError("Checkpoint feature order does not match the nine-channel contract.")
        if self.schema["label_definition"] != "interval_residual_v1" or self.schema["label_unit"] != "V/s":
            raise ValueError("Unsupported target definition/unit.")
        self.config = load_model_config(self.checkpoint["model_config"], self.backend)
        if self.schema["history_steps"] != self.config.seq_len:
            raise ValueError("Checkpoint history length mismatch.")
        self.scalers = Scalers.from_dict(self.checkpoint["scalers"])
        self.model = build_model(self.config, backend=self.backend,
                                 merged=self.checkpoint.get("merged", False))
        self.model.load_state_dict(self.checkpoint["model_state_dict"], strict=True)
        self.model.to(self.device).eval()
        self.history = deque(maxlen=self.config.seq_len)
        self.last_source_time = None

    def validate_schema(self, metadata):
        for key in ("feature_names", "history_steps", "horizon_steps_to_target_interval_start", "label_definition"):
            observed = list(metadata[key]) if key == "feature_names" else metadata[key]
            if observed != self.schema[key]:
                raise ValueError(f"Input metadata differs from checkpoint: {key}")
        if not np.isclose(metadata["sample_interval_s"], self.schema["sample_interval_s"], rtol=1e-5, atol=1e-12):
            raise ValueError("Input sample interval differs from checkpoint.")
        if not np.isclose(metadata["b0_per_phase"], self.schema["b0_per_phase"], rtol=1e-9, atol=1e-12):
            raise ValueError("Input b0/per-phase reference convention differs from checkpoint.")

    def predict(self, window, source_time_s=None, source_step=None):
        window = np.asarray(window, dtype=np.float32)
        if window.shape != (self.config.seq_len, 9) or not np.isfinite(window).all():
            raise ValueError(f"Expected a finite [{self.config.seq_len},9] raw window.")
        if source_time_s is not None and not np.isfinite(source_time_s):
            raise ValueError("Source timestamp must be finite.")
        residual = float(predict_array(self.model, self.scalers, window[None], 1, self.device)[0, 0])
        source_z2 = float(window[-1, 7])
        h = int(self.schema["horizon_steps_to_target_interval_start"])
        dt = float(self.schema["sample_interval_s"])
        return {
            "residual_V_per_s": residual,
            "future_disturbance_V_per_s": source_z2+residual,
            "source_z2_V_per_s": source_z2,
            "source_time_s": source_time_s,
            "target_start_time_s": None if source_time_s is None else source_time_s+h*dt,
            "target_end_time_s": None if source_time_s is None else source_time_s+(h+1)*dt,
            "source_step": source_step,
            "target_step": None if source_step is None else source_step+h,
        }

    def reset(self):
        self.history.clear()
        self.last_source_time = None

    def push(self, sample, source_time_s, source_step=None):
        """Python 旁路/离线回放用的滚动窗口；不代表硬实时控制中断实现。"""
        sample = np.asarray(sample, dtype=np.float32)
        if sample.shape != (9,) or not np.isfinite(sample).all() or not np.isfinite(source_time_s):
            self.reset()
            raise ValueError("Invalid online sample/timestamp; history was reset.")
        dt = float(self.schema["sample_interval_s"])
        if self.last_source_time is not None and not np.isclose(
                source_time_s-self.last_source_time, dt, rtol=1e-4, atol=1e-10):
            self.reset()
        self.history.append(sample.copy())
        self.last_source_time = float(source_time_s)
        if len(self.history) < self.config.seq_len:
            return None
        return self.predict(np.stack(self.history), float(source_time_s), source_step)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--checkpoint", type=Path, required=True)
    p.add_argument("--input-npz", type=Path, required=True)
    p.add_argument("--output", type=Path, default=None,
                   help="省略时在 ndp_tcn/results 自动生成带时间戳的 NPZ 文件")
    p.add_argument("--batch-size", type=int, default=256)
    p.add_argument("--threads", type=int, default=2)
    args = p.parse_args()
    if args.output is not None and (args.output.suffix.lower() != ".npz" or args.output.exists()):
        raise ValueError("Use a new .npz output filename.")
    if args.batch_size < 1 or args.threads < 1:
        raise ValueError("batch-size and threads must be positive.")
    torch.set_num_threads(args.threads)
    predictor = ResidualPredictor(args.checkpoint)
    with np.load(args.input_npz, allow_pickle=False) as data:
        predictor.validate_schema(json.loads(str(data["metadata_json"].item())))
        x = data["X"]
        times = data["source_time_s"]
        if x.ndim != 3 or x.shape[1:] != (predictor.config.seq_len, 9) or not np.isfinite(x).all():
            raise ValueError("Invalid input windows.")
        if times.shape != (len(x),) or not np.isfinite(times).all():
            raise ValueError("Invalid source timestamps.")
        # 推理接口只读取历史 X 与元数据/时间，不读取标签 y。
        residual = predict_array(predictor.model, predictor.scalers, x, args.batch_size, predictor.device)
        future = residual[:, 0]+x[:, -1, 7]
    dt = predictor.schema["sample_interval_s"]
    h = predictor.schema["horizon_steps_to_target_interval_start"]
    with open_result_file(args.output, prefix=f"predict_{args.input_npz.stem}",
                          suffix=".npz", binary=True) as (output_path, stream):
        np.savez_compressed(stream, residual_V_per_s=residual,
                            future_disturbance_V_per_s=future,
                            source_z2_V_per_s=x[:, -1, 7], source_time_s=times,
                            target_start_time_s=times+h*dt, target_end_time_s=times+(h+1)*dt,
                            checkpoint=np.asarray(str(args.checkpoint.resolve())))
    print(f"Saved {len(x)} predictions: {output_path}")
    return output_path


if __name__ == "__main__":
    main()
