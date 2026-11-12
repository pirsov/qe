# Практическая работа — модуль 2, вариант 10

Ответ по шаблону экзаменационного задания: эскиз, таблица точек, УП с коррекцией длины и диаметра, защита. Стойка — **Fanuc / ISO**.

## Ответ на задание

| Файл | Назначение |
|------|------------|
| [`cnc/praktika_var10.md`](cnc/praktika_var10.md) | Полный ответ по шаблону (п.1–4) |
| [`cnc/var10.nc`](cnc/var10.nc) | УП **O0010**: G43 + G41, фреза Ø16, Z−5 |
| [`cnc/contour.png`](cnc/contour.png) | Эскиз контура в XOY |
| [`cnc/duck.dxf`](cnc/duck.dxf) | Контур для КОМПАС-3D |
| [`cnc/coordinates.md`](cnc/coordinates.md) | Опорные точки и проверки |

В OFFSET: **H1** = длина инструмента, **D1 = 8.0** (радиус фрезы Ø16).

## Теория к аттестации

[`cnc/attestaciya_voprosy.md`](cnc/attestaciya_voprosy.md) — вопросы и ответы на 2–3 предложения.

## SwanSoft (дополнительно)

[`cnc/duck.nc`](cnc/duck.nc) — та же геометрия, уменьшена под ход ~280 мм в −X/−Y (фреза Ø8, D1=4.0).  
RESET → REF home → G54=0 → D01=4 → AUTO → CYCLE START.
