"""核查完整工况划分、训练集标准化及 NPZ 标签接口。"""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import torch

from ndp_tcn.data import (
    FEATURE_NAMES, CaseData, Scalers, NPZWindows, load_case, load_splits,
)


def make_case(path, case_id, n=3, offset=0.0, metadata_overrides=None):
    L, h, dt = 4, 1, 1/30000
    raw = np.arange((n+L-1)*9, dtype=np.float32).reshape(-1, 9)+offset
    raw[:, 5], raw[:, 8] = 12, 48
    k = np.arange(L-1, n+L-1, dtype=np.int64)
    X = raw[k[:, None]+np.arange(-L+1, 1)]
    y = (np.arange(n, dtype=np.float32)+1)[:, None]*10
    source_z2 = X[:, -1, 7].astype(np.float64)
    meta = {
        "feature_names": list(FEATURE_NAMES), "label_definition": "interval_residual_v1",
        "history_steps": L, "horizon_steps_to_target_interval_start": h,
        "sample_interval_s": dt, "b0_per_phase": 20000,
        "case_id": case_id, "source_sha256": f"{case_id:064x}",
        "X_shape": list(X.shape), "y_shape": list(y.shape),
    }
    meta.update(metadata_overrides or {})
    np.savez_compressed(path, X=X, y=y, source_z2_V_per_s=source_z2,
                        source_index=k, target_interval_index=k+h,
                        source_time_s=k*dt, target_start_time_s=(k+h)*dt,
                        target_end_time_s=(k+h+1)*dt,
                        target_disturbance_V_per_s=source_z2+y[:, 0],
                        feature_names=np.asarray(FEATURE_NAMES),
                        metadata_json=np.asarray(json.dumps(meta)))
    path.with_suffix(".json").write_text(json.dumps(meta), encoding="utf-8")
    return meta


class DataTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.manifest = {"train": ["train.npz"], "val": ["val.npz"], "test": ["test.npz"]}
        make_case(self.root/"train.npz", 1)
        make_case(self.root/"val.npz", 2, offset=1000)
        make_case(self.root/"test.npz", 3, offset=2000)

    def tearDown(self):
        self.temp.cleanup()

    def test_default_does_not_load_test_arrays_and_dict_manifest_works(self):
        original = load_case
        called = []

        def record_load(path):
            called.append(Path(path).name)
            if Path(path).name == "test.npz":
                self.fail("Training requested test arrays.")
            return original(path)

        with patch("ndp_tcn.data.load_case", side_effect=record_load):
            grouped = load_splits(self.root, self.manifest)
        self.assertEqual(called, ["train.npz", "val.npz"])
        self.assertEqual(grouped["test"], [])
        manifest_path = self.root/"split.json"
        manifest_path.write_text(json.dumps(self.manifest), encoding="utf-8")
        all_groups = load_splits(self.root, manifest_path, include_test=True)
        self.assertEqual(all_groups["test"][0].case_id, 3)

    def test_reject_duplicate_file_source_and_case_ids(self):
        duplicated_file = copy.deepcopy(self.manifest)
        duplicated_file["val"] = ["train.npz"]
        with self.assertRaisesRegex(ValueError, "Duplicate file"):
            load_splits(self.root, duplicated_file)
        make_case(self.root/"test.npz", 3, metadata_overrides={"source_sha256": f"{1:064x}"})
        with self.assertRaisesRegex(ValueError, "Duplicate source/case"):
            load_splits(self.root, self.manifest)
        make_case(self.root/"test.npz", 1, metadata_overrides={"source_sha256": f"{99:064x}"})
        with self.assertRaisesRegex(ValueError, "Duplicate source/case"):
            load_splits(self.root, self.manifest)

    def test_explicit_empty_validation_keeps_test_held_out(self):
        manifest = {"train": ["train.npz", "val.npz"], "val": [], "test": ["test.npz"]}
        with patch("ndp_tcn.data.load_case", wraps=load_case) as loader:
            groups = load_splits(self.root, manifest)
        self.assertEqual([case.case_id for case in groups["train"]], [1, 2])
        self.assertEqual(groups["val"], [])
        self.assertEqual(groups["test"], [])
        self.assertEqual([Path(call.args[0]).name for call in loader.call_args_list],
                         ["train.npz", "val.npz"])
        self.assertEqual(Scalers.fit(groups["train"]).fit_case_ids, (1, 2))
        evaluated = load_splits(self.root, manifest, include_test=True)
        self.assertEqual([case.case_id for case in evaluated["test"]], [3])
        manifest["test"] = ["train.npz"]
        with self.assertRaisesRegex(ValueError, "Duplicate file"):
            load_splits(self.root, manifest)

    def test_train_and_test_must_stay_nonempty_and_val_explicit(self):
        for split in ("train", "test"):
            manifest = dict(self.manifest, val=[])
            manifest[split] = []
            with self.subTest(split=split), self.assertRaisesRegex(ValueError, "nonempty"):
                load_splits(self.root, manifest)
        for value in (None, "", "val.npz"):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "val must be a list"):
                load_splits(self.root, dict(self.manifest, val=value))
        with self.assertRaisesRegex(ValueError, "val must be a list"):
            load_splits(self.root, {"train": ["train.npz"], "test": ["test.npz"]})
    def test_metadata_mismatch_rejected_even_for_unloaded_test(self):
        make_case(self.root/"test.npz", 3, metadata_overrides={"sample_interval_s": 1/10000})
        with self.assertRaisesRegex(ValueError, "same history, horizon"):
            load_splits(self.root, self.manifest)
        with self.assertRaisesRegex(ValueError, "Inconsistent sample interval"):
            load_case(self.root/"test.npz")

    def test_stale_sidecar_and_wrong_target_units_rejected(self):
        sidecar = self.root/"val.json"
        metadata = json.loads(sidecar.read_text())
        metadata["case_id"] = 9
        sidecar.write_text(json.dumps(metadata), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "metadata mismatch"):
            load_splits(self.root, self.manifest)
        make_case(self.root/"val.npz", 2, metadata_overrides={"target_units": "A"})
        with self.assertRaisesRegex(ValueError, "V/s"):
            load_case(self.root/"val.npz")

    def test_paired_nominal_and_variation_cannot_cross_splits(self):
        pair = {"batch_id": "batch", "split_group": "N001", "paired_nominal_id": 1}
        make_case(self.root/"train.npz", 1, metadata_overrides=pair)
        make_case(self.root/"test.npz", 3, metadata_overrides=pair)
        with patch("ndp_tcn.data.load_case") as loader:
            with self.assertRaisesRegex(ValueError, "Paired group crosses splits"):
                load_splits(self.root, self.manifest)
            loader.assert_not_called()
        together = {"train": ["train.npz", "test.npz"], "val": [], "test": ["val.npz"]}
        groups = load_splits(self.root, together, include_test=True)
        self.assertEqual([case.case_id for case in groups["train"]], [1, 3])

    def test_pair_alias_and_stale_group_sidecar_are_rejected(self):
        pair = {"batch_id": "batch", "split_group": "N001", "paired_nominal_id": 1}
        make_case(self.root/"train.npz", 1, metadata_overrides=pair)
        make_case(self.root/"test.npz", 3, metadata_overrides=dict(pair, split_group="renamed"))
        with self.assertRaisesRegex(ValueError, "inconsistent split_group"):
            load_splits(self.root, self.manifest)
        make_case(self.root/"test.npz", 3, metadata_overrides=dict(pair, split_group="N003", paired_nominal_id=3))
        sidecar = self.root/"test.json"
        saved = json.loads(sidecar.read_text(encoding="utf-8"))
        saved["paired_nominal_id"] = 4
        sidecar.write_text(json.dumps(saved), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "metadata mismatch.*paired_nominal_id"):
            load_splits(self.root, self.manifest)

    def test_incomplete_pair_and_local_batch_id_are_rejected(self):
        make_case(self.root/"test.npz", 3, metadata_overrides={"split_group": "N001"})
        with self.assertRaisesRegex(ValueError, "Paired metadata"):
            load_splits(self.root, self.manifest)
        make_case(self.root/"test.npz", 3, metadata_overrides={"batch_case_id": 301})
        with self.assertRaisesRegex(ValueError, "case_id must equal"):
            load_splits(self.root, self.manifest)

    def test_training_only_scalers_constant_channels_and_roundtrip(self):
        groups = load_splits(self.root, self.manifest)
        scaler = Scalers.fit(groups["train"])
        train = groups["train"][0]
        np.testing.assert_allclose(scaler.x_mean, train.X.mean(axis=(0, 1)))
        self.assertEqual(scaler.fit_case_ids, (1,))
        self.assertEqual(scaler.x_scale[5], 1)
        self.assertEqual(scaler.x_scale[8], 1)
        norm = scaler.transform_x(train.X)
        np.testing.assert_array_equal(norm[:, :, [5, 8]], 0)
        self.assertGreater(float(scaler.transform_x(groups["val"][0].X)[:, :, 0].mean()), 10)
        saved = Scalers.from_dict(json.loads(json.dumps(scaler.to_dict())))
        np.testing.assert_allclose(saved.inverse_y(saved.transform_y(train.y)), train.y, atol=1e-6)
        np.testing.assert_array_equal(saved.transform_x(train.X), norm)

    def test_dataset_boundaries_case_weights_and_targets_remain_separate(self):
        make_case(self.root/"val.npz", 2, n=5, offset=1000)
        cases = [load_case(self.root/"train.npz"), load_case(self.root/"val.npz")]
        scalers = Scalers.fit(cases[:1])
        dataset = NPZWindows(cases, scalers)
        self.assertEqual(len(dataset), 8)
        x2, y2, case2 = dataset[2]
        x3, y3, case3 = dataset[3]
        self.assertEqual((case2, case3), (0, 1))
        self.assertEqual(tuple(x3.shape), (4, 9))
        self.assertEqual(tuple(y3.shape), (1,))
        self.assertEqual(x3.dtype, torch.float32)
        np.testing.assert_allclose(dataset.sample_weights[:3].sum(), 1)
        np.testing.assert_allclose(dataset.sample_weights[3:].sum(), 1)
        np.testing.assert_array_equal(x3.numpy(), scalers.transform_x(cases[1].X[0]))
        changed = copy.copy(cases[0])
        changed.y = cases[0].y+1000
        other = NPZWindows([changed], scalers)
        np.testing.assert_array_equal(other[0][0].numpy(), dataset[0][0].numpy())
        self.assertNotEqual(float(other[0][1].item()), float(dataset[0][1].item()))
        with self.assertRaises(IndexError):
            dataset[len(dataset)]


if __name__ == "__main__":
    unittest.main()
