# Validation en France : saisons 2022 et 2025

Les règles de la veille, appliquées à l'archive standard de FIRMS pour la France métropolitaine (VIIRS S-NPP, NOAA-20 et MODIS), comparées à deux références :

- **EFFIS** (Copernicus), les surfaces brûlées cartographiées par satélite, comme en Espagne. Un feu EFFIS est détecté si son contour touche l'empreinte des foyers d'un feu de la veille (avec 1,0 km de marge) et si sa date tombe dans celles du feu (± 3 jours).
- **BDIFF**, la base de données officielle des incendies de forêt en France (ministère de l'Agriculture, Licence Ouverte 2.0), qui reprend aussi les feux de Prométhée. Elle ne donne pas de contour : un feu BDIFF est détecté si l'empreinte d'un feu de la veille touche sa commune (avec 1,0 km de marge) et si la première alerte tombe dans ses dates (± 3 jours). Le retard est mesuré depuis l'heure de la première alerte.

Le masque des sources fixes de chaque année vient de l'autre année, pour ne pas utiliser d'information qu'on n'aurait pas en temps réel.

## 2022

19 099 foyers après les filtres ; 4 079 feux de la veille ; 1 088 surfaces EFFIS ; 4 433 feux BDIFF, dont 135 de 30 ha ou plus.

### Face à EFFIS

| Taille (EFFIS) | Feux EFFIS | Détectés | Retard médian sur la date EFFIS | Vus avant la date EFFIS |
|---|---:|---:|---:|---:|
| 30–100 ha | 206 | 187 (91 %) | +1,0 h | 40 |
| 100–500 ha | 69 | 66 (96 %) | +1,0 h | 12 |
| ≥ 500 ha | 15 | 15 (100 %) | +2,0 h | 0 |

### Face à BDIFF

| Surface parcourue (BDIFF) | Feux BDIFF | dont surfaces mesurées | Détectés | Retard médian sur la première alerte |
|---|---:|---:|---:|---:|
| 30–100 ha | 88 | 20 | 60 (68 %) | +0,6 h |
| 100–500 ha | 32 | 6 | 28 (88 %) | +1,1 h |
| ≥ 500 ha | 15 | 7 | 14 (93 %) | +3,5 h |

Feux BDIFF de 1 000 ha ou plus :

| Commune (INSEE) | Première alerte (UTC) | Surface BDIFF | Détecté | Retard | Foyers |
|---|---|---:|---|---:|---:|
| Landiras (33225) | 2022-07-12 14:31 | 12 552 ha | oui | +6,6 h | 4096 |
| Landiras (33225) | 2022-08-12 10:36 | 6 743 ha | non | — | — |
| La Teste-de-Buch (33529) | 2022-07-12 12:36 | 5 709 ha | oui | +8,5 h | 1287 |
| Saumos (33503) | 2022-09-12 13:21 | 3 248 ha | oui | +21,5 h | 547 |
| Aiguines (83002) | 2022-06-18 07:25 | 2 500 ha | oui | +3,8 h | 231 |
| Brasparts (29016) | 2022-07-24 21:28 | 1 917 ha | oui | −151,9 h | 138 |
| Graveson (13045) | 2022-07-14 14:16 | 1 452 ha | oui | +6,6 h | 104 |
| Baugé-en-Anjou (49018) | 2022-08-08 11:03 | 1 450 ha | oui | +0,2 h | 319 |
| Massegros Causses Gorges (48094) | 2022-08-08 14:21 | 1 207 ha | oui | +6,4 h | 98 |
| Lussas (07145) | 2022-07-27 07:43 | 1 120 ha | oui | +3,1 h | 85 |

La reprise de Landiras d'août (6 743 ha) n'est pas un oubli de la veille : elle l'a suivie comme un seul feu de 1 742 foyers du 9 au 13 août, mais à une quinzaine de kilomètres de la commune de Landiras, à laquelle BDIFF rattache le feu. Sans contour, le croisement par commune ne peut pas les relier.

## 2025

9 320 foyers après les filtres ; 3 926 feux de la veille ; 1 312 surfaces EFFIS ; 2 541 feux BDIFF, dont 64 de 30 ha ou plus.

### Face à EFFIS

| Taille (EFFIS) | Feux EFFIS | Détectés | Retard médian sur la date EFFIS | Vus avant la date EFFIS |
|---|---:|---:|---:|---:|
| 30–100 ha | 186 | 170 (91 %) | +1,0 h | 45 |
| 100–500 ha | 64 | 58 (91 %) | +1,0 h | 19 |
| ≥ 500 ha | 5 | 5 (100 %) | +2,0 h | 0 |

### Face à BDIFF

| Surface parcourue (BDIFF) | Feux BDIFF | dont surfaces mesurées | Détectés | Retard médian sur la première alerte |
|---|---:|---:|---:|---:|
| 30–100 ha | 45 | 32 | 34 (76 %) | +0,2 h |
| 100–500 ha | 16 | 14 | 13 (81 %) | +0,6 h |
| ≥ 500 ha | 3 | 3 | 3 (100 %) | +0,4 h |

Feux BDIFF de 1 000 ha ou plus :

| Commune (INSEE) | Première alerte (UTC) | Surface BDIFF | Détecté | Retard | Foyers |
|---|---|---:|---|---:|---:|
| Ribaute (11311) | 2025-08-05 14:16 | 11 133 ha | oui | +5,5 h | 529 |
| Narbonne (11262) | 2025-07-07 12:45 | 1 551 ha | oui | +0,4 h | 73 |

## Surface brûlée Sentinel-2 face à EFFIS

Échantillon de 59 feux de 2022 et 2025 avec contour EFFIS, stratifié par taille et par année ; 59 avec une image avant et après. Mêmes réglages qu'en Espagne (dNBR > 0,15, à moins de 3 000 m des foyers). IoU : surface commune divisée par la surface des deux réunis (1 = même contour).

| Taille (EFFIS) | Feux | IoU médian | IoU ≥ 0,5 | Surface / EFFIS (médiane) |
|---|---:|---:|---:|---:|
| Tous | 59 | 0,54 | 54 % | 0,95 |
| 30–100 ha | 20 | 0,58 | 55 % | 1,02 |
| 100–500 ha | 20 | 0,53 | 55 % | 0,97 |
| ≥ 500 ha | 19 | 0,55 | 53 % | 0,84 |
