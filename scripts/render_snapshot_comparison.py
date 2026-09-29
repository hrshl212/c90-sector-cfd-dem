#!/usr/bin/env python3
"""Render matched full-cylinder and 90-degree-sector AMReX snapshots."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import vtk
from scipy.interpolate import RegularGridInterpolator
from vtk.util.numpy_support import vtk_to_numpy


MM = 1.0e3


def read_time(plotfile: Path) -> float:
    lines = (plotfile / "Header").read_text().splitlines()
    variable_count = int(lines[1])
    return float(lines[3 + variable_count])


def read_grid(plotfile: Path, arrays: tuple[str, ...]) -> dict[str, np.ndarray]:
    reader = vtk.vtkAMReXGridReader()
    reader.SetFileName(str(plotfile))
    reader.UpdateInformation()
    selection = reader.GetCellDataArraySelection()
    selection.DisableAllArrays()
    for name in arrays:
        selection.EnableArray(name)
    reader.Update()

    output = reader.GetOutputDataObject(0)
    blocks = [
        output.GetDataSet(0, index)
        for index in range(output.GetNumberOfDataSets(0))
    ]
    blocks = [block for block in blocks if block is not None]
    spacing = np.asarray(blocks[0].GetSpacing())
    lower = np.min([np.asarray(block.GetOrigin()) for block in blocks], axis=0)
    upper = np.max(
        [np.asarray(block.GetBounds())[[1, 3, 5]] for block in blocks], axis=0
    )
    shape_xyz = np.rint((upper - lower) / spacing).astype(int)
    fields = {
        name: np.full(tuple(shape_xyz[::-1]), np.nan, dtype=float) for name in arrays
    }

    for block in blocks:
        origin = np.asarray(block.GetOrigin())
        start = np.rint((origin - lower) / spacing).astype(int)
        dimensions = np.asarray(block.GetDimensions()) - 1
        slices = tuple(
            slice(start[axis], start[axis] + dimensions[axis])
            for axis in (2, 1, 0)
        )
        block_shape = tuple(dimensions[::-1])
        for name in arrays:
            values = vtk_to_numpy(block.GetCellData().GetArray(name))
            fields[name][slices] = values.reshape(block_shape)

    fields["x"] = lower[0] + (np.arange(shape_xyz[0]) + 0.5) * spacing[0]
    fields["y"] = lower[1] + (np.arange(shape_xyz[1]) + 0.5) * spacing[1]
    fields["z"] = lower[2] + (np.arange(shape_xyz[2]) + 0.5) * spacing[2]
    return fields


def read_particles(plotfile: Path) -> tuple[np.ndarray, np.ndarray]:
    reader = vtk.vtkAMReXParticlesReader()
    reader.SetPlotFileName(str(plotfile))
    reader.UpdateInformation()
    selection = reader.GetPointDataArraySelection()
    selection.DisableAllArrays()
    selection.EnableArray("velz")
    reader.Update()

    output = reader.GetOutputDataObject(0)
    points: list[np.ndarray] = []
    velocity: list[np.ndarray] = []
    for block_index in range(output.GetNumberOfBlocks()):
        block = output.GetBlock(block_index)
        if block is None:
            continue
        for piece_index in range(block.GetNumberOfPieces()):
            piece = block.GetPiece(piece_index)
            if piece is None or piece.GetNumberOfPoints() == 0:
                continue
            points.append(vtk_to_numpy(piece.GetPoints().GetData()))
            velocity.append(vtk_to_numpy(piece.GetPointData().GetArray("velz")))
    return np.concatenate(points), np.concatenate(velocity)


def sector_diagonal(fields: dict[str, np.ndarray]) -> tuple[np.ndarray, ...]:
    radius = np.linspace(0.0, min(fields["x"][-1], fields["y"][-1]), 180)
    rr, zz = np.meshgrid(radius, fields["z"])
    xy = rr / np.sqrt(2.0)
    samples = np.column_stack((zz.ravel(), xy.ravel(), xy.ravel()))
    result = []
    for name in ("w_g", "volfrac"):
        interpolator = RegularGridInterpolator(
            (fields["z"], fields["y"], fields["x"]),
            fields[name],
            bounds_error=False,
            fill_value=np.nan,
        )
        result.append(interpolator(samples).reshape(rr.shape))
    return radius, fields["z"], *result


def fluid_mask(values: np.ndarray, volume_fraction: np.ndarray) -> np.ma.MaskedArray:
    return np.ma.masked_where((volume_fraction < 0.5) | ~np.isfinite(values), values)


def style_axis(axis: plt.Axes) -> None:
    axis.spines[["top", "right"]].set_visible(False)
    axis.tick_params(direction="out", length=3.5, width=0.8)


def plot_flow(
    full: dict[str, np.ndarray],
    sector: dict[str, np.ndarray],
    full_time: float,
    sector_time: float,
    output: Path,
) -> None:
    center_y = int(np.argmin(np.abs(full["y"])))
    full_w = fluid_mask(full["w_g"][:, center_y, :], full["volfrac"][:, center_y, :])
    radius, sector_z, sector_w_raw, sector_vf = sector_diagonal(sector)
    sector_w = fluid_mask(sector_w_raw, sector_vf)

    combined = np.concatenate((full_w.compressed(), sector_w.compressed()))
    lower, upper = np.nanpercentile(combined, (1.0, 99.5))
    lower = min(lower, 0.0)
    levels = np.linspace(lower, upper, 80)

    fig, axes = plt.subplots(1, 2, figsize=(10.8, 6.2), constrained_layout=True)
    panels = (
        (axes[0], full["x"] * MM, full["z"] * MM, full_w, "Full 360° cylinder", "x (mm)"),
        (axes[1], radius * MM, sector_z * MM, sector_w, "90° rotational sector", "r along θ = 45° (mm)"),
    )
    contour = None
    for axis, horizontal, vertical, field, title, xlabel in panels:
        contour = axis.contourf(
            horizontal,
            vertical,
            field,
            levels=levels,
            cmap="turbo",
            extend="both",
        )
        axis.contour(
            horizontal,
            vertical,
            np.ma.getmaskarray(field),
            levels=[0.5],
            colors="#232a31",
            linewidths=0.7,
        )
        axis.set_title(title, fontsize=13, weight="semibold", pad=10)
        axis.set_xlabel(xlabel)
        axis.set_ylabel("z (mm)")
        axis.set_ylim(max(full["z"][0], sector["z"][0]) * MM, 39.35)
        style_axis(axis)
    colorbar = fig.colorbar(contour, ax=axes, location="bottom", shrink=0.78, pad=0.08)
    colorbar.set_label("Axial gas velocity, $w_g$ (m s$^{-1}$)")
    fig.suptitle(
        "Matched gas-flow structure\n"
        f"full: t = {full_time:.6f} s  ·  sector: t = {sector_time:.6f} s",
        fontsize=15,
        weight="semibold",
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def deterministic_sample(
    points: np.ndarray, values: np.ndarray, limit: int
) -> tuple[np.ndarray, np.ndarray]:
    if len(points) <= limit:
        return points, values
    indices = np.linspace(0, len(points) - 1, limit, dtype=int)
    return points[indices], values[indices]


def geometry_profile(fields: dict[str, np.ndarray]) -> tuple[np.ndarray, np.ndarray]:
    center_y = int(np.argmin(np.abs(fields["y"])))
    cross_section = fields["volfrac"][:, center_y, :] >= 0.5
    radii = np.full(len(fields["z"]), np.nan)
    for z_index, row in enumerate(cross_section):
        if np.any(row):
            radii[z_index] = np.max(np.abs(fields["x"][row]))
    valid = np.isfinite(radii)
    return fields["z"][valid] * MM, radii[valid] * MM


def draw_geometry(
    axis: plt.Axes,
    profile_z: np.ndarray,
    profile_r: np.ndarray,
    sector: bool,
) -> None:
    if sector:
        theta = np.linspace(0.0, np.pi / 2.0, 100)
        angles = (0.0, np.pi / 2.0)
    else:
        theta = np.linspace(0.0, 2.0 * np.pi, 160)
        angles = (0.0, np.pi / 2.0, np.pi, 3.0 * np.pi / 2.0)
    line = dict(color="#263746", linewidth=0.8, alpha=0.78)
    transition = np.flatnonzero(np.abs(np.diff(profile_r)) > 0.15)
    ring_indices = np.unique(np.concatenate(([0], transition, transition + 1, [-1])))
    for index in ring_indices:
        radius = profile_r[index]
        z_value = profile_z[index]
        axis.plot(radius * np.cos(theta), radius * np.sin(theta), z_value, **line)
    for angle in angles:
        axis.plot(
            profile_r * np.cos(angle),
            profile_r * np.sin(angle),
            profile_z,
            **line,
        )
    if sector:
        for index in ring_indices:
            radius = profile_r[index]
            z_value = profile_z[index]
            for angle in (0.0, np.pi / 2.0):
                axis.plot(
                    [0.0, radius * np.cos(angle)],
                    [0.0, radius * np.sin(angle)],
                    [z_value, z_value],
                    **line,
                )
        axis.plot(
            np.zeros_like(profile_z),
            np.zeros_like(profile_z),
            profile_z,
            **line,
        )


def plot_particles(
    full_points: np.ndarray,
    full_velocity: np.ndarray,
    sector_points: np.ndarray,
    sector_velocity: np.ndarray,
    profile_z: np.ndarray,
    profile_r: np.ndarray,
    full_time: float,
    sector_time: float,
    output: Path,
) -> None:
    full_count = len(full_points)
    sector_count = len(sector_points)
    full_points, full_velocity = deterministic_sample(full_points, full_velocity, 70000)
    sector_points, sector_velocity = deterministic_sample(sector_points, sector_velocity, 35000)
    all_velocity = np.concatenate((full_velocity, sector_velocity))
    v_min, v_max = np.nanpercentile(all_velocity, (1.0, 99.0))
    norm = mpl.colors.Normalize(vmin=v_min, vmax=v_max)

    fig = plt.figure(figsize=(11.2, 6.6), constrained_layout=True)
    axes = [
        fig.add_subplot(1, 2, 1, projection="3d"),
        fig.add_subplot(1, 2, 2, projection="3d"),
    ]
    panels = (
        (
            axes[0],
            full_points,
            full_velocity,
            f"Full 360° cylinder\n{full_count:,} particles",
            False,
        ),
        (
            axes[1],
            sector_points,
            sector_velocity,
            f"90° rotational sector\n{sector_count:,} particles (×4 = {4 * sector_count:,})",
            True,
        ),
    )
    scatter = None
    for axis, points, velocity, title, is_sector in panels:
        scatter = axis.scatter(
            points[:, 0] * MM,
            points[:, 1] * MM,
            points[:, 2] * MM,
            c=velocity,
            cmap="viridis",
            norm=norm,
            s=0.35,
            alpha=0.48,
            linewidths=0,
            rasterized=True,
        )
        draw_geometry(axis, profile_z, profile_r, is_sector)
        axis.set_title(title, fontsize=13, weight="semibold", pad=10)
        axis.set_xlabel("x (mm)", labelpad=2)
        axis.set_ylabel("y (mm)", labelpad=2)
        axis.set_zlabel("z (mm)", labelpad=4)
        axis.set_zlim(0.0, 40.0)
        if is_sector:
            axis.set_xlim(0.0, 4.6)
            axis.set_ylim(0.0, 4.6)
            axis.set_box_aspect((1, 1, 3.0))
        else:
            axis.set_xlim(-4.6, 4.6)
            axis.set_ylim(-4.6, 4.6)
            axis.set_box_aspect((2, 2, 3.0))
        axis.view_init(elev=20, azim=-58)
        axis.xaxis.set_major_locator(mpl.ticker.MaxNLocator(5))
        axis.yaxis.set_major_locator(mpl.ticker.MaxNLocator(5))
        axis.zaxis.set_major_locator(mpl.ticker.MaxNLocator(6))
        axis.grid(False)
        axis.xaxis.pane.set_alpha(0.0)
        axis.yaxis.pane.set_alpha(0.0)
        axis.zaxis.pane.set_alpha(0.0)
    colorbar = fig.colorbar(scatter, ax=axes, location="bottom", shrink=0.75, pad=0.09)
    colorbar.set_label("Particle axial velocity, $v_{p,z}$ (m s$^{-1}$)")
    fig.suptitle(
        "Particle distribution inside the simulated geometry\n"
        f"full: t = {full_time:.6f} s  ·  sector: t = {sector_time:.6f} s",
        fontsize=15,
        weight="semibold",
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full-flow", type=Path, required=True)
    parser.add_argument("--full-particles", type=Path)
    parser.add_argument("--sector-flow", type=Path, required=True)
    parser.add_argument("--sector-particles", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    full_particles_path = args.full_particles or args.full_flow
    full_time = read_time(args.full_flow)
    sector_time = read_time(args.sector_flow)
    full_grid = read_grid(args.full_flow, ("w_g", "volfrac"))
    sector_grid = read_grid(args.sector_flow, ("w_g", "volfrac"))
    full_points, full_velocity = read_particles(full_particles_path)
    sector_points, sector_velocity = read_particles(args.sector_particles)
    profile_z, profile_r = geometry_profile(full_grid)

    plot_flow(
        full_grid,
        sector_grid,
        full_time,
        sector_time,
        args.output_dir / "matched_gas_flow.png",
    )
    plot_particles(
        full_points,
        full_velocity,
        sector_points,
        sector_velocity,
        profile_z,
        profile_r,
        full_time,
        sector_time,
        args.output_dir / "matched_particle_geometry.png",
    )


if __name__ == "__main__":
    main()
