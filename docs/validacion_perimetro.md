# Superficie quemada con Sentinel-2 frente a EFFIS

Muestra de 141 incendios de 2023 y 2024 con perímetro EFFIS, estratificada por tamaño y año. 141 con imagen de antes y de después; 0 sin imagen útil y 0 con error de lectura.

IoU: superficie común entre el perímetro calculado y el de EFFIS dividida por la superficie de los dos juntos (1 es coincidencia exacta). Razón: hectáreas calculadas entre hectáreas de EFFIS.

En negrita, la combinación que usa el vigía (`DNBR_UMBRAL` y `PERIMETRO_ANCLA_M` en [config.py](../vigia/config.py)).

«Después del fuego» es cómo se resume cada píxel con las imágenes posteriores. El NBR mínimo y el segundo más bajo quedan casi iguales en esta muestra, que es de verano y con cielos limpios. El vigía usa el segundo más bajo porque fuera del verano una sombra de nube o una bruma que la máscara no detecta en una sola imagen basta para que el mínimo la cuente como quemada: en Campoo de Suso (octubre de 2026) daba 123 ha donde EFFIS cartografió 13. Exigir que lo vean dos imágenes cuesta un poco en los incendios grandes, que salen algo más cortos.

## Todos (141 incendios)

| Después del fuego | Umbral dNBR | Anclaje a los focos | IoU mediano | IoU ≥ 0,5 | Razón de superficie (mediana) |
|---|---:|---:|---:|---:|---:|
| 2.º NBR más bajo | 0,10 | 750 m | 0,62 | 64 % | 0,98 |
| 2.º NBR más bajo | 0,10 | 1.500 m | 0,66 | 69 % | 1,01 |
| 2.º NBR más bajo | 0,10 | 3.000 m | 0,72 | 69 % | 1,03 |
| 2.º NBR más bajo | 0,15 | 750 m | 0,66 | 65 % | 0,88 |
| 2.º NBR más bajo | 0,15 | 1.500 m | 0,71 | 70 % | 0,93 |
| **2.º NBR más bajo** | **0,15** | **3.000 m** | **0,74** | **72 %** | **0,94** |
| 2.º NBR más bajo | 0,20 | 750 m | 0,66 | 65 % | 0,80 |
| 2.º NBR más bajo | 0,20 | 1.500 m | 0,70 | 70 % | 0,84 |
| 2.º NBR más bajo | 0,20 | 3.000 m | 0,75 | 71 % | 0,88 |
| 2.º NBR más bajo | 0,27 | 750 m | 0,59 | 62 % | 0,68 |
| 2.º NBR más bajo | 0,27 | 1.500 m | 0,64 | 67 % | 0,69 |
| 2.º NBR más bajo | 0,27 | 3.000 m | 0,66 | 67 % | 0,72 |
| NBR mínimo | 0,10 | 750 m | 0,59 | 62 % | 1,05 |
| NBR mínimo | 0,10 | 1.500 m | 0,64 | 65 % | 1,09 |
| NBR mínimo | 0,10 | 3.000 m | 0,66 | 65 % | 1,09 |
| NBR mínimo | 0,15 | 750 m | 0,67 | 67 % | 0,96 |
| NBR mínimo | 0,15 | 1.500 m | 0,71 | 72 % | 0,98 |
| NBR mínimo | 0,15 | 3.000 m | 0,73 | 72 % | 1,00 |
| NBR mínimo | 0,20 | 750 m | 0,68 | 70 % | 0,87 |
| NBR mínimo | 0,20 | 1.500 m | 0,74 | 73 % | 0,92 |
| NBR mínimo | 0,20 | 3.000 m | 0,75 | 75 % | 0,93 |
| NBR mínimo | 0,27 | 750 m | 0,63 | 67 % | 0,73 |
| NBR mínimo | 0,27 | 1.500 m | 0,67 | 71 % | 0,79 |
| NBR mínimo | 0,27 | 3.000 m | 0,70 | 73 % | 0,82 |

## 30–100 ha (50 incendios)

| Después del fuego | Umbral dNBR | Anclaje a los focos | IoU mediano | IoU ≥ 0,5 | Razón de superficie (mediana) |
|---|---:|---:|---:|---:|---:|
| 2.º NBR más bajo | 0,10 | 750 m | 0,66 | 66 % | 1,15 |
| 2.º NBR más bajo | 0,10 | 1.500 m | 0,65 | 66 % | 1,15 |
| 2.º NBR más bajo | 0,10 | 3.000 m | 0,65 | 64 % | 1,15 |
| 2.º NBR más bajo | 0,15 | 750 m | 0,69 | 66 % | 1,02 |
| 2.º NBR más bajo | 0,15 | 1.500 m | 0,70 | 66 % | 1,02 |
| **2.º NBR más bajo** | **0,15** | **3.000 m** | **0,70** | **66 %** | **1,02** |
| 2.º NBR más bajo | 0,20 | 750 m | 0,70 | 66 % | 0,94 |
| 2.º NBR más bajo | 0,20 | 1.500 m | 0,70 | 66 % | 0,94 |
| 2.º NBR más bajo | 0,20 | 3.000 m | 0,70 | 66 % | 0,94 |
| 2.º NBR más bajo | 0,27 | 750 m | 0,68 | 66 % | 0,84 |
| 2.º NBR más bajo | 0,27 | 1.500 m | 0,69 | 66 % | 0,84 |
| 2.º NBR más bajo | 0,27 | 3.000 m | 0,69 | 66 % | 0,84 |
| NBR mínimo | 0,10 | 750 m | 0,59 | 60 % | 1,24 |
| NBR mínimo | 0,10 | 1.500 m | 0,58 | 58 % | 1,28 |
| NBR mínimo | 0,10 | 3.000 m | 0,58 | 56 % | 1,29 |
| NBR mínimo | 0,15 | 750 m | 0,68 | 64 % | 1,10 |
| NBR mínimo | 0,15 | 1.500 m | 0,68 | 62 % | 1,10 |
| NBR mínimo | 0,15 | 3.000 m | 0,68 | 62 % | 1,10 |
| NBR mínimo | 0,20 | 750 m | 0,71 | 68 % | 1,02 |
| NBR mínimo | 0,20 | 1.500 m | 0,71 | 66 % | 1,02 |
| NBR mínimo | 0,20 | 3.000 m | 0,71 | 66 % | 1,02 |
| NBR mínimo | 0,27 | 750 m | 0,71 | 68 % | 0,91 |
| NBR mínimo | 0,27 | 1.500 m | 0,71 | 66 % | 0,92 |
| NBR mínimo | 0,27 | 3.000 m | 0,71 | 66 % | 0,92 |

## 100–500 ha (50 incendios)

| Después del fuego | Umbral dNBR | Anclaje a los focos | IoU mediano | IoU ≥ 0,5 | Razón de superficie (mediana) |
|---|---:|---:|---:|---:|---:|
| 2.º NBR más bajo | 0,10 | 750 m | 0,62 | 64 % | 0,95 |
| 2.º NBR más bajo | 0,10 | 1.500 m | 0,70 | 66 % | 1,03 |
| 2.º NBR más bajo | 0,10 | 3.000 m | 0,74 | 66 % | 1,04 |
| 2.º NBR más bajo | 0,15 | 750 m | 0,67 | 68 % | 0,86 |
| 2.º NBR más bajo | 0,15 | 1.500 m | 0,73 | 74 % | 0,92 |
| **2.º NBR más bajo** | **0,15** | **3.000 m** | **0,74** | **78 %** | **0,95** |
| 2.º NBR más bajo | 0,20 | 750 m | 0,65 | 68 % | 0,77 |
| 2.º NBR más bajo | 0,20 | 1.500 m | 0,76 | 74 % | 0,85 |
| 2.º NBR más bajo | 0,20 | 3.000 m | 0,77 | 76 % | 0,87 |
| 2.º NBR más bajo | 0,27 | 750 m | 0,61 | 64 % | 0,67 |
| 2.º NBR más bajo | 0,27 | 1.500 m | 0,64 | 68 % | 0,70 |
| 2.º NBR más bajo | 0,27 | 3.000 m | 0,65 | 68 % | 0,71 |
| NBR mínimo | 0,10 | 750 m | 0,60 | 62 % | 1,04 |
| NBR mínimo | 0,10 | 1.500 m | 0,64 | 64 % | 1,07 |
| NBR mínimo | 0,10 | 3.000 m | 0,66 | 64 % | 1,09 |
| NBR mínimo | 0,15 | 750 m | 0,69 | 70 % | 0,91 |
| NBR mínimo | 0,15 | 1.500 m | 0,74 | 76 % | 0,98 |
| NBR mínimo | 0,15 | 3.000 m | 0,75 | 76 % | 1,00 |
| NBR mínimo | 0,20 | 750 m | 0,69 | 72 % | 0,85 |
| NBR mínimo | 0,20 | 1.500 m | 0,77 | 76 % | 0,91 |
| NBR mínimo | 0,20 | 3.000 m | 0,79 | 80 % | 0,92 |
| NBR mínimo | 0,27 | 750 m | 0,64 | 70 % | 0,75 |
| NBR mínimo | 0,27 | 1.500 m | 0,73 | 76 % | 0,81 |
| NBR mínimo | 0,27 | 3.000 m | 0,73 | 78 % | 0,83 |

## ≥ 500 ha (41 incendios)

| Después del fuego | Umbral dNBR | Anclaje a los focos | IoU mediano | IoU ≥ 0,5 | Razón de superficie (mediana) |
|---|---:|---:|---:|---:|---:|
| 2.º NBR más bajo | 0,10 | 750 m | 0,61 | 61 % | 0,82 |
| 2.º NBR más bajo | 0,10 | 1.500 m | 0,73 | 76 % | 0,86 |
| 2.º NBR más bajo | 0,10 | 3.000 m | 0,80 | 78 % | 0,98 |
| 2.º NBR más bajo | 0,15 | 750 m | 0,61 | 61 % | 0,68 |
| 2.º NBR más bajo | 0,15 | 1.500 m | 0,73 | 71 % | 0,82 |
| **2.º NBR más bajo** | **0,15** | **3.000 m** | **0,81** | **73 %** | **0,92** |
| 2.º NBR más bajo | 0,20 | 750 m | 0,61 | 59 % | 0,64 |
| 2.º NBR más bajo | 0,20 | 1.500 m | 0,70 | 68 % | 0,78 |
| 2.º NBR más bajo | 0,20 | 3.000 m | 0,76 | 71 % | 0,82 |
| 2.º NBR más bajo | 0,27 | 750 m | 0,53 | 56 % | 0,54 |
| 2.º NBR más bajo | 0,27 | 1.500 m | 0,61 | 66 % | 0,63 |
| 2.º NBR más bajo | 0,27 | 3.000 m | 0,64 | 68 % | 0,68 |
| NBR mínimo | 0,10 | 750 m | 0,59 | 66 % | 0,88 |
| NBR mínimo | 0,10 | 1.500 m | 0,73 | 76 % | 0,97 |
| NBR mínimo | 0,10 | 3.000 m | 0,78 | 78 % | 0,99 |
| NBR mínimo | 0,15 | 750 m | 0,61 | 68 % | 0,80 |
| NBR mínimo | 0,15 | 1.500 m | 0,73 | 78 % | 0,86 |
| NBR mínimo | 0,15 | 3.000 m | 0,81 | 80 % | 0,95 |
| NBR mínimo | 0,20 | 750 m | 0,62 | 68 % | 0,75 |
| NBR mínimo | 0,20 | 1.500 m | 0,73 | 78 % | 0,82 |
| NBR mínimo | 0,20 | 3.000 m | 0,78 | 80 % | 0,90 |
| NBR mínimo | 0,27 | 750 m | 0,61 | 61 % | 0,62 |
| NBR mínimo | 0,27 | 1.500 m | 0,66 | 71 % | 0,71 |
| NBR mínimo | 0,27 | 3.000 m | 0,68 | 76 % | 0,74 |
