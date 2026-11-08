#!/usr/bin/env python3
"""Build G-code, coordinate table and verification plots for the duck contour."""
from __future__ import annotations

import math
from pathlib import Path

from geometry import build, fmt

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent

TOOL_DIA = 8.0  # mm
TOOL_RAD = TOOL_DIA / 2.0
SAFE_Z = 20.0
RAPID_Z = 5.0
CUT_Z = -5.0
FEED_XY = 200.0
FEED_Z = 80.0
SPINDLE = 1200


def ij(start, center):
    return center[0] - start[0], center[1] - start[1]


def xyz(x, y, n=3):
    return f"X{x:.{n}f} Y{y:.{n}f}"


def write_gcode(segs, pts, path: Path):
    P2 = pts["P2"]
    # Lead-in / lead-out: extension of the first segment (vertical X=-25) above P2.
    # Clockwise around the part + G41 → cutter to the left of travel = outside.
    lead = 40.0
    pin = (P2[0], P2[1] + lead)  # (-25, 240)
    park = (50.0, 260.0)

    xs = [p[0] for k, p in pts.items() if k.startswith("P")]
    ys = [p[1] for k, p in pts.items() if k.startswith("P")]
    xmin, xmax = min(xs) - 20, max(xs) + 20
    ymin, ymax = min(ys) - 20, max(ys) + 20

    n = [0]

    def nxt():
        n[0] += 10
        return f"N{n[0]:03d}"

    lines = []
    a = lines.append
    a("%")
    a("O0001")
    a("(DUCK CONTOUR)")
    a("(XY: X0 vertical axis, Y0 lower 150 datum)")
    a(f"(Tool T1 D{TOOL_DIA:.0f}mm  set D1={TOOL_RAD:.1f} RADIUS)")
    a(f"(Depth Z{CUT_Z:.1f}  stock X[{xmin:.0f}..{xmax:.0f}] Y[{ymin:.0f}..{ymax:.0f}] Z10)")
    a(f"{nxt()} G21 G17 G40 G49 G80 G90 G94")
    a(f"{nxt()} G54")
    a(f"{nxt()} T1 M06")
    a(f"{nxt()} S{SPINDLE:.0f} M03")
    a(f"{nxt()} M08")
    a(f"{nxt()} G00 {xyz(*pin)}")
    a(f"{nxt()} G00 Z{SAFE_Z:.1f}")
    a(f"{nxt()} G00 Z{RAPID_Z:.1f}")
    a(f"{nxt()} G01 Z{CUT_Z:.1f} F{FEED_Z:.0f}        (plunge)")
    a(f"{nxt()} G41 D1 G01 {xyz(*P2)} F{FEED_XY:.0f}    (lead-in to P2)")

    comments = {
        "head_right": "P2-P3 head right",
        "R55": "P3-P4 R55 neck",
        "25deg": "P4-P5 25deg breast",
        "R115": "P5-P6 R115 back",
        "5deg": "P6-P7 5deg to tail",
        "lower_tail": "P7-P8 lower tail",
        "R116": "P8-P9 R116",
        "bottom": "P9-P10 bottom",
        "R145": "P10-P11 R145 belly",
        "80deg": "P11-P1 80deg left",
        "R60": "P1-P2 R60 head",
    }

    for s in segs:
        note = comments.get(s.name, s.name)
        if s.kind == "line":
            a(f"{nxt()} G01 {xyz(*s.p1)}            ({note})")
        else:
            i, j = ij(s.p0, s.center)
            a(f"{nxt()} {s.g} {xyz(*s.p1)} I{i:.3f} J{j:.3f}    ({note})")

    a(f"{nxt()} G40 G01 {xyz(*pin)}            (lead-out, cancel G41)")
    a(f"{nxt()} G00 Z{SAFE_Z:.1f}")
    a(f"{nxt()} G00 {xyz(*park)}            (park)")
    a(f"{nxt()} M09")
    a(f"{nxt()} M05")
    a(f"{nxt()} M30")
    a("%")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path, pin


def write_preview(segs, pts, pin, path: Path):
    """Contour-only program without cutter comp — for NC viewers."""
    lines = ["%", "O0002", "(DUCK CONTOUR PREVIEW, no G41)"]
    n = [0]

    def nxt():
        n[0] += 10
        return f"N{n[0]:03d}"

    a = lines.append
    a(f"{nxt()} G21 G17 G40 G90")
    a(f"{nxt()} G00 {xyz(*pin)}")
    a(f"{nxt()} G00 Z{RAPID_Z:.1f}")
    a(f"{nxt()} G01 Z{CUT_Z:.1f} F{FEED_Z:.0f}")
    a(f"{nxt()} G01 {xyz(*pts['P2'])} F{FEED_XY:.0f}")
    for s in segs:
        if s.kind == "line":
            a(f"{nxt()} G01 {xyz(*s.p1)}")
        else:
            i, j = ij(s.p0, s.center)
            a(f"{nxt()} {s.g} {xyz(*s.p1)} I{i:.3f} J{j:.3f}")
    a(f"{nxt()} G00 Z{SAFE_Z:.1f}")
    a(f"{nxt()} M30")
    a("%")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_table(pts, segs, path: Path):
    rows = [
        "# Опорные точки контура",
        "",
        "Система координат как на чертеже: **X = 0** — вертикальная ось, **Y = 0** — нижняя штриховая линия размера 150.",
        "",
        "| Точка | X, мм | Y, мм | Описание |",
        "|-------|------:|------:|----------|",
    ]
    desc = {
        "P1": "Сопряжение R60 и левой стороны 80°",
        "P2": "Сопряжение R60 и правой стороны головы",
        "P3": "Сопряжение правой стороны и R55 (Y = 150)",
        "P4": "Сопряжение R55 и груди 25°",
        "P5": "Сопряжение груди 25° и R115",
        "P6": "Сопряжение R115 и спины 5°",
        "P7": "Хвост, острый угол (X = 305)",
        "P8": "Сопряжение нижней линии хвоста и R116",
        "P9": "Сопряжение R116 и нижнего основания",
        "P10": "Сопряжение нижнего основания и R145",
        "P11": "Сопряжение R145 и левой стороны 80°",
        "C60": "Центр R60",
        "C55": "Центр R55",
        "C115": "Центр R115",
        "C116": "Центр R116",
        "C145": "Центр R145",
    }
    for k in [
        "P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8", "P9", "P10", "P11",
        "C60", "C55", "C115", "C116", "C145",
    ]:
        x, y = fmt(pts[k])
        rows.append(f"| {k} | {x:.3f} | {y:.3f} | {desc[k]} |")

    rows += [
        "",
        "## Проверки",
        "",
        "| Условие | Значение |",
        "|---------|----------|",
        f"| Vert. span P1–P11 | {pts['P1'][1] - pts['P11'][1]:.3f} (должно быть 200) |",
        f"| P7.X | {pts['P7'][0]:.3f} (должно быть 305) |",
        f"| P3.Y | {pts['P3'][1]:.3f} (должно быть 150) |",
        f"| C60.X | {pts['C60'][0]:.3f} (должно быть −85) |",
        f"| \\|C60−P1\\| | {math.hypot(*[pts['C60'][i]-pts['P1'][i] for i in (0,1)]):.3f} |",
        f"| \\|C60−P2\\| | {math.hypot(*[pts['C60'][i]-pts['P2'][i] for i in (0,1)]):.3f} |",
        f"| \\|C55−P3\\| | {math.hypot(*[pts['C55'][i]-pts['P3'][i] for i in (0,1)]):.3f} |",
        f"| \\|C55−P4\\| | {math.hypot(*[pts['C55'][i]-pts['P4'][i] for i in (0,1)]):.3f} |",
        f"| \\|C115−P5\\| | {math.hypot(*[pts['C115'][i]-pts['P5'][i] for i in (0,1)]):.3f} |",
        f"| \\|C115−P6\\| | {math.hypot(*[pts['C115'][i]-pts['P6'][i] for i in (0,1)]):.3f} |",
        f"| \\|C116−P8\\| | {math.hypot(*[pts['C116'][i]-pts['P8'][i] for i in (0,1)]):.3f} |",
        f"| \\|C116−P9\\| | {math.hypot(*[pts['C116'][i]-pts['P9'][i] for i in (0,1)]):.3f} |",
        f"| \\|C145−P10\\| | {math.hypot(*[pts['C145'][i]-pts['P10'][i] for i in (0,1)]):.3f} |",
        f"| \\|C145−P11\\| | {math.hypot(*[pts['C145'][i]-pts['P11'][i] for i in (0,1)]):.3f} |",
        "",
    ]
    path.write_text("\n".join(rows), encoding="utf-8")


def plot_contour(segs, pts, pin, path: Path):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Arc, FancyArrowPatch
    import numpy as np

    fig, ax = plt.subplots(figsize=(11, 8), dpi=140)
    ax.set_aspect("equal")

    def arc_xy(c, a, b, r, g, n=80):
        a0 = math.atan2(a[1] - c[1], a[0] - c[0])
        a1 = math.atan2(b[1] - c[1], b[0] - c[0])
        if g == "G02":  # CW
            da = a0 - a1
            if da <= 0:
                da += 2 * math.pi
            angs = a0 - np.linspace(0, da, n)
        else:
            da = a1 - a0
            if da <= 0:
                da += 2 * math.pi
            angs = a0 + np.linspace(0, da, n)
        return c[0] + r * np.cos(angs), c[1] + r * np.sin(angs)

    xs, ys = [], []
    for s in segs:
        if s.kind == "line":
            ax.plot([s.p0[0], s.p1[0]], [s.p0[1], s.p1[1]], color="#1a1a1a", lw=2.2)
            xs += [s.p0[0], s.p1[0]]
            ys += [s.p0[1], s.p1[1]]
        else:
            x, y = arc_xy(s.center, s.p0, s.p1, s.r, s.g)
            ax.plot(x, y, color="#1a1a1a", lw=2.2)
            xs += list(x)
            ys += list(y)

    # lead-in / lead-out
    ax.plot([pin[0], pts["P2"][0]], [pin[1], pts["P2"][1]], color="#2a9d4a", lw=1.8, ls="--", label="заход / выход")
    ax.scatter(*pin, c="#2a9d4a", s=28, zorder=5)
    ax.annotate("заход", pin, textcoords="offset points", xytext=(8, 6), color="#2a9d4a", fontsize=8)

    for name in ["P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8", "P9", "P10", "P11"]:
        p = pts[name]
        ax.scatter(*p, c="#c0392b", s=18, zorder=6)
        ax.annotate(name, p, textcoords="offset points", xytext=(4, 4), fontsize=7, color="#7b1e16")

    ax.axhline(0, color="#4c7bd9", lw=0.8, ls=":", alpha=0.8)
    ax.axvline(0, color="#4c7bd9", lw=0.8, ls=":", alpha=0.8)
    ax.set_xlabel("X, мм")
    ax.set_ylabel("Y, мм")
    ax.set_title("Контур фрезерования (обход по часовой, G41 снаружи)")
    ax.grid(True, alpha=0.25)
    ax.legend(loc="lower right")
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def overlay_drawing(segs, pts, path: Path):
    from PIL import Image, ImageDraw

    src = Path("/home/ubuntu/.cursor/projects/workspace/assets/ff686c79-8064-4fdb-abbd-fd8c101229f7.png")
    if not src.exists():
        return
    im = Image.open(src).convert("RGB")
    dr = ImageDraw.Draw(im)
    x0, y0 = 171.0, 217.0
    s = 0.630  # px/mm, mean of 85 and 305 and 150

    def to_px(p):
        return x0 + p[0] * s, y0 - p[1] * s

    import numpy as np

    for seg in segs:
        if seg.kind == "line":
            dr.line([to_px(seg.p0), to_px(seg.p1)], fill=(220, 30, 30), width=2)
        else:
            c, a, b, r, g = seg.center, seg.p0, seg.p1, seg.r, seg.g
            a0 = math.atan2(a[1] - c[1], a[0] - c[0])
            a1 = math.atan2(b[1] - c[1], b[0] - c[0])
            if g == "G02":
                da = a0 - a1
                if da <= 0:
                    da += 2 * math.pi
                angs = a0 - np.linspace(0, da, max(20, int(da / 0.05)))
            else:
                da = a1 - a0
                if da <= 0:
                    da += 2 * math.pi
                angs = a0 + np.linspace(0, da, max(20, int(da / 0.05)))
            poly = [to_px((c[0] + r * math.cos(t), c[1] + r * math.sin(t))) for t in angs]
            if len(poly) >= 2:
                dr.line(poly, fill=(220, 30, 30), width=2)
    im.save(path)


def simulate_gcode(nc_path: Path, plot_path: Path):
    """Parse the NC file and plot programmed path (without cutter comp)."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import re

    x = y = None
    mode = "G00"
    xs, ys = [], []
    cx, cy = [], []
    cutting = False
    for raw in nc_path.read_text(encoding="utf-8").splitlines():
        line = raw.split("(")[0].strip()
        if not line or line in {"%", "M30"}:
            continue
        if re.search(r"G00\b", line):
            mode = "G00"
            cutting = False
        if re.search(r"G01\b", line):
            mode = "G01"
            cutting = True
        if re.search(r"G02\b", line):
            mode = "G02"
            cutting = True
        if re.search(r"G03\b", line):
            mode = "G03"
            cutting = True
        mx = re.search(r"X(-?\d+\.?\d*)", line)
        my = re.search(r"Y(-?\d+\.?\d*)", line)
        mi = re.search(r"I(-?\d+\.?\d*)", line)
        mj = re.search(r"J(-?\d+\.?\d*)", line)
        if x is None:
            x = float(mx.group(1)) if mx else 0.0
            y = float(my.group(1)) if my else 0.0
            xs.append(x)
            ys.append(y)
            continue
        nx, ny = x, y
        if mx:
            nx = float(mx.group(1))
        if my:
            ny = float(my.group(1))
        if mode in ("G02", "G03") and mi and mj:
            i, j = float(mi.group(1)), float(mj.group(1))
            cc = (x + i, y + j)
            r = math.hypot(i, j)
            a0 = math.atan2(y - cc[1], x - cc[0])
            a1 = math.atan2(ny - cc[1], nx - cc[0])
            if mode == "G02":
                da = a0 - a1
                if da <= 0:
                    da += 2 * math.pi
                angs = [a0 - da * t / 40 for t in range(1, 41)]
            else:
                da = a1 - a0
                if da <= 0:
                    da += 2 * math.pi
                angs = [a0 + da * t / 40 for t in range(1, 41)]
            for t in angs:
                xs.append(cc[0] + r * math.cos(t))
                ys.append(cc[1] + r * math.sin(t))
                if cutting:
                    cx.append(xs[-1])
                    cy.append(ys[-1])
        else:
            xs.append(nx)
            ys.append(ny)
            if cutting:
                cx.append(nx)
                cy.append(ny)
        x, y = nx, ny

    fig, ax = plt.subplots(figsize=(11, 8), dpi=140)
    ax.set_aspect("equal")
    ax.plot(xs, ys, color="#95a5a6", lw=1.0, ls=":", label="ускоренный / отвод")
    ax.plot(cx, cy, color="#c0392b", lw=2.0, label="рабочий ход (контур)")
    ax.axhline(0, color="#4c7bd9", lw=0.7, ls=":", alpha=0.7)
    ax.axvline(0, color="#4c7bd9", lw=0.7, ls=":", alpha=0.7)
    ax.set_title("Траектория из duck.nc (без смещения фрезы)")
    ax.set_xlabel("X, мм")
    ax.set_ylabel("Y, мм")
    ax.grid(True, alpha=0.25)
    ax.legend(loc="lower right")
    fig.tight_layout()
    fig.savefig(plot_path, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main():
    segs, pts = build()
    nc, pin = write_gcode(segs, pts, ROOT / "duck.nc")
    write_preview(segs, pts, pin, ROOT / "duck_preview.nc")
    write_table(pts, segs, ROOT / "coordinates.md")
    plot_contour(segs, pts, pin, ROOT / "contour.png")
    overlay_drawing(segs, pts, ROOT / "overlay_on_drawing.png")
    simulate_gcode(nc, ROOT / "toolpath_from_nc.png")
    print("wrote", nc)
    for k in ["P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8", "P9", "P10", "P11"]:
        print(f"  {k} {fmt(pts[k])}")


if __name__ == "__main__":
    main()
