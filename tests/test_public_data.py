from __future__ import annotations

import csv
import math
import unittest
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "sanitized"
CONFIGURATIONS = ("c90_full_cylinder_equivalent", "full360")


def load(path: Path, value_name: str) -> dict[str, list[tuple[float, float]]]:
    grouped: dict[str, list[tuple[float, float]]] = defaultdict(list)
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        expected = ["time_s", "configuration", value_name]
        if reader.fieldnames != expected:
            raise AssertionError(f"{path.name}: expected {expected}")
        for row in reader:
            configuration = row["configuration"]
            if configuration not in CONFIGURATIONS:
                raise AssertionError(f"unknown configuration: {configuration}")
            time_s = float(row["time_s"])
            value = float(row[value_name])
            if not math.isfinite(time_s) or not math.isfinite(value):
                raise AssertionError("nonfinite public data")
            grouped[configuration].append((time_s, value))
    return grouped


class PublicDataTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.retention = load(
            DATA / "particle_retention_timeseries.csv", "retained_percent"
        )
        cls.counts = load(DATA / "particle_count_timeseries.csv", "particle_count")

    def test_complete_configurations(self) -> None:
        self.assertEqual(tuple(self.retention), CONFIGURATIONS)
        self.assertEqual(tuple(self.counts), CONFIGURATIONS)

    def test_time_keys_match_and_increase(self) -> None:
        for configuration in CONFIGURATIONS:
            retention_times = [row[0] for row in self.retention[configuration]]
            count_times = [row[0] for row in self.counts[configuration]]
            self.assertEqual(retention_times, count_times)
            self.assertTrue(
                all(b > a for a, b in zip(retention_times, retention_times[1:]))
            )
            self.assertLessEqual(retention_times[-1], 0.840015000001)

    def test_population_invariants(self) -> None:
        for configuration in CONFIGURATIONS:
            retention = [row[1] for row in self.retention[configuration]]
            counts = [row[1] for row in self.counts[configuration]]
            self.assertEqual(retention[0], 100.0)
            self.assertTrue(all(0.0 <= value <= 100.0 for value in retention))
            self.assertTrue(all(value > 0 and value.is_integer() for value in counts))
            expected = [100.0 * value / counts[0] for value in counts]
            for actual, reference in zip(retention, expected):
                self.assertAlmostEqual(actual, reference, places=11)


if __name__ == "__main__":
    unittest.main()
