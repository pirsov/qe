%
O0001
(DUCK CONTOUR)
(SwanSoft Fanuc 0i-M)
(After HOME leave G54 = 0,0,0)
(XY scaled to fit ~280mm travel in -X -Y from HOME)
(Z only <=0 — Z+ from HOME = Over travel)
(RESET alarm, then AUTO / CYCLE START)
(Tool T1 D8mm  set D1=4.0 RADIUS)
(Depth Z-5.0  path X[-252..-15] Y[-251..-15])
(Lead-in/out R9.8 outside part at P2)
N010 G21 G17 G40 G49 G80 G90 G94
N020 G54
N030 T1 M06
N040 S1200 M03
N050 M08
N060 G00 X-157.200 Y-35.000        (lead-in XY, outside)
N070 G00 Z0.0                 (Z0 = HOME height, do not go +Z)
N080 G01 Z-5.0 F80        (plunge)
N090 G01 G41 D1 X-157.200 Y-75.000 F200  (G41 on LINE)
N100 G03 X-176.814 Y-75.000 I-9.807 J0.000    (LEAD-IN arc R10 onto contour)
N110 G01 X-176.814 Y-99.517            (P2-P3 head right)
N120 G03 X-161.242 Y-123.959 I26.969 J0.000    (P3-P4 R55 neck)
N130 G01 X-102.999 Y-151.119            (P4-P5 25deg breast)
N140 G03 X-74.253 Y-156.187 I23.831 J51.106    (P5-P6 R115 back)
N150 G01 X-15.000 Y-151.003            (P6-P7 5deg to tail)
N160 G01 X-46.504 Y-218.565            (P7-P8 lower tail)
N170 G02 X-98.055 Y-251.406 I-51.551 J24.038    (P8-P9 R116)
N180 G01 X-182.480 Y-251.406            (P9-P10 bottom)
N190 G02 X-252.500 Y-167.960 I0.000 J71.100    (P10-P11 R145 belly)
N200 G01 X-235.208 Y-69.891            (P11-P1 80deg left)
N210 G02 X-176.814 Y-75.000 I28.974 J-5.109    (P1-P2 R60 head)
N220 G03 X-167.007 Y-84.807 I9.807 J0.000    (LEAD-OUT arc R10 off contour)
N230 G01 X-121.814 Y-84.807            (clear of part, still G41)
N240 G40 G01 X-121.814 Y-44.807      (cancel G41 on LINE only)
N250 G00 Z0.0
N260 G00 X-101.814 Y-15.000            (park)
N270 M09
N280 M05
N290 M30
%
