"""标签时间索引、批次隔离及已有文件保护的针对性验证。"""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
from scipy.io import savemat

from prepare_residual_labels import (
    FEATURE_NAMES, build_samples, check_output_path, process_directory,
)


def known_sequence(b0=20000.0, n=30):
    dt = 1.0 / 30000
    time = np.arange(n) * dt
    x = np.zeros((n, 9), dtype=float)
    x[:, 6] = 4 + np.arange(n) % 3
    f = -80000 + 300 * np.arange(n-1)
    x[0, 0] = 12
    x[1:, 0] = 12 + np.cumsum(dt * (b0*x[:-1, 6] + f))
    x[:, 5] = 12
    x[:, 7] = -81000 + 10*np.arange(n)
    x[:, 8] = 48
    return x, time, f


def write_case(path, case_id, b0=20000.0, extra_meta=None):
    x, time, f = known_sequence(b0)
    savemat(path, {
        "data": {"features": x, "time": time,
                 "feature_names": np.asarray(FEATURE_NAMES, dtype=object),
                 "valid": np.ones(len(time), dtype=np.uint8)},
        "meta": {"case_id": case_id, "b0": b0, "wc": 5000, "wo": 14000,
                 "sample_frequency_Hz": 30000, "pulse_start_s": 0.0,
                 "IREF_definition": "common per-phase current reference",
                 **(extra_meta or {})},
    })
    return x, time, f


class ResidualLabelTests(unittest.TestCase):
    def test_known_disturbance_horizons_and_bounds(self):
        x, time, f = known_sequence()
        for horizon in (0, 1, 3):
            with self.subTest(horizon=horizon):
                result = build_samples(x, time, 20000, 8, horizon)
                k = result["source_index"]
                expected = f[k+horizon] - x[k, 7]
                np.testing.assert_allclose(result["y"][:, 0], expected, atol=.002)
                np.testing.assert_array_equal(result["X"][0], x[:8].astype(np.float32))
                self.assertEqual(result["X"].shape, (len(time)-8-horizon, 8, 9))
                self.assertEqual(result["target_end_time_s"][-1], time[-1])

    def test_future_label_value_does_not_enter_current_input(self):
        x, time, _ = known_sequence()
        first = build_samples(x, time, 20000)
        altered = x.copy()
        altered[9, 0] += .1
        second = build_samples(altered, time, 20000)
        np.testing.assert_array_equal(first["X"][0], second["X"][0])
        np.testing.assert_allclose(second["y"][0]-first["y"][0], 3000, atol=.002)

    def test_batch_keeps_cases_and_parameters_separate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inputs, outputs = root/"inputs", root/"outputs"
            inputs.mkdir()
            expected = {}
            for case_id, b0 in [(1, 20000), (2, 17000)]:
                expected[case_id] = write_case(inputs/f"pulse_case{case_id}.mat", case_id, b0)
            # 参数 MAT 和子目录都不应被默认批处理选中。
            savemat(inputs/"canshu.mat", {"parameter": 123})
            (inputs/"support").mkdir()
            savemat(inputs/"support"/"pulse_hidden.mat", {"parameter": 123})
            original_bytes = {p: p.read_bytes() for p in inputs.rglob("*.mat")}
            with contextlib.redirect_stdout(io.StringIO()):
                summary = process_directory(inputs, outputs, history=8, horizon=1)
            self.assertEqual(summary["file_count"], 2)
            self.assertEqual(summary["total_samples"], 42)
            for record in summary["files"]:
                x, _, f = expected[record["case_id"]]
                with np.load(record["npz_file"], allow_pickle=False) as result:
                    k = result["source_index"]
                    np.testing.assert_allclose(result["y"][:, 0], f[k+1]-x[k, 7], atol=.002)
                    np.testing.assert_array_equal(result["X"][0], x[:8].astype(np.float32))
                stats = json.loads(Path(record["metadata_file"]).read_text(encoding="utf-8"))
                self.assertEqual(stats["case_id"], record["case_id"])
            for path, original in original_bytes.items():
                self.assertEqual(path.read_bytes(), original)

    def test_batch_collision_stops_before_any_new_dataset(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inputs, outputs = root/"inputs", root/"outputs"
            inputs.mkdir()
            outputs.mkdir()
            write_case(inputs/"pulse_a.mat", 1)
            write_case(inputs/"pulse_b.mat", 2)
            sentinel = outputs/"pulse_b_L8_h1_residual.npz"
            sentinel.write_bytes(b"existing result")
            with self.assertRaises(FileExistsError):
                process_directory(inputs, outputs)
            self.assertEqual(sentinel.read_bytes(), b"existing result")
            self.assertEqual([p.name for p in outputs.iterdir()], [sentinel.name])

    def test_bad_case_stops_before_writing_good_case(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inputs, outputs = root/"inputs", root/"outputs"
            inputs.mkdir()
            write_case(inputs/"pulse_a.mat", 1)
            savemat(inputs/"pulse_bad.mat", {"parameter": 123})
            with self.assertRaisesRegex(ValueError, "pulse_bad.mat"):
                process_directory(inputs, outputs)
            self.assertFalse(outputs.exists())

    def test_missing_npz_suffix_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, r"\.npz"):
                check_output_path(Path(directory)/"no_extension")

    def test_nv_batch_preserves_pairs_and_uses_global_ids_with_dc_null(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inputs, outputs = root/"inputs", root/"outputs"
            inputs.mkdir()
            common = {"batch_id": "batch500", "paired_nominal_id": 1,
                      "split_group": "N001", "frequency_Hz": 0,
                      "high_duty_fraction": float("nan"),
                      "L_factors": np.ones(4), "phase_L_uH": np.full(4, 290)}
            for name, batch_id, group, factor in (("N001.mat", 1, "nominal", 1.0),
                                                  ("V001.mat", 301, "variation", .9)):
                write_case(inputs/name, 1, extra_meta=dict(common, batch_case_id=batch_id,
                           case_group=group, output_C_factor=factor))
            write_case(inputs/"pulse_old.mat", 1)
            (inputs/"support").mkdir()
            write_case(inputs/"support"/"N_hidden.mat", 2)
            original = {p: p.read_bytes() for p in inputs.rglob("*.mat")}
            with contextlib.redirect_stdout(io.StringIO()):
                summary = process_directory(inputs, outputs, pattern="[NV]*.mat")
            self.assertEqual(summary["file_count"], 2)
            self.assertEqual(summary["top_level_mat_count"], 3)
            self.assertEqual([r["case_id"] for r in summary["files"]], [1, 301])
            self.assertEqual([r["source_case_id"] for r in summary["files"]], [1, 1])
            for record in summary["files"]:
                self.assertEqual(record["split_group"], "N001")
                text = Path(record["metadata_file"]).read_text(encoding="utf-8")
                self.assertNotIn("NaN", text)
                stats = json.loads(text)
                self.assertIsNone(stats["case_parameters"]["high_duty_fraction"])
                self.assertEqual(stats["case_parameters"]["L_factors"], [1, 1, 1, 1])
                with np.load(record["npz_file"], allow_pickle=False) as archive:
                    self.assertEqual(json.loads(str(archive["metadata_json"].item())), stats)
                    self.assertTrue(np.isfinite(archive["X"]).all())
                    self.assertTrue(np.isfinite(archive["y"]).all())
            for path, raw in original.items():
                self.assertEqual(path.read_bytes(), raw)

    def test_duplicate_case_id_stops_before_writing_any_dataset(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inputs, outputs = root/"inputs", root/"outputs"
            inputs.mkdir()
            write_case(inputs/"pulse_a.mat", 1)
            write_case(inputs/"pulse_b.mat", 1, b0=19000)
            with contextlib.redirect_stdout(io.StringIO()), self.assertRaisesRegex(ValueError, "Duplicate source/case"):
                process_directory(inputs, outputs)
            self.assertFalse(outputs.exists())

    def test_incomplete_batch_metadata_is_not_silently_discarded(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inputs, outputs = root/"inputs", root/"outputs"
            inputs.mkdir()
            write_case(inputs/"V001.mat", 1, extra_meta={"batch_case_id": 301})
            with contextlib.redirect_stdout(io.StringIO()), self.assertRaisesRegex(ValueError, "Incomplete batch/group"):
                process_directory(inputs, outputs, pattern="[NV]*.mat")
            self.assertFalse(outputs.exists())


if __name__ == "__main__":
    unittest.main()
