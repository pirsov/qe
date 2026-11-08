%
O0001
(DUCK CONTOUR)
(SwanSoft Fanuc 0i-M)
(After HOME leave G54 = 0,0,0 — XY in -X -Y, Z only <=0)
(No Z+ moves: Z+ from HOME = Over travel on Z)
(RESET alarm, then AUTO / CYCLE START)
(Tool T1 D8mm  set D1=4.0 RADIUS)
(Depth Z-5.0  path X[-492..-8] Y[-480..-60])
(Lead-in/out R20 outside part at P2)
N010 G21 G17 G40 G49 G80 G90 G94
N020 G54
N030 T1 M06
N040 S1200 M03
N050 M08
N060 G00 X-297.823 Y-80.240        (lead-in XY, outside)
N070 G00 Z0.0                 (Z0 = HOME height, do not go +Z)
N080 G01 Z-5.0 F80        (plunge)
N090 G01 G41 D1 X-297.823 Y-120.240 F200  (G41 on LINE)
N100 G03 X-337.823 Y-120.240 I-20.000 J0.000    (LEAD-IN arc R20 onto contour)
N110 G01 X-337.823 Y-170.240            (P2-P3 head right)
N120 G03 X-306.067 Y-220.087 I55.000 J0.000    (P3-P4 R55 neck)
N130 G01 X-187.287 Y-275.475            (P4-P5 25deg breast)
N140 G03 X-128.663 Y-285.812 I48.601 J104.225    (P5-P6 R115 back)
N150 G01 X-7.823 Y-275.240            (P6-P7 5deg to tail)
N160 G01 X-72.073 Y-413.024            (P7-P8 lower tail)
N170 G02 X-177.204 Y-480.000 I-105.132 J49.024    (P8-P9 R116)
N180 G01 X-349.380 Y-480.000            (P9-P10 bottom)
N190 G02 X-492.177 Y-309.821 I0.000 J145.000    (P10-P11 R145 belly)
N200 G01 X-456.912 Y-109.821            (P11-P1 80deg left)
N210 G02 X-337.823 Y-120.240 I59.088 J-10.419    (P1-P2 R60 head)
N220 G03 X-317.823 Y-140.240 I20.000 J0.000    (LEAD-OUT arc R20 off contour)
N230 G01 X-282.823 Y-140.240            (clear of part, still G41)
N240 G40 G01 X-282.823 Y-100.240      (cancel G41 on LINE only)
N250 G00 Z0.0
N260 G00 X-262.823 Y-60.240            (park)
N270 M09
N280 M05
N290 M30
%
