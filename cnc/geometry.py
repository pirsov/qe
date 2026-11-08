#!/usr/bin/env python3
"""Closed duck contour from the mill drawing.

Coordinate system (as on the drawing):
  X = 0  — vertical dashed axis
  Y = 0  — lower dashed line of dimension 150
  Y up, X right, millimetres

Construction:
  R60 centre at (-85, 200); right side of the head is vertical X = -25
  200 — vertical span of the 80° left side (R60 tangent → R145 tangent)
  150 — Y of R55 / head-right junction
  305 — tail X
  5°  — back line, rising to the right
  25° — breast line, falling to the right
  80° — left side from the horizontal
  120° on the drawing is the exterior angle at the tail;
        interior is 60°, so the lower tail line is at 65° to +X
"""
from __future__ import annotations

import math
from dataclasses import dataclass

DEG = math.pi / 180.0


def d2r(a: float) -> float:
    return a * DEG


def pol(r: float, ang_deg: float) -> tuple[float, float]:
    a = d2r(ang_deg)
    return (r * math.cos(a), r * math.sin(a))


def add(p, q):
    return (p[0] + q[0], p[1] + q[1])


def sub(p, q):
    return (p[0] - q[0], p[1] - q[1])


def mul(p, s):
    return (p[0] * s, p[1] * s)


def hypot(p):
    return math.hypot(p[0], p[1])


def rot90(p, ccw=True):
    return (-p[1], p[0]) if ccw else (p[1], -p[0])


def ang(p):
    return math.degrees(math.atan2(p[1], p[0]))


def line_offset_point(pt, direction_deg, dist, side="left"):
    d = pol(1.0, direction_deg)
    n = rot90(d, ccw=True)
    if side == "right":
        n = mul(n, -1)
    return add(pt, mul(n, dist))


def project_to_line(c, pt, direction_deg):
    d = pol(1.0, direction_deg)
    n = rot90(d, ccw=True)
    w = sub(c, pt)
    t = w[0] * d[0] + w[1] * d[1]
    off = w[0] * n[0] + w[1] * n[1]
    foot = add(pt, mul(d, t))
    return foot, off, t


def fillet_two_lines(p_a, dir_a, p_b, dir_b, radius, side_a="left", side_b="left"):
    import numpy as np

    ca = line_offset_point(p_a, dir_a, radius, side_a)
    cb = line_offset_point(p_b, dir_b, radius, side_b)
    da = pol(1.0, dir_a)
    db = pol(1.0, dir_b)
    A = np.array([[da[0], -db[0]], [da[1], -db[1]]], float)
    rhs = np.array([cb[0] - ca[0], cb[1] - ca[1]], float)
    ts = np.linalg.solve(A, rhs)
    center = add(ca, mul(da, float(ts[0])))
    ta, _, _ = project_to_line(center, p_a, dir_a)
    tb, _, _ = project_to_line(center, p_b, dir_b)
    return center, ta, tb


# Drawing parameters
YC60 = 200.0
Y_TAIL = 45.0
P3Y = 150.0
LOWER_ANG = 65.0  # 120° exterior at tail, 5° back → 65°
UPPER_ANG = 5.0
BREAST_ANG = -25.0


@dataclass
class Seg:
    kind: str  # 'line' | 'arc'
    p0: tuple[float, float]
    p1: tuple[float, float]
    center: tuple[float, float] | None = None
    r: float | None = None
    g: str | None = None  # 'G02' | 'G03' for clockwise part traversal
    name: str = ""


def build(
    yc60: float = YC60,
    y_tail: float = Y_TAIL,
    p3y: float = P3Y,
    lower_ang: float = LOWER_ANG,
    upper_ang: float = UPPER_ANG,
    breast_ang: float = BREAST_ANG,
):
    s80 = math.sin(d2r(80.0))
    c80 = math.cos(d2r(80.0))

    C60 = (-85.0, yc60)
    n_in = (s80, -c80)
    n_out = (-s80, c80)
    P1 = add(C60, mul(n_out, 60.0))
    P2 = (-25.0, yc60)

    d80 = (-c80, -s80)
    L80 = 200.0 / s80
    P11 = add(P1, mul(d80, L80))
    C145 = add(P11, mul(n_in, 145.0))
    P10 = (C145[0], C145[1] - 145.0)
    y_bottom = P10[1]

    P3 = (-25.0, p3y)
    C55 = (P3[0] + 55.0, P3[1])
    bx, by = pol(1.0, breast_ang)
    th4 = math.degrees(math.atan2(-bx, by))
    P4 = add(C55, pol(55.0, th4))

    P7 = (305.0, y_tail)
    C115, P5, P6 = fillet_two_lines(
        P4, breast_ang, P7, upper_ang, 115.0, side_a="left", side_b="left"
    )

    C116_y = y_bottom + 116.0
    off_pt = line_offset_point(P7, lower_ang, 116.0, side="left")
    cl, sl = pol(1.0, lower_ang)
    t = (C116_y - off_pt[1]) / sl
    C116 = add(off_pt, mul((cl, sl), t))
    P9 = (C116[0], y_bottom)
    P8, _, _ = project_to_line(C116, P7, lower_ang)

    pts = {
        "C60": C60,
        "P1": P1,
        "P2": P2,
        "P3": P3,
        "C55": C55,
        "P4": P4,
        "P5": P5,
        "C115": C115,
        "P6": P6,
        "P7": P7,
        "P8": P8,
        "C116": C116,
        "P9": P9,
        "P10": P10,
        "C145": C145,
        "P11": P11,
    }

    # Clockwise around the part (G41 = outside).
    segs = [
        Seg("line", P2, P3, name="head_right"),
        Seg("arc", P3, P4, C55, 55.0, "G03", "R55"),
        Seg("line", P4, P5, name="25deg"),
        Seg("arc", P5, P6, C115, 115.0, "G03", "R115"),
        Seg("line", P6, P7, name="5deg"),
        Seg("line", P7, P8, name="lower_tail"),
        Seg("arc", P8, P9, C116, 116.0, "G02", "R116"),
        Seg("line", P9, P10, name="bottom"),
        Seg("arc", P10, P11, C145, 145.0, "G02", "R145"),
        Seg("line", P11, P1, name="80deg"),
        Seg("arc", P1, P2, C60, 60.0, "G02", "R60"),
    ]
    return segs, pts


def fmt(p, n=3):
    return (round(p[0], n), round(p[1], n))


if __name__ == "__main__":
    segs, pts = build()
    assert abs(pts["P1"][1] - pts["P11"][1] - 200) < 1e-9
    assert abs(pts["P7"][0] - 305) < 1e-9
    assert abs(pts["P3"][1] - 150) < 1e-9
    assert abs(pts["C60"][0] + 85) < 1e-9
    for name, r, a, b in [
        ("C60", 60, "P1", "P2"),
        ("C55", 55, "P3", "P4"),
        ("C115", 115, "P5", "P6"),
        ("C116", 116, "P8", "P9"),
        ("C145", 145, "P10", "P11"),
    ]:
        for p in (a, b):
            d = hypot(sub(pts[p], pts[name]))
            assert abs(d - r) < 1e-6, (name, p, d, r)
    assert hypot(sub(segs[-1].p1, segs[0].p0)) < 1e-9
    print("geometry ok", {k: fmt(pts[k]) for k in ("P2", "P7", "P10")})
