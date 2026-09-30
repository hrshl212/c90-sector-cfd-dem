#!/usr/bin/env python3
"""Render matched full-cylinder and 90-degree-sector AMReX snapshots."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import vtk
from matplotlib.patches import Patch, Rectangle
from vtk.util.numpy_support import vtk_to_numpy


MM = 1.0e3
LIQUID_VELOCITY_MIN = 0.0
LIQUID_VELOCITY_MAX = 0.002


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
    piston_z0: float,
    piston_speed: float,
    piston_radius: float,
    output: Path,
) -> None:
    center_y = int(np.argmin(np.abs(full["y"])))
    full_w = fluid_mask(full["w_g"][:, center_y, :], full["volfrac"][:, center_y, :])
    sector_y = int(np.argmin(np.abs(sector["y"])))
    sector_w = fluid_mask(
        sector["w_g"][:, sector_y, :], sector["volfrac"][:, sector_y, :]
    )

    levels = np.linspace(LIQUID_VELOCITY_MIN, LIQUID_VELOCITY_MAX, 80)

    fig, axes = plt.subplots(2, 1, figsize=(12.5, 5.8), constrained_layout=True)
    panels = (
        (
            axes[0],
            full["z"] * MM,
            full["x"] * MM,
            full_w.T,
            "Full 360° cylinder",
            full_time,
            False,
        ),
        (
            axes[1],
            sector["z"] * MM,
            sector["x"] * MM,
            sector_w.T,
            "90° rotational sector",
            sector_time,
            True,
        ),
    )
    contour = None
    for axis, horizontal, vertical, field, title, time_s, is_sector in panels:
        contour = axis.contourf(
            horizontal,
            vertical,
            np.ma.clip(field, LIQUID_VELOCITY_MIN, LIQUID_VELOCITY_MAX),
            levels=levels,
            cmap="turbo",
            extend="max",
        )
        axis.contour(
            horizontal,
            vertical,
            np.ma.getmaskarray(field),
            levels=[0.5],
            colors="#232a31",
            linewidths=0.7,
        )
        piston_z = (piston_z0 + piston_speed * time_s) * MM
        piston_bottom = 0.0 if is_sector else -piston_radius * MM
        piston_height = piston_radius * MM if is_sector else 2.0 * piston_radius * MM
        axis.add_patch(
            Rectangle(
                (0.0, piston_bottom),
                piston_z,
                piston_height,
                facecolor="#f7f7f5",
                edgecolor="#39434c",
                hatch="////",
                linewidth=0.9,
                zorder=5,
            )
        )
        axis.set_title(title, fontsize=13, weight="semibold", pad=10)
        axis.set_xlabel("z (mm)")
        axis.set_ylabel("x (mm)")
        axis.set_xlim(0.0, 39.4)
        axis.set_ylim(-4.6, 4.6)
        axis.set_aspect("equal", adjustable="box")
        style_axis(axis)
    axes[0].legend(
        handles=[
            Patch(
                facecolor="#f7f7f5",
                edgecolor="#39434c",
                hatch="////",
                label="penalized IBM piston",
            )
        ],
        loc="upper right",
        frameon=True,
        framealpha=0.95,
        fontsize=9,
    )
    colorbar = fig.colorbar(contour, ax=axes, location="right", shrink=0.82, pad=0.025)
    colorbar.set_ticks(np.linspace(LIQUID_VELOCITY_MIN, LIQUID_VELOCITY_MAX, 6))
    colorbar.set_label("Axial liquid velocity (m s$^{-1}$)")
    fig.suptitle(
        "Matched liquid-flow structure\n"
        f"full: t = {full_time:.6f} s  ·  sector: t = {sector_time:.6f} s",
        fontsize=15,
        weight="semibold",
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def plot_cross_section(
    full: dict[str, np.ndarray],
    sector: dict[str, np.ndarray],
    full_time: float,
    sector_time: float,
    output: Path,
) -> None:
    target_z = 0.005
    full_k = int(np.argmin(np.abs(full["z"] - target_z)))
    sector_k = int(np.argmin(np.abs(sector["z"] - target_z)))
    full_w = fluid_mask(full["w_g"][full_k], full["volfrac"][full_k]).T
    sector_w = fluid_mask(sector["w_g"][sector_k], sector["volfrac"][sector_k]).T
    levels = np.linspace(LIQUID_VELOCITY_MIN, LIQUID_VELOCITY_MAX, 80)

    fig, axes = plt.subplots(1, 2, figsize=(10.5, 5.2), constrained_layout=True)
    panels = (
        (axes[0], full["y"] * MM, full["x"] * MM, full_w, "Full 360° cylinder"),
        (
            axes[1],
            sector["y"] * MM,
            sector["x"] * MM,
            sector_w,
            "90° rotational sector",
        ),
    )
    contour = None
    for axis, horizontal, vertical, field, title in panels:
        contour = axis.contourf(
            horizontal,
            vertical,
            np.ma.clip(field, LIQUID_VELOCITY_MIN, LIQUID_VELOCITY_MAX),
            levels=levels,
            cmap="turbo",
            extend="max",
        )
        axis.contour(
            horizontal,
            vertical,
            np.ma.getmaskarray(field),
            levels=[0.5],
            colors="#232a31",
            linewidths=0.8,
        )
        axis.set_title(title, fontsize=13, weight="semibold", pad=9)
        axis.set_xlabel("y (mm)")
        axis.set_ylabel("x (mm)")
        axis.set_xlim(-4.9, 4.9)
        axis.set_ylim(-4.9, 4.9)
        axis.set_aspect("equal", adjustable="box")
        style_axis(axis)
    colorbar = fig.colorbar(contour, ax=axes, location="right", shrink=0.82, pad=0.03)
    colorbar.set_ticks(np.linspace(LIQUID_VELOCITY_MIN, LIQUID_VELOCITY_MAX, 6))
    colorbar.set_label("Axial liquid velocity (m s$^{-1}$)")
    fig.suptitle(
        "Liquid-velocity cross section at z = 5 mm\n"
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


def draw_3d_geometry(
    axis: plt.Axes, profile_z: np.ndarray, profile_r: np.ndarray, sector: bool
) -> None:
    line = dict(color="#263746", linewidth=0.8, alpha=0.78)
    transition = np.flatnonzero(np.abs(np.diff(profile_r)) > 0.15)
    ring_indices = np.unique(np.concatenate(([0], transition, transition + 1, [-1])))
    if sector:
        theta = np.linspace(0.0, np.pi / 2.0, 80)
        generators = (0.0, np.pi / 4.0, np.pi / 2.0)
    else:
        theta = np.linspace(0.0, 2.0 * np.pi, 150)
        generators = (0.0, np.pi / 2.0, np.pi, 3.0 * np.pi / 2.0)
    for index in ring_indices:
        radius = profile_r[index]
        z_value = profile_z[index]
        axis.plot(
            np.full_like(theta, z_value),
            radius * np.cos(theta),
            radius * np.sin(theta),
            **line,
        )
        if sector:
            axis.plot([z_value, z_value], [0.0, radius], [0.0, 0.0], **line)
            axis.plot([z_value, z_value], [0.0, 0.0], [0.0, radius], **line)
    for angle in generators:
        axis.plot(
            profile_z,
            profile_r * np.cos(angle),
            profile_r * np.sin(angle),
            **line,
        )
    if sector:
        axis.plot(profile_z, np.zeros_like(profile_z), np.zeros_like(profile_z), **line)


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

    fig = plt.figure(figsize=(13.0, 8.2))
    axes = [
        fig.add_axes((0.02, 0.51, 0.84, 0.32), projection="3d"),
        fig.add_axes((0.02, 0.07, 0.84, 0.32), projection="3d"),
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
            points[:, 2] * MM,
            points[:, 0] * MM,
            points[:, 1] * MM,
            c=velocity,
            cmap="viridis",
            norm=norm,
            s=0.35,
            alpha=0.48,
            linewidths=0,
            rasterized=True,
        )
        draw_3d_geometry(axis, profile_z, profile_r, is_sector)
        axis.set_xlabel("z (mm)")
        axis.set_ylabel("x (mm)", labelpad=2)
        axis.set_zlabel("y (mm)", labelpad=2)
        axis.set_xlim(0.0, 39.4)
        axis.set_ylim(-4.6, 4.6)
        axis.set_zlim(-4.6, 4.6)
        axis.set_box_aspect((4.3, 1.0, 1.0), zoom=1.52)
        axis.view_init(elev=17, azim=-72)
        axis.xaxis.set_major_locator(mpl.ticker.MaxNLocator(5))
        axis.yaxis.set_major_locator(mpl.ticker.MaxNLocator(3))
        axis.zaxis.set_major_locator(mpl.ticker.MaxNLocator(3))
        axis.tick_params(pad=0, labelsize=8)
        axis.grid(False)
        axis.xaxis.pane.set_alpha(0.0)
        axis.yaxis.pane.set_alpha(0.0)
        axis.zaxis.pane.set_alpha(0.0)
    fig.text(0.44, 0.85, panels[0][3], ha="center", va="center", fontsize=12, weight="semibold")
    fig.text(0.44, 0.41, panels[1][3], ha="center", va="center", fontsize=12, weight="semibold")
    color_axis = fig.add_axes((0.90, 0.17, 0.018, 0.64))
    colorbar = fig.colorbar(scatter, cax=color_axis)
    colorbar.set_label("Particle axial velocity, $v_{p,z}$ (m s$^{-1}$)")
    fig.suptitle(
        "Particle distribution inside the simulated geometry\n"
        f"full: t = {full_time:.6f} s  ·  sector: t = {sector_time:.6f} s",
        fontsize=15,
        weight="semibold",
        y=0.97,
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
    parser.add_argument("--piston-z0", type=float, default=0.0002)
    parser.add_argument("--piston-speed", type=float, default=0.0017)
    parser.add_argument("--piston-radius", type=float, default=0.00433)
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
        args.piston_z0,
        args.piston_speed,
        args.piston_radius,
        args.output_dir / "matched_liquid_flow.png",
    )
    plot_cross_section(
        full_grid,
        sector_grid,
        full_time,
        sector_time,
        args.output_dir / "matched_liquid_velocity_cross_section_z5mm.png",
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
