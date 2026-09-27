#!/usr/bin/env python3
"""Plot measured C90 and full-cylinder particle-population histories."""

from __future__ import annotations

import argparse
import csv
import math
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter


CONFIGURATIONS = (
    "c90_full_cylinder_equivalent",
    "full360",
)
LABELS = {
    "c90_full_cylinder_equivalent": "C90",
    "full360": "Full cylinder",
}
COUNT_LABELS = {
    "c90_full_cylinder_equivalent": (
        "C90 (full-cylinder equivalent, sector count ×4)"
    ),
    "full360": "Full cylinder (native count)",
}
COLORS = {
    "c90_full_cylinder_equivalent": "#0072B2",
    "full360": "#D55E00",
}


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--retention-csv", required=True, type=Path)
    result.add_argument("--count-csv", required=True, type=Path)
    result.add_argument("--output-dir", required=True, type=Path)
    return result


def read_series(
    path: Path, value_column: str
) -> dict[str, tuple[list[float], list[float]]]:
    expected_header = ["time_s", "configuration", value_column]
    grouped: dict[str, list[tuple[float, float]]] = defaultdict(list)

    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != expected_header:
            raise ValueError(
                f"unexpected columns in {path}: {reader.fieldnames}; "
                f"expected {expected_header}"
            )
        for row in reader:
            configuration = row["configuration"]
            if configuration not in CONFIGURATIONS:
                raise ValueError(f"unknown configuration {configuration!r}")
            time_s = float(row["time_s"])
            value = float(row[value_column])
            if not math.isfinite(time_s) or not math.isfinite(value):
                raise ValueError(f"nonfinite row in {path}")
            grouped[configuration].append((time_s, value))

    if tuple(grouped) != CONFIGURATIONS:
        raise ValueError(f"missing or reordered configuration in {path}")

    result: dict[str, tuple[list[float], list[float]]] = {}
    for configuration in CONFIGURATIONS:
        rows = grouped[configuration]
        times = [row[0] for row in rows]
        values = [row[1] for row in rows]
        if not rows or any(right <= left for left, right in zip(times, times[1:])):
            raise ValueError(f"non-increasing or empty series for {configuration}")
        result[configuration] = (times, values)
    return result


def style_axes(axis: plt.Axes, xmax: float) -> None:
    axis.set_xlim(0.0, xmax)
    axis.grid(True, color="#D9D9D9", linewidth=0.8)
    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)
    axis.tick_params(direction="out")


def plot_retention(
    series: dict[str, tuple[list[float], list[float]]], output: Path
) -> None:
    figure, axis = plt.subplots(figsize=(8.4, 5.2), constrained_layout=True)
    xmax = max(max(times) for times, _ in series.values())
    for configuration in CONFIGURATIONS:
        times, values = series[configuration]
        axis.plot(
            times,
            values,
            color=COLORS[configuration],
            marker="o",
            markersize=4.2,
            linewidth=2.0,
            label=LABELS[configuration],
        )

    style_axes(axis, xmax)
    axis.set_xlabel("Simulation time (s)")
    axis.set_ylabel("Particles retained (%)")
    axis.set_title("Particle retention")
    axis.legend(frameon=False, loc="lower left")
    axis.set_ylim(bottom=min(min(values) for _, values in series.values()) - 0.5)
    figure.savefig(
        output,
        dpi=200,
        metadata={
            "Title": "Particle retention",
            "Description": "Measured C90 and full-cylinder particle retention.",
        },
    )
    plt.close(figure)


def plot_counts(
    series: dict[str, tuple[list[float], list[float]]], output: Path
) -> None:
    figure, axis = plt.subplots(figsize=(8.4, 5.2), constrained_layout=True)
    xmax = max(max(times) for times, _ in series.values())
    for configuration in CONFIGURATIONS:
        times, values = series[configuration]
        axis.plot(
            times,
            values,
            color=COLORS[configuration],
            marker="o",
            markersize=4.2,
            linewidth=2.0,
            label=COUNT_LABELS[configuration],
        )

    style_axes(axis, xmax)
    axis.set_xlabel("Simulation time (s)")
    axis.set_ylabel("Particle count")
    axis.set_title("Particle population")
    axis.yaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value:,.0f}"))
    axis.legend(frameon=False, loc="lower left")
    axis.set_ylim(bottom=min(min(values) for _, values in series.values()) - 1000)
    figure.savefig(
        output,
        dpi=200,
        metadata={
            "Title": "Particle population",
            "Description": (
                "Measured full-cylinder count and C90 full-cylinder-equivalent "
                "count."
            ),
        },
    )
    plt.close(figure)


def main() -> None:
    arguments = parser().parse_args()
    retention = read_series(arguments.retention_csv, "retained_percent")
    counts = read_series(arguments.count_csv, "particle_count")

    for configuration in CONFIGURATIONS:
        if retention[configuration][0] != counts[configuration][0]:
            raise ValueError(f"time mismatch for {configuration}")

    arguments.output_dir.mkdir(parents=True, exist_ok=True)
    retention_output = arguments.output_dir / "particle_retention.png"
    counts_output = arguments.output_dir / "particle_count.png"
    plot_retention(retention, retention_output)
    plot_counts(counts, counts_output)
    print(f"wrote={retention_output}")
    print(f"wrote={counts_output}")


if __name__ == "__main__":
    main()
