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
# After HOME, Fanuc Z0 is at the top stroke. G00 Z+… → Over travel on Z.
# With G54 Z=0 left at HOME use only Z≤0. (If you set G54 Z on blank top, Z+20 is OK.)
SAFE_Z = 0.0
RAPID_Z = 0.0
CUT_Z = -5.0
FEED_XY = 200.0
FEED_Z = 80.0
SPINDLE = 1200

# SwanSoft Fanuc: after REF/HOME the machine sits at the POSITIVE stroke end.
# Work must be in -X/-Y. Training mills often allow only ~300 mm into -X/-Y
# (Y-413 already caused Over travel) — scale the path to fit TRAVEL.
TRAVEL = 280.0
MARGIN = 15.0


def ij(start, center):
    return center[0] - start[0], center[1] - start[1]


def xyz(x, y, n=3):
    return f"X{x:.{n}f} Y{y:.{n}f}"


def shift_pt(p, dx, dy):
    return (p[0] + dx, p[1] + dy)


def scale_pt(p, s):
    return (p[0] * s, p[1] * s)


def apply_shift_pts(pts, dx, dy):
    return {k: shift_pt(v, dx, dy) for k, v in pts.items()}


def apply_shift_lead(lead, dx, dy):
    out = dict(lead)
    for key in ("P2", "c_in", "start_in", "rapid_in", "c_out", "end_out", "away", "cancel", "park"):
        out[key] = shift_pt(lead[key], dx, dy)
    return out


def apply_shift_segs(segs, dx, dy):
    from geometry import Seg

    out = []
    for s in segs:
        if s.kind == "line":
            out.append(
                Seg("line", shift_pt(s.p0, dx, dy), shift_pt(s.p1, dx, dy), name=s.name)
            )
        else:
            out.append(
                Seg(
                    "arc",
                    shift_pt(s.p0, dx, dy),
                    shift_pt(s.p1, dx, dy),
                    shift_pt(s.center, dx, dy),
                    s.r,
                    s.g,
                    s.name,
                )
            )
    return out


def apply_scale_pts(pts, s):
    return {k: scale_pt(v, s) for k, v in pts.items()}


def apply_scale_segs(segs, s):
    from geometry import Seg

    out = []
    for seg in segs:
        if seg.kind == "line":
            out.append(
                Seg("line", scale_pt(seg.p0, s), scale_pt(seg.p1, s), name=seg.name)
            )
        else:
            out.append(
                Seg(
                    "arc",
                    scale_pt(seg.p0, s),
                    scale_pt(seg.p1, s),
                    scale_pt(seg.center, s),
                    seg.r * s,
                    seg.g,
                    seg.name,
                )
            )
    return out


def path_bounds(pts, lead: dict):
    xs = [p[0] for k, p in pts.items() if k.startswith("P")]
    ys = [p[1] for k, p in pts.items() if k.startswith("P")]
    for key in ("rapid_in", "start_in", "end_out", "away", "cancel", "park", "P2"):
        xs.append(lead[key][0])
        ys.append(lead[key][1])
    return min(xs), max(xs), min(ys), max(ys)


def lead_geometry(pts, r_lead: float = 20.0):
    """Tangential circular lead-in / lead-out off the part at P2.

    Contour starts at P2 going down (0,-1). Outside is +X.
    Lead-in:  G03 90° from the right onto P2 (arrive going down).
    Lead-out: G03 90° from P2 downward-out, then linear away; G40 on G01 only.
    """
    P2 = pts["P2"]
    r = r_lead
    c_in = (P2[0] + r, P2[1])          # (-5, 200) for r=20
    start_in = (c_in[0] + r, c_in[1])   # (15, 200) — east of center
    rapid_in = (start_in[0], start_in[1] + 40.0)  # (15, 240)

    # Lead-out center same side; from P2 CCW 90° → below center
    c_out = c_in
    end_out = (c_out[0], c_out[1] - r)  # (-5, 180)
    away = (P2[0] + 55.0, end_out[1])   # clear of part
    cancel = (away[0], away[1] + 40.0)
    park = (P2[0] + 75.0, P2[1] + 60.0)  # relative to P2 (survives work shift)
    return {
        "P2": P2,
        "r": r,
        "c_in": c_in,
        "start_in": start_in,
        "rapid_in": rapid_in,
        "c_out": c_out,
        "end_out": end_out,
        "away": away,
        "cancel": cancel,
        "park": park,
    }


def write_gcode(segs, pts, path: Path, lead: dict | None = None):
    L = lead if lead is not None else lead_geometry(pts)
    P2, r = L["P2"], L["r"]

    xs = [p[0] for k, p in pts.items() if k.startswith("P")]
    ys = [p[1] for k, p in pts.items() if k.startswith("P")]
    for key in ("rapid_in", "start_in", "end_out", "away", "cancel", "park"):
        xs.append(L[key][0])
        ys.append(L[key][1])
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)

    n = [0]

    def nxt():
        n[0] += 10
        return f"N{n[0]:03d}"

    lines = []
    a = lines.append
    a("%")
    a("O0001")
    a("(DUCK CONTOUR)")
    a("(SwanSoft Fanuc 0i-M)")
    a("(After HOME leave G54 = 0,0,0)")
    a("(XY scaled to fit ~280mm travel in -X -Y from HOME)")
    a("(Z only <=0 — Z+ from HOME = Over travel)")
    a("(RESET alarm, then AUTO / CYCLE START)")
    a(f"(Tool T1 D{TOOL_DIA:.0f}mm  set D1={TOOL_RAD:.1f} RADIUS)")
    a(f"(Depth Z{CUT_Z:.1f}  path X[{xmin:.0f}..{xmax:.0f}] Y[{ymin:.0f}..{ymax:.0f}])")
    a(f"(Lead-in/out R{r:.1f} outside part at P2)")
    a(f"{nxt()} G21 G17 G40 G49 G80 G90 G94")
    a(f"{nxt()} G54")
    a(f"{nxt()} T1 M06")
    a(f"{nxt()} S{SPINDLE:.0f} M03")
    a(f"{nxt()} M08")

    # --- ZAHOD (approach from outside the part) ---
    a(f"{nxt()} G00 {xyz(*L['rapid_in'])}        (lead-in XY, outside)")
    a(f"{nxt()} G00 Z{SAFE_Z:.1f}                 (Z0 = HOME height, do not go +Z)")
    a(f"{nxt()} G01 Z{CUT_Z:.1f} F{FEED_Z:.0f}        (plunge)")
    a(f"{nxt()} G01 G41 D1 {xyz(*L['start_in'])} F{FEED_XY:.0f}  (G41 on LINE)")
    i_in, j_in = ij(L["start_in"], L["c_in"])
    a(
        f"{nxt()} G03 {xyz(*P2)} I{i_in:.3f} J{j_in:.3f}    "
        f"(LEAD-IN arc R{r:.0f} onto contour)"
    )

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

    # --- VYHOD (leave the part, G40 only on LINE — SwanSoft rule) ---
    i_out, j_out = ij(P2, L["c_out"])
    a(
        f"{nxt()} G03 {xyz(*L['end_out'])} I{i_out:.3f} J{j_out:.3f}    "
        f"(LEAD-OUT arc R{r:.0f} off contour)"
    )
    a(f"{nxt()} G01 {xyz(*L['away'])}            (clear of part, still G41)")
    a(f"{nxt()} G40 G01 {xyz(*L['cancel'])}      (cancel G41 on LINE only)")
    a(f"{nxt()} G00 Z{SAFE_Z:.1f}")
    a(f"{nxt()} G00 {xyz(*L['park'])}            (park)")
    a(f"{nxt()} M09")
    a(f"{nxt()} M05")
    a(f"{nxt()} M30")
    a("%")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path, L


def _arc_angles(center, p0, p1, g: str):
    """DXF ARC is always CCW from start_angle to end_angle (degrees)."""
    a0 = math.degrees(math.atan2(p0[1] - center[1], p0[0] - center[0]))
    a1 = math.degrees(math.atan2(p1[1] - center[1], p1[0] - center[0]))
    if g == "G02":  # CW path A→B = same curve as CCW B→A
        return a1, a0
    return a0, a1


def write_dxf(segs, pts, lead: dict, path: Path):
    """AutoCAD R12 DXF — open in KOMPAS-3D and Save As .cdw."""
    ents = []

    def pair(code, value):
        ents.append(f"{code}\n{value}")

    def add_line(layer, p0, p1):
        pair(0, "LINE")
        pair(8, layer)
        pair(10, f"{p0[0]:.6f}")
        pair(20, f"{p0[1]:.6f}")
        pair(30, "0.0")
        pair(11, f"{p1[0]:.6f}")
        pair(21, f"{p1[1]:.6f}")
        pair(31, "0.0")

    def add_arc(layer, center, p0, p1, g, r):
        a0, a1 = _arc_angles(center, p0, p1, g)
        pair(0, "ARC")
        pair(8, layer)
        pair(10, f"{center[0]:.6f}")
        pair(20, f"{center[1]:.6f}")
        pair(30, "0.0")
        pair(40, f"{r:.6f}")
        pair(50, f"{a0:.6f}")
        pair(51, f"{a1:.6f}")

    for s in segs:
        if s.kind == "line":
            add_line("KONTUR", s.p0, s.p1)
        else:
            add_arc("KONTUR", s.center, s.p0, s.p1, s.g, s.r)

    # Lead-in / lead-out off the part
    add_line("ZAHOD", lead["rapid_in"], lead["start_in"])
    add_arc("ZAHOD", lead["c_in"], lead["start_in"], lead["P2"], "G03", lead["r"])
    add_arc("VYHOD", lead["c_out"], lead["P2"], lead["end_out"], "G03", lead["r"])
    add_line("VYHOD", lead["end_out"], lead["away"])
    add_line("VYHOD", lead["away"], lead["cancel"])

    for x0, y0, x1, y1 in [(-200, 0, 320, 0), (0, -180, 0, 230)]:
        add_line("OSI", (x0, y0), (x1, y1))

    for name in ["P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8", "P9", "P10", "P11"]:
        p = pts[name]
        pair(0, "POINT")
        pair(8, "TOCHKI")
        pair(10, f"{p[0]:.6f}")
        pair(20, f"{p[1]:.6f}")
        pair(30, "0.0")

    body = "\n".join(ents)
    dxf = f"""0
SECTION
2
HEADER
9
$INSUNITS
70
4
9
$MEASUREMENT
70
1
0
ENDSEC
0
SECTION
2
TABLES
0
TABLE
2
LAYER
70
5
0
LAYER
2
KONTUR
70
0
62
7
6
CONTINUOUS
0
LAYER
2
ZAHOD
70
0
62
3
6
CONTINUOUS
0
LAYER
2
VYHOD
70
0
62
1
6
CONTINUOUS
0
LAYER
2
OSI
70
0
62
8
6
DASHDOT
0
LAYER
2
TOCHKI
70
0
62
1
6
CONTINUOUS
0
ENDTAB
0
ENDSEC
0
SECTION
2
ENTITIES
{body}
0
ENDSEC
0
EOF
"""
    path.write_text(dxf, encoding="utf-8")
    return path


def write_preview(segs, pts, lead: dict, path: Path):
    """Contour + lead-in/out without cutter comp — for NC viewers."""
    lines = ["%", "O0002", "(DUCK CONTOUR PREVIEW, no G41)"]
    n = [0]

    def nxt():
        n[0] += 10
        return f"N{n[0]:03d}"

    a = lines.append
    a(f"{nxt()} G21 G17 G40 G90")
    a(f"{nxt()} G00 {xyz(*lead['rapid_in'])}")
    a(f"{nxt()} G00 Z{RAPID_Z:.1f}")
    a(f"{nxt()} G01 Z{CUT_Z:.1f} F{FEED_Z:.0f}")
    a(f"{nxt()} G01 {xyz(*lead['start_in'])} F{FEED_XY:.0f}")
    i_in, j_in = ij(lead["start_in"], lead["c_in"])
    a(f"{nxt()} G03 {xyz(*lead['P2'])} I{i_in:.3f} J{j_in:.3f}")
    for s in segs:
        if s.kind == "line":
            a(f"{nxt()} G01 {xyz(*s.p1)}")
        else:
            i, j = ij(s.p0, s.center)
            a(f"{nxt()} {s.g} {xyz(*s.p1)} I{i:.3f} J{j:.3f}")
    i_out, j_out = ij(lead["P2"], lead["c_out"])
    a(f"{nxt()} G03 {xyz(*lead['end_out'])} I{i_out:.3f} J{j_out:.3f}")
    a(f"{nxt()} G01 {xyz(*lead['away'])}")
    a(f"{nxt()} G01 {xyz(*lead['cancel'])}")
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


def plot_contour(segs, pts, lead: dict, path: Path):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
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

    for s in segs:
        if s.kind == "line":
            ax.plot([s.p0[0], s.p1[0]], [s.p0[1], s.p1[1]], color="#1a1a1a", lw=2.2)
        else:
            x, y = arc_xy(s.center, s.p0, s.p1, s.r, s.g)
            ax.plot(x, y, color="#1a1a1a", lw=2.2)

    # Lead-in (green)
    ax.plot(
        [lead["rapid_in"][0], lead["start_in"][0]],
        [lead["rapid_in"][1], lead["start_in"][1]],
        color="#2a9d4a",
        lw=1.8,
        ls="--",
        label="заход",
    )
    x, y = arc_xy(lead["c_in"], lead["start_in"], lead["P2"], lead["r"], "G03")
    ax.plot(x, y, color="#2a9d4a", lw=2.0, ls="--")
    ax.annotate("заход", lead["start_in"], textcoords="offset points", xytext=(8, 8), color="#2a9d4a", fontsize=8)

    # Lead-out (orange)
    x, y = arc_xy(lead["c_out"], lead["P2"], lead["end_out"], lead["r"], "G03")
    ax.plot(x, y, color="#e67e22", lw=2.0, ls="--", label="выход")
    ax.plot(
        [lead["end_out"][0], lead["away"][0], lead["cancel"][0]],
        [lead["end_out"][1], lead["away"][1], lead["cancel"][1]],
        color="#e67e22",
        lw=1.8,
        ls="--",
    )
    ax.annotate("выход", lead["away"], textcoords="offset points", xytext=(6, -12), color="#e67e22", fontsize=8)

    for name in ["P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8", "P9", "P10", "P11"]:
        p = pts[name]
        ax.scatter(*p, c="#c0392b", s=18, zorder=6)
        ax.annotate(name, p, textcoords="offset points", xytext=(4, 4), fontsize=7, color="#7b1e16")

    ax.axhline(0, color="#4c7bd9", lw=0.8, ls=":", alpha=0.8)
    ax.axvline(0, color="#4c7bd9", lw=0.8, ls=":", alpha=0.8)
    ax.set_xlabel("X, мм")
    ax.set_ylabel("Y, мм")
    ax.set_title("Контур: заход / обход по часовой / выход (G41 снаружи)")
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
    segs0, pts0 = build()
    lead0 = lead_geometry(pts0)
    # Drawing-space artifacts (match the paper drawing / KOMPAS)
    write_dxf(segs0, pts0, lead0, ROOT / "duck.dxf")
    write_table(pts0, segs0, ROOT / "coordinates.md")
    plot_contour(segs0, pts0, lead0, ROOT / "contour.png")
    overlay_drawing(segs0, pts0, ROOT / "overlay_on_drawing.png")

    # Machine-space NC for SwanSoft Fanuc (small travel ~280 mm into -X/-Y):
    # scale drawing → rebuild lead → shift so path ∈ [-TRAVEL+MARGIN, -MARGIN].
    xmin0, xmax0, ymin0, ymax0 = path_bounds(pts0, lead0)
    span0 = max(xmax0 - xmin0, ymax0 - ymin0)
    usable = TRAVEL - 2 * MARGIN
    scale = 0.95 * usable / span0
    r_lead = max(8.0, 20.0 * scale)
    pts = apply_scale_pts(pts0, scale)
    segs = apply_scale_segs(segs0, scale)
    lead = lead_geometry(pts, r_lead=r_lead)
    xmin, xmax, ymin, ymax = path_bounds(pts, lead)
    dx = -MARGIN - xmax
    dy = -MARGIN - ymax
    pts = apply_shift_pts(pts, dx, dy)
    segs = apply_shift_segs(segs, dx, dy)
    lead = apply_shift_lead(lead, dx, dy)
    nc, lead = write_gcode(segs, pts, ROOT / "duck.nc", lead=lead)
    write_preview(segs, pts, lead, ROOT / "duck_preview.nc")
    simulate_gcode(nc, ROOT / "toolpath_from_nc.png")

    # Sync browser viewer with shifted NC moves (no G41 words needed)
    _write_viewer_nc(ROOT / "viewer.html", lead, segs)

    print("wrote", nc)
    print(
        f"SwanSoft fit: scale={scale:.4f} r_lead={r_lead:.2f} "
        f"shift=({dx:.2f},{dy:.2f}) travel={TRAVEL:.0f}"
    )
    print(
        "lead-in",
        fmt(lead["start_in"]),
        "→",
        fmt(lead["P2"]),
        " lead-out",
        fmt(lead["P2"]),
        "→",
        fmt(lead["end_out"]),
    )
    xs = [p[0] for k, p in pts.items() if k.startswith("P")]
    ys = [p[1] for k, p in pts.items() if k.startswith("P")]
    print(f"NC bbox X[{min(xs):.1f}..{max(xs):.1f}] Y[{min(ys):.1f}..{max(ys):.1f}]")
    for k in ["P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8", "P9", "P10", "P11"]:
        print(f"  {k} {fmt(pts[k])}")


def _write_viewer_nc(path: Path, lead: dict, segs):
    """Refresh the hardcoded path inside viewer.html."""
    text = path.read_text(encoding="utf-8")
    start = text.index("const NC = `") + len("const NC = `")
    end = text.index("`;", start)
    lines = [
        f"G00 {xyz(*lead['rapid_in'])}",
        f"G01 {xyz(*lead['start_in'])}",
        f"G03 {xyz(*lead['P2'])} I{ij(lead['start_in'], lead['c_in'])[0]:.3f} J{ij(lead['start_in'], lead['c_in'])[1]:.3f}",
    ]
    for s in segs:
        if s.kind == "line":
            lines.append(f"G01 {xyz(*s.p1)}")
        else:
            i, j = ij(s.p0, s.center)
            lines.append(f"{s.g} {xyz(*s.p1)} I{i:.3f} J{j:.3f}")
    i, j = ij(lead["P2"], lead["c_out"])
    lines += [
        f"G03 {xyz(*lead['end_out'])} I{i:.3f} J{j:.3f}",
        f"G01 {xyz(*lead['away'])}",
        f"G01 {xyz(*lead['cancel'])}",
        f"G00 {xyz(*lead['park'])}",
    ]
    path.write_text(text[:start] + "\n" + "\n".join(lines) + "\n" + text[end:], encoding="utf-8")


if __name__ == "__main__":
    main()
