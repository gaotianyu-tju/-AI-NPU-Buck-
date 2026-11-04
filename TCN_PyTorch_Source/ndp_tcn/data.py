"""按完整工况读取残差样本；输入和标签分离，标准化仅拟合训练工况。"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Mapping, Sequence

import numpy as np
import torch
from torch.utils.data import Dataset


FEATURE_NAMES = ("Vo", "ILA", "ILB", "ILC", "ILD", "VREF", "IREF", "z2", "Vin")
LABEL_DEFINITION = "interval_residual_v1"


def _positive_integer(value, name, allow_zero=False):
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise ValueError(f"{name} must be an integer.")
    if value < (0 if allow_zero else 1):
        raise ValueError(f"Invalid {name}: {value}.")
    return int(value)


def _check_metadata(metadata):
    if tuple(metadata.get("feature_names", ())) != FEATURE_NAMES:
        raise ValueError("The nine feature names/order do not match the residual task.")
    if metadata.get("label_definition") != LABEL_DEFINITION:
        raise ValueError("Unsupported/missing label_definition; regenerate labels with the current script.")
    _positive_integer(metadata.get("history_steps"), "history_steps")
    _positive_integer(metadata.get("horizon_steps_to_target_interval_start"), "horizon", True)
    _positive_integer(metadata.get("case_id"), "case_id")
    dt = float(metadata.get("sample_interval_s", float("nan")))
    b0 = float(metadata.get("b0_per_phase", float("nan")))
    if not np.isfinite(dt) or dt <= 0 or not np.isfinite(b0) or b0 == 0:
        raise ValueError("Invalid sample_interval_s or b0_per_phase.")
    if not re.fullmatch(r"[0-9a-fA-F]{64}", str(metadata.get("source_sha256", ""))):
        raise ValueError("A valid source_sha256 is required to identify duplicate source runs.")
    for field in ("target_units", "label_units"):
        if field in metadata and metadata[field] != "V/s":
            raise ValueError("Residual labels must use V/s units.")
    paired_group_key(metadata)
    load_family_key(metadata)
    if "batch_case_id" in metadata:
        if _positive_integer(metadata["batch_case_id"], "batch_case_id") != metadata["case_id"]:
            raise ValueError("case_id must equal the unique batch_case_id for batch datasets.")


def paired_group_key(metadata):
    """旧数据没有配对字段时保持原行为；有配对信息时必须完整。"""
    if "split_group" not in metadata and "paired_nominal_id" not in metadata:
        return None
    batch, group = metadata.get("batch_id"), metadata.get("split_group")
    if (not isinstance(batch, str) or not batch.strip()
            or not isinstance(group, str) or not group.strip()):
        raise ValueError("Paired metadata requires nonempty batch_id and split_group.")
    # 0明确表示未配对；这些工况仍受各自split_group的完整工况隔离约束。
    _positive_integer(metadata.get("paired_nominal_id"), "paired_nominal_id", allow_zero=True)
    return batch, group


def load_family_key(metadata):
    """跨批次负载族隔离；旧标签没有这两个字段时保持原有行为。"""
    fields = ("load_family_scope", "load_family_key")
    if not any(field in metadata for field in fields):
        return None
    scope, key = (metadata.get(field) for field in fields)
    if (not isinstance(scope, str) or not scope.strip()
            or not isinstance(key, str) or not key.strip()):
        raise ValueError("Load family metadata requires nonempty load_family_scope and load_family_key.")
    return scope, key


def read_case_metadata(path):
    """只读取 NPZ 的元数据项，不解压 X/y；可用于检查尚未打开的测试工况。"""
    path = Path(path)
    with np.load(path, allow_pickle=False) as archive:
        metadata = json.loads(str(archive["metadata_json"].item()))
    _check_metadata(metadata)
    sidecar = path.with_suffix(".json")
    if sidecar.exists():
        saved = json.loads(sidecar.read_text(encoding="utf-8-sig"))
        # JSON 和 NPZ 必须属于同一次生成，避免旧的旁文件掩盖真实工况身份。
        for name in ("case_id", "source_sha256", "feature_names", "history_steps",
                     "horizon_steps_to_target_interval_start", "sample_interval_s",
                     "b0_per_phase", "label_definition", "X_shape", "y_shape",
                     "batch_id", "batch_case_id", "source_case_id", "case_group",
                     "paired_nominal_id", "split_group", "source_identity",
                     "source_batch_case_id", "source_batch_id", "collection_id",
                     "load_family_scope", "load_family_key", "case_parameters"):
            if saved.get(name) != metadata.get(name):
                raise ValueError(f"NPZ/JSON metadata mismatch for {path.name}: {name}.")
    return metadata


@dataclass
class CaseData:
    path: Path
    X: np.ndarray
    y: np.ndarray
    source_z2: np.ndarray
    source_time: np.ndarray
    target_start: np.ndarray
    target_end: np.ndarray
    metadata: dict

    @property
    def case_id(self):
        return int(self.metadata["case_id"])

    @property
    def seq_len(self):
        return int(self.X.shape[1])

    @property
    def horizon(self):
        return int(self.metadata["horizon_steps_to_target_interval_start"])

    @property
    def sample_interval(self):
        return float(self.metadata["sample_interval_s"])


def load_case(path):
    path = Path(path).resolve()
    metadata = read_case_metadata(path)
    with np.load(path, allow_pickle=False) as archive:
        if tuple(archive["feature_names"].tolist()) != FEATURE_NAMES:
            raise ValueError(f"Wrong feature order in {path.name}.")
        X = np.asarray(archive["X"], dtype=np.float32)
        y = np.asarray(archive["y"], dtype=np.float32)
        arrays = {name: np.asarray(archive[key], dtype=np.float64) for name, key in (
            ("source_z2", "source_z2_V_per_s"), ("source_time", "source_time_s"),
            ("target_start", "target_start_time_s"), ("target_end", "target_end_time_s"),
            ("target_disturbance", "target_disturbance_V_per_s"))}
        source_index = np.asarray(archive["source_index"])
        target_index = np.asarray(archive["target_interval_index"])
    L = int(metadata["history_steps"])
    if X.ndim != 3 or X.shape[1:] != (L, 9) or X.shape[0] == 0:
        raise ValueError(f"Expected nonempty X[N,{L},9] in {path.name}.")
    n = len(X)
    if y.shape != (n, 1) or any(value.shape != (n,) for value in arrays.values()):
        raise ValueError(f"Target/timestamp shapes do not match X in {path.name}.")
    if not all(np.isfinite(value).all() for value in (X, y, *arrays.values())):
        raise ValueError(f"Nonfinite feature, target or timing value in {path.name}.")
    if metadata.get("X_shape") != list(X.shape) or metadata.get("y_shape") != list(y.shape):
        raise ValueError(f"Metadata shapes disagree with arrays in {path.name}.")
    for name, indices in (("source", source_index), ("target", target_index)):
        if indices.shape != (n,) or indices.dtype.kind not in "iu":
            raise ValueError(f"Invalid {name} indices in {path.name}.")
    h, dt = int(metadata["horizon_steps_to_target_interval_start"]), float(metadata["sample_interval_s"])
    if np.any(source_index < L-1) or np.any(np.diff(source_index) <= 0):
        raise ValueError(f"Source window indices are invalid in {path.name}.")
    if not np.array_equal(target_index, source_index + h):
        raise ValueError(f"Source/target horizon mismatch in {path.name}.")
    tolerance = max(1e-11, dt*1e-6)
    comparisons = (
        (arrays["target_start"]-arrays["source_time"], np.full(n, h*dt)),
        (arrays["target_end"]-arrays["target_start"], np.full(n, dt)),
        (np.diff(arrays["source_time"]), np.diff(source_index)*dt),
    )
    if any(not np.allclose(a, b, rtol=1e-6, atol=tolerance) for a, b in comparisons):
        raise ValueError(f"Inconsistent sample interval or target timing in {path.name}.")
    if not np.allclose(arrays["source_z2"], X[:, -1, 7], rtol=1e-7, atol=1e-4):
        raise ValueError(f"Source z2 does not match the window endpoint in {path.name}.")
    if not np.allclose(y[:, 0], arrays["target_disturbance"]-arrays["source_z2"], rtol=1e-6, atol=1e-3):
        raise ValueError(f"Stored labels do not match the declared residual in {path.name}.")
    return CaseData(path, X, y, arrays["source_z2"], arrays["source_time"],
                    arrays["target_start"], arrays["target_end"], metadata)


def load_splits(data_dir, manifest_path, include_test=False):
    """按完整文件分组；允许 val=[]，仅 include_test=True 时读取测试 X/y。"""
    root = Path(data_dir).resolve()
    if isinstance(manifest_path, Mapping):
        manifest = dict(manifest_path)
    else:
        manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8-sig"))
    grouped = {}
    seen_paths, seen_hashes, seen_ids = set(), set(), set()
    group_splits, paired_groups, group_pairs = {}, {}, {}
    family_splits = {}
    reference = None
    for split in ("train", "val", "test"):
        names = manifest.get(split)
        if not isinstance(names, list) or not all(isinstance(name, str) for name in names):
            raise ValueError(f"Manifest {split} must be a list of NPZ filenames; use val=[] for no validation.")
        if not names and split != "val":
            raise ValueError(f"Manifest {split} must be a nonempty list of NPZ filenames.")
        grouped[split] = []
        for name in names:
            path = (root/name).resolve()
            if not path.is_relative_to(root) or path.suffix.lower() != ".npz":
                raise ValueError(f"Manifest filename must stay inside data_dir: {name}.")
            canonical = str(path).casefold()
            if canonical in seen_paths:
                raise ValueError(f"Duplicate file across/in splits: {name}.")
            seen_paths.add(canonical)
            metadata = read_case_metadata(path)
            identity = str(metadata["source_sha256"]).lower()
            case_id = int(metadata["case_id"])
            if identity in seen_hashes or case_id in seen_ids:
                raise ValueError(f"Duplicate source/case identity across/in splits: {name}.")
            seen_hashes.add(identity)
            seen_ids.add(case_id)
            group_key = paired_group_key(metadata)
            if group_key is not None:
                if metadata["paired_nominal_id"] > 0:
                    pair_key = (metadata["batch_id"], metadata["paired_nominal_id"])
                    if pair_key in paired_groups and paired_groups[pair_key] != group_key:
                        raise ValueError(f"The same paired_nominal_id has inconsistent split_group: {name}.")
                    if group_key in group_pairs and group_pairs[group_key] != pair_key:
                        raise ValueError(f"A split_group contains inconsistent paired_nominal_id: {name}.")
                    paired_groups[pair_key], group_pairs[group_key] = group_key, pair_key
                if group_key in group_splits and group_splits[group_key] != split:
                    raise ValueError(f"Paired group crosses splits: {group_key} in {name}.")
                group_splits[group_key] = split
            family_key = load_family_key(metadata)
            if family_key is not None:
                if family_key in family_splits and family_splits[family_key] != split:
                    raise ValueError(f"Load family crosses splits: {family_key} in {name}.")
                family_splits[family_key] = split
            signature = (metadata["history_steps"], metadata["horizon_steps_to_target_interval_start"],
                         metadata["sample_interval_s"], metadata["b0_per_phase"], metadata["label_definition"])
            if reference is None:
                reference = signature
            elif (signature[:2] != reference[:2] or signature[4] != reference[4]
                  or not np.isclose(signature[2], reference[2], rtol=1e-6, atol=1e-12)
                  or not np.isclose(signature[3], reference[3], rtol=1e-9, atol=1e-12)):
                raise ValueError("All splits must use the same history, horizon, sample interval, b0 and label definition.")
            grouped[split].append(path)
    return {split: ([load_case(path) for path in paths] if split != "test" or include_test else [])
            for split, paths in grouped.items()}


@dataclass
class Scalers:
    x_mean: np.ndarray
    x_scale: np.ndarray
    y_mean: np.ndarray
    y_scale: np.ndarray
    fit_case_ids: tuple = ()

    def __post_init__(self):
        for name, size in (("x_mean", 9), ("x_scale", 9), ("y_mean", 1), ("y_scale", 1)):
            value = np.asarray(getattr(self, name), dtype=np.float64)
            if value.shape != (size,) or not np.isfinite(value).all():
                raise ValueError(f"Invalid scaler {name}.")
            if name.endswith("scale") and np.any(value <= 0):
                raise ValueError("Normalization scales must be positive.")
            setattr(self, name, value)
        self.fit_case_ids = tuple(int(value) for value in self.fit_case_ids)

    @classmethod
    def fit(cls, cases: Sequence[CaseData]):
        """按训练窗口中的观测次数估计均值/方差；常量通道尺度设为 1。"""
        if not cases:
            raise ValueError("Cannot fit normalization without training cases.")

        def moments(getter, width):
            count, mean, m2 = 0, np.zeros(width), np.zeros(width)
            for case in cases:
                values = np.asarray(getter(case), dtype=np.float64).reshape(-1, width)
                if not len(values) or not np.isfinite(values).all():
                    raise ValueError("Cannot fit scalers to empty/nonfinite training arrays.")
                batch_count = len(values)
                batch_mean, batch_var = values.mean(axis=0), values.var(axis=0)
                delta = batch_mean-mean
                total = count+batch_count
                m2 += batch_var*batch_count + delta**2*count*batch_count/total
                mean += delta*batch_count/total
                count = total
            std = np.sqrt(np.maximum(m2/count, 0))
            return mean, np.where(std > 1e-12, std, 1.0)

        xm, xs = moments(lambda case: case.X, 9)
        ym, ys = moments(lambda case: case.y, 1)
        return cls(xm, xs, ym, ys, tuple(case.case_id for case in cases))

    def transform_x(self, values):
        values = np.asarray(values)
        if values.ndim < 2 or values.shape[-1] != 9 or not np.isfinite(values).all():
            raise ValueError("Expected finite input with nine channels.")
        return ((values-self.x_mean)/self.x_scale).astype(np.float32)

    def transform_y(self, values):
        return ((np.asarray(values)-self.y_mean)/self.y_scale).astype(np.float32)

    def inverse_y(self, values):
        return np.asarray(values)*self.y_scale+self.y_mean

    def to_dict(self):
        return {"x_mean": self.x_mean.tolist(), "x_scale": self.x_scale.tolist(),
                "y_mean": self.y_mean.tolist(), "y_scale": self.y_scale.tolist(),
                "fit_case_ids": list(self.fit_case_ids)}

    @classmethod
    def from_dict(cls, values):
        return cls(values["x_mean"], values["x_scale"], values["y_mean"], values["y_scale"],
                   tuple(values.get("fit_case_ids", ())))


class NPZWindows(Dataset):
    """工况边界不拼接；case_index 是 cases 列表中的下标。"""

    def __init__(self, cases: Sequence[CaseData], scalers: Scalers):
        if not cases or any(len(case.X) == 0 for case in cases):
            raise ValueError("NPZWindows needs nonempty cases.")
        if len({case.X.shape[1:] for case in cases}) != 1:
            raise ValueError("All cases in a dataset must have the same input shape.")
        self.cases = list(cases)
        self.scalers = scalers
        self._x = [torch.from_numpy(scalers.transform_x(case.X)) for case in cases]
        self._y = [torch.from_numpy(scalers.transform_y(case.y)) for case in cases]
        lengths = np.asarray([len(case.X) for case in cases], dtype=np.int64)
        self._ends = np.cumsum(lengths)
        self._starts = np.r_[0, self._ends[:-1]]
        self.sample_weights = np.concatenate([np.full(n, 1.0/n, dtype=np.float64) for n in lengths])

    def __len__(self):
        return int(self._ends[-1])

    def __getitem__(self, index):
        index = int(index)
        if index < 0:
            index += len(self)
        if index < 0 or index >= len(self):
            raise IndexError(index)
        case_index = int(np.searchsorted(self._ends, index, side="right"))
        local = index-int(self._starts[case_index])
        return self._x[case_index][local], self._y[case_index][local], case_index
