%
O0001
(DUCK CONTOUR)
(SwanSoft Fanuc 0i-M)
(After HOME leave G54 = 0,0,0 — path is in -X -Y from home)
(RESET alarm, then AUTO / CYCLE START)
(Tool T1 D8mm  set D1=4.0 RADIUS)
(Depth Z-5.0  path X[-492..-8] Y[-480..-60])
(Lead-in/out R20 outside part at P2)
N010 G21 G17 G40 G49 G80 G90 G94
N020 G54
N030 T1 M06
N040 S1200 M03
N050 M08
N060 G00 X-297.823 Y-80.240        (above lead-in, outside)
N070 G00 Z20.0
N080 G00 Z5.0
N090 G01 Z-5.0 F80        (plunge outside part)
N100 G01 G41 D1 X-297.823 Y-120.240 F200  (G41 on LINE)
N110 G03 X-337.823 Y-120.240 I-20.000 J0.000    (LEAD-IN arc R20 onto contour)
N120 G01 X-337.823 Y-170.240            (P2-P3 head right)
N130 G03 X-306.067 Y-220.087 I55.000 J0.000    (P3-P4 R55 neck)
N140 G01 X-187.287 Y-275.475            (P4-P5 25deg breast)
N150 G03 X-128.663 Y-285.812 I48.601 J104.225    (P5-P6 R115 back)
N160 G01 X-7.823 Y-275.240            (P6-P7 5deg to tail)
N170 G01 X-72.073 Y-413.024            (P7-P8 lower tail)
N180 G02 X-177.204 Y-480.000 I-105.132 J49.024    (P8-P9 R116)
N190 G01 X-349.380 Y-480.000            (P9-P10 bottom)
N200 G02 X-492.177 Y-309.821 I0.000 J145.000    (P10-P11 R145 belly)
N210 G01 X-456.912 Y-109.821            (P11-P1 80deg left)
N220 G02 X-337.823 Y-120.240 I59.088 J-10.419    (P1-P2 R60 head)
N230 G03 X-317.823 Y-140.240 I20.000 J0.000    (LEAD-OUT arc R20 off contour)
N240 G01 X-282.823 Y-140.240            (clear of part, still G41)
N250 G40 G01 X-282.823 Y-100.240      (cancel G41 on LINE only)
N260 G00 Z20.0
N270 G00 X-262.823 Y-60.240            (park)
N280 M09
N290 M05
N300 M30
%
