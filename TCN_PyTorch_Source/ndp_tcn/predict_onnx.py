"""用 ONNX Runtime 在 PC 回放原始九通道窗口；不依赖 PyTorch，不是 C28x 固件。"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from .outputs import open_result_file


FEATURE_NAMES = ("Vo", "ILA", "ILB", "ILC", "ILD", "VREF", "IREF", "z2", "Vin")
CONTRACT_KEY = "ndp_tcn_contract"


def pack_normalized_numpy(windows, padded_channels=12):
    """CPU 上把已标准化 BL9 窗口转成 NCHW，新增的三个通道为标准化零。"""
    windows = np.asarray(windows)
    if (windows.ndim != 3 or windows.shape[2] != 9 or len(windows) == 0 or windows.shape[1] < 1
            or padded_channels != 12 or not np.isfinite(windows).all()):
        raise ValueError("TI packing requires finite normalized [N,L,9] windows and 12 channels.")
    packed = np.zeros((len(windows), padded_channels, windows.shape[1], 1), dtype=np.float32)
    packed[:, :9, :, 0] = windows.transpose(0, 2, 1)
    if not np.isfinite(packed).all():
        raise ValueError("Packed input exceeds float32 range.")
    return packed


class OnnxResidualPredictor:
    """接受物理信号窗口，外部标准化后执行固定 batch=1 图，再恢复 V/s。"""

    def __init__(self, model_path, threads=2):
        if threads < 1:
            raise ValueError("threads must be positive.")
        try:
            import onnxruntime as ort
        except ImportError as exc:
            raise ImportError("Install the PC runtime: python -m pip install onnxruntime") from exc
        self.model_path = Path(model_path).resolve()
        options = ort.SessionOptions()
        options.intra_op_num_threads = threads
        options.inter_op_num_threads = 1
        self.session = ort.InferenceSession(str(self.model_path), sess_options=options,
                                           providers=["CPUExecutionProvider"])
        metadata = self.session.get_modelmeta().custom_metadata_map
        if CONTRACT_KEY not in metadata:
            raise ValueError("ONNX is missing its embedded ndp_tcn_contract; use the project exporter.")
        self.contract = json.loads(metadata[CONTRACT_KEY])
        c = self.contract
        self.contract_version = c.get("contract_version")
        if (type(self.contract_version) is not int or self.contract_version not in (1, 2, 3) or c.get("input_is_normalized") is not True
                or c.get("output_is_normalized") is not True):
            raise ValueError("Unsupported ONNX normalization contract.")
        self.schema = c["data_schema"]
        self.seq_len = self.schema["history_steps"]
        self.horizon = self.schema["horizon_steps_to_target_interval_start"]
        if (type(self.seq_len) is not int or self.seq_len < 2
                or type(self.horizon) is not int or self.horizon < 0):
            raise ValueError("Invalid ONNX history/horizon contract.")
        if (tuple(self.schema["feature_names"]) != FEATURE_NAMES
                or self.schema["label_definition"] != "interval_residual_v1"
                or self.schema["label_unit"] != "V/s"):
            raise ValueError("Unsupported ONNX feature order or target units.")
        self.dt = float(self.schema["sample_interval_s"])
        if not np.isfinite(self.dt) or self.dt <= 0:
            raise ValueError("Invalid sample interval.")
        b0 = float(self.schema["b0_per_phase"])
        if not np.isfinite(b0) or b0 <= 0:
            raise ValueError("Invalid b0 convention.")
        for key, size in (("x_mean", 9), ("x_scale", 9), ("y_mean", 1), ("y_scale", 1)):
            value = np.asarray(c["scalers"][key], dtype=np.float64)
            if (value.shape != (size,) or not np.isfinite(value).all()
                    or (key.endswith("scale") and np.any(value <= 0))):
                raise ValueError(f"Invalid embedded scaler: {key}")
            setattr(self, key, value)
        inputs, outputs = self.session.get_inputs(), self.session.get_outputs()
        input_shape, output_shape = [1, self.seq_len, 9], [1, 1]
        if self.contract_version in (2, 3):
            expected_backend = "ti_npu_fullconv" if self.contract_version == 3 else "ti_npu"
            if (c.get("model_backend") != expected_backend or c.get("input_layout") != "NCHW"
                    or c.get("raw_window_shape") != [self.seq_len, 9]
                    or c.get("padded_channels") != 12):
                raise ValueError("Invalid TI NPU external-packing contract.")
            input_shape = [1, 12, self.seq_len, 1]
        if self.contract_version == 3:
            if (c.get("effective_output_channel") != 0 or c.get("packed_output_channels") != 4
                    or c.get("output_layout") != "NCHW"):
                raise ValueError("Invalid full-convolution four-channel output contract.")
            output_shape = [1, 4, 1, 1]
        if (c.get("input_name") != "normalized_window"
                or c.get("output_name") != "normalized_residual"
                or c.get("input_shape") != input_shape or c.get("output_shape") != output_shape
                or c.get("input_dtype") != "float32" or c.get("output_dtype") != "float32"
                or len(inputs) != 1 or len(outputs) != 1
                or inputs[0].name != c["input_name"] or outputs[0].name != c["output_name"]
                or inputs[0].type != "tensor(float)" or outputs[0].type != "tensor(float)"
                or inputs[0].shape != input_shape or outputs[0].shape != output_shape):
            raise ValueError("ONNX graph input/output differs from its deployment contract.")

    def validate_schema(self, metadata):
        for key in ("feature_names", "history_steps", "horizon_steps_to_target_interval_start",
                    "label_definition"):
            value = list(metadata[key]) if key == "feature_names" else metadata[key]
            if value != self.schema[key]:
                raise ValueError(f"Input metadata differs from ONNX: {key}")
        for key, rtol, atol in (("sample_interval_s", 1e-5, 1e-12),
                               ("b0_per_phase", 1e-9, 1e-12)):
            if not np.isclose(metadata[key], self.schema[key], rtol=rtol, atol=atol):
                raise ValueError(f"Input metadata differs from ONNX: {key}")

    def predict_array(self, windows):
        windows = np.asarray(windows)
        if (windows.ndim != 3 or windows.shape[1:] != (self.seq_len, 9)
                or len(windows) == 0 or not np.isfinite(windows).all()):
            raise ValueError(f"Expected nonempty finite raw windows [N,{self.seq_len},9].")
        normalized = ((windows.astype(np.float64)-self.x_mean)/self.x_scale).astype(np.float32)
        if not np.isfinite(normalized).all():
            raise ValueError("Normalized input exceeds float32 range.")
        graph_inputs = pack_normalized_numpy(normalized) if self.contract_version in (2, 3) else normalized
        result = np.empty((len(windows), 1), dtype=np.float64)
        for index in range(len(windows)):
            pred = self.session.run([self.contract["output_name"]], {
                self.contract["input_name"]: np.ascontiguousarray(graph_inputs[index:index+1])})[0]
            if self.contract_version == 3:
                if pred.shape != (1, 4, 1, 1) or not np.isfinite(pred).all():
                    raise ValueError("ONNX returned an invalid four-channel core output.")
                pred = pred[:, 0, 0, 0].reshape(1, 1)
            if pred.shape != (1, 1) or not np.isfinite(pred).all():
                raise ValueError("ONNX returned an invalid residual prediction.")
            result[index] = pred[0].astype(np.float64)*self.y_scale+self.y_mean
        if not np.isfinite(result).all():
            raise ValueError("Decoded residual exceeds physical output range.")
        return result

    def predict(self, window, source_time_s=None):
        window = np.asarray(window)
        if window.shape != (self.seq_len, 9):
            raise ValueError(f"Expected a raw [{self.seq_len},9] window.")
        if source_time_s is not None and not np.isfinite(source_time_s):
            raise ValueError("Invalid source timestamp.")
        residual = float(self.predict_array(window[None])[0, 0])
        z2 = float(window[-1, 7])
        return {"residual_V_per_s": residual, "future_disturbance_V_per_s": z2+residual,
                "source_z2_V_per_s": z2, "source_time_s": source_time_s,
                "target_start_time_s": None if source_time_s is None else source_time_s+self.horizon*self.dt,
                "target_end_time_s": None if source_time_s is None else source_time_s+(self.horizon+1)*self.dt}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--input-npz", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--threads", type=int, default=2)
    args = parser.parse_args()
    if args.output is not None and (args.output.exists() or args.output.suffix.lower() != ".npz"):
        raise ValueError("Use a new .npz output path.")
    predictor = OnnxResidualPredictor(args.model, threads=args.threads)
    with np.load(args.input_npz, allow_pickle=False) as data:
        predictor.validate_schema(json.loads(str(data["metadata_json"].item())))
        windows, times = data["X"], data["source_time_s"]
        if times.shape != (len(windows),) or not np.isfinite(times).all():
            raise ValueError("Invalid source timestamps.")
        # 仅使用历史输入、时间与元数据；不读取 y 或目标扰动。
        residual = predictor.predict_array(windows)
    with open_result_file(args.output, prefix=f"predict_onnx_{args.input_npz.stem}",
                          suffix=".npz", binary=True) as (path, stream):
        np.savez_compressed(stream, residual_V_per_s=residual,
                            future_disturbance_V_per_s=residual[:, 0]+windows[:, -1, 7],
                            source_z2_V_per_s=windows[:, -1, 7], source_time_s=times,
                            target_start_time_s=times+predictor.horizon*predictor.dt,
                            target_end_time_s=times+(predictor.horizon+1)*predictor.dt,
                            onnx_model=np.asarray(str(predictor.model_path)),
                            onnx_sha256=np.asarray(hashlib.sha256(predictor.model_path.read_bytes()).hexdigest()),
                            checkpoint=np.asarray(predictor.contract["checkpoint"]))
    print(f"Saved {len(residual)} ONNX predictions: {path}")
    return path


if __name__ == "__main__":
    main()
