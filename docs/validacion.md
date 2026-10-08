# Contraste con temporadas pasadas

Reglas de la vigilancia aplicadas al archivo estándar de FIRMS (VIIRS S-NPP, NOAA-20 y MODIS) y comparadas con las áreas quemadas de EFFIS en España. Un incendio de EFFIS cuenta como detectado si su perímetro toca la huella de focos de un incendio del vigía (con 1 km de margen) y su fecha cae dentro de las del incendio (± 3 días). La máscara de fuentes fijas de cada año sale del otro año.

Las dos últimas columnas comparan con EFFIS la huella de píxeles y el perímetro estimado (solo en incendios con al menos 3 píxeles VIIRS). El IoU es superficie común entre superficie unida: 1 sería el mismo dibujo. Sale bajo cuando un incendio del vigía abarca varias áreas EFFIS, porque se compara con cada una por separado. Parámetros del perímetro (0.5 de radio, 0.75 km de cierre) elegidos con 2023; 2024 sirve de comprobación.

## 2023

19.339 focos tras los filtros; 4.162 incendios del vigía; 1.397 áreas EFFIS de cualquier tamaño.

| Tamaño (EFFIS) | Incendios EFFIS | Detectados | Retraso mediano | Vistos antes que la fecha EFFIS | Superficie / EFFIS: píxeles · perímetro | Coincidencia (IoU): píxeles · perímetro |
|---|---:|---:|---:|---:|---:|---:|
| 30–100 ha | 244 | 202 (83 %) | +1,0 h | 41 | 2,38 · 1,42 | 0,18 · 0,23 |
| 100–500 ha | 105 | 98 (93 %) | +1,2 h | 21 | 1,62 · 1,11 | 0,28 · 0,29 |
| ≥ 500 ha | 23 | 21 (91 %) | +2,0 h | 4 | 1,24 · 1,18 | 0,33 · 0,39 |

Incendios del vigía que coinciden con algún perímetro EFFIS, según su número de focos:

| Focos | Con perímetro EFFIS | Total |
|---:|---:|---:|
| ≥ 1 | 743 (18 %) | 4162 |
| ≥ 3 | 477 (48 %) | 992 |
| ≥ 10 | 187 (81 %) | 232 |
| ≥ 30 | 59 (91 %) | 65 |

## 2024

11.522 focos tras los filtros; 4.039 incendios del vigía; 769 áreas EFFIS de cualquier tamaño.

| Tamaño (EFFIS) | Incendios EFFIS | Detectados | Retraso mediano | Vistos antes que la fecha EFFIS | Superficie / EFFIS: píxeles · perímetro | Coincidencia (IoU): píxeles · perímetro |
|---|---:|---:|---:|---:|---:|---:|
| 30–100 ha | 135 | 103 (76 %) | +1,9 h | 16 | 2,02 · 1,12 | 0,20 · 0,24 |
| 100–500 ha | 63 | 48 (76 %) | +2,0 h | 9 | 1,05 · 0,74 | 0,27 · 0,23 |
| ≥ 500 ha | 20 | 20 (100 %) | +2,0 h | 3 | 0,62 · 0,49 | 0,32 · 0,34 |

Incendios del vigía que coinciden con algún perímetro EFFIS, según su número de focos:

| Focos | Con perímetro EFFIS | Total |
|---:|---:|---:|
| ≥ 1 | 490 (12 %) | 4039 |
| ≥ 3 | 290 (31 %) | 935 |
| ≥ 10 | 90 (59 %) | 153 |
| ≥ 30 | 27 (79 %) | 34 |
