# Vigía de incendios

Incendios con focos activos en España y en Francia metropolitana (Córcega incluida) vistos
por satélite cada hora, sin esperar a la estadística oficial. Los focos de NASA FIRMS se agrupan en incendios con reglas fijas y se
cruzan con la Red Natura 2000, con la cubierta del suelo (CORINE Land Cover 2018) y con las
áreas quemadas que cartografía EFFIS, el servicio europeo de incendios de Copernicus. La
superficie quemada se estima con imágenes de Sentinel-2 en cuanto hay una pasada despejada.

**Web:** https://asensio94.github.io/vigia-incendios/ · **Fuente Atom:**
[feed.xml](https://asensio94.github.io/vigia-incendios/feed.xml) · **GeoJSON:**
[incendios.geojson](https://asensio94.github.io/vigia-incendios/incendios.geojson) ·
**Quemado según Sentinel-2:** [quemado.geojson](https://asensio94.github.io/vigia-incendios/quemado.geojson) ·
**Señales para Estado de las IBA:** [signals.json](https://asensio94.github.io/vigia-incendios/signals.json)
(los dos países) · **Francia, en francés:** https://asensio94.github.io/vigia-incendios/fr/

Está pensado para que periodistas y entidades de conservación sepan en pocas horas qué
arde, dónde y si toca un espacio protegido. No sustituye a la información oficial de
extinción: un foco es un píxel caliente, no un parte.

> **Estado: activo.** Se actualiza solo y sigue en desarrollo.

## Cómo funciona

1. **Focos.** Cada hora se descargan los ficheros públicos de FIRMS de las últimas 48 horas
   (o de 7 días si la vuelta anterior es de hace más de 40 horas). Los satélites son VIIRS
   en S-NPP, NOAA-20 y NOAA-21, con píxel de 375 m, y MODIS en Terra y Aqua, con píxel de
   1 km. Estos ficheros no piden clave.
2. **Filtros.**
   - Se quitan los focos de confianza baja: VIIRS «low» y MODIS por debajo de 30.
   - Se quitan los que caen fuera de España.
   - Se quitan los que están a menos de 0,5 km de una fuente fija de calor (cementeras,
     acerías, refinerías). Las fuentes fijas son las que FIRMS marcó como tales en su
     archivo de 2023 y 2024.
3. **Incendios.** Dos focos son del mismo incendio si sus píxeles están a menos de 2 km (más
   si son píxeles grandes) y se vieron con menos de 72 h de diferencia; la relación se
   encadena.
   - Cada incendio conserva su identificador (`IN-AAAAMMDD-NNN`) de una vuelta a otra.
   - Si dos incendios se juntan, sobrevive el más antiguo y el otro queda como «unido». Su
     enlace lleva al superviviente.
4. **Cruces.**
   - Espacios de la Red Natura 2000 que toca la huella de píxeles.
   - Cubierta CORINE en hasta 30 celdas con focos.
   - Municipio y provincia, de Nominatim.
   - Perímetro EFFIS: el área quemada que toca la huella con 1 km de margen y empezó entre
     3 días antes del primer foco y 3 días después del último.
5. **Superficie quemada con Sentinel-2.** Para los incendios que no son focos aislados:
   - NBR = (B8A − B12) / (B8A + B12), a 20 m, de las escenas L2A de Earth Search (AWS),
     con la máscara de nubes SCL.
   - Antes: mediana de las 6 escenas más recientes de los 40 días previos al primer foco.
   - Después: el segundo NBR más bajo de cada píxel (el único, si solo hay una observación)
     desde el primer foco hasta 4 escenas después del último (como mucho 20 días). Así entra
     todo el avance aunque cada escena tenga nubes distintas, y una sombra de nube o una bruma
     que la máscara no detectó en una sola escena no cuenta como quemado: hacen falta dos
     escenas que lo vean.
   - Quemado: dNBR por encima del umbral, en manchas unidas a la huella de focos y cerca de
     ella. Así no entran las cosechas ni los labrados, que también bajan el NBR.
   - Severidad por el dNBR: baja hasta 0,27, moderada hasta 0,66, alta por encima.
   - Hectáreas quemadas dentro de cada espacio de la Red Natura 2000.
   - Cada incendio se revisa como mucho cada 6 horas y se recalcula si cambian sus focos o
     llegan escenas nuevas. Mientras no estén todas, el perímetro es «provisional».
   - Si las nubes dejan ver menos de la mitad de la zona de los focos, la cifra se publica
     como mínimo («al menos X ha») o, si no se ve nada quemado, como «aún no se puede medir».
   - Si más de la mitad de lo quemado solo lo vio una imagen, el filtro del segundo NBR no
     actúa: la ficha avisa de que la cifra puede sobrar y no se da por definitiva hasta que
     llegue otra imagen o pasen los 20 días.
   - Cada ficha enlaza la imagen más despejada de antes y la de después en Copernicus Browser,
     en infrarrojo de onda corta (B12-B8A-B4), para comprobar el perímetro a ojo.
   - `PERIMETRO_VERSION` entra en la clave de cada perímetro: al cambiar el cálculo se sube y
     se rehacen todos en las vueltas siguientes.
6. **Estados.** «Activo» si hay algún foco en las últimas 24 h; «reciente» hasta 7 días;
   luego «inactivo».
   - Los **focos aislados** (uno o dos focos, sin perímetro EFFIS ni Red Natura) suelen ser
     quemas agrícolas y no se muestran salvo que se pida.

6. **Perímetro, frente y progresión** (a partir de 3 píxeles VIIRS). Sigue la idea de
   [FEDS](https://doi.org/10.1038/s41597-022-01343-0), el seguimiento de incendios de la NASA
   (Chen et al., 2022), con reglas que se pueden rehacer a mano:
   - Cada píxel VIIRS es un disco de radio medio píxel × 0,5.
   - Tras cada pasada se suman los discos nuevos al perímetro anterior y se cierran los
     huecos de menos de 1,5 km (cierre morfológico de 0,75 km): el terreno que el fuego
     cruzó entre dos pasadas. El perímetro nunca encoge.
   - **Frente activo:** el tramo del borde a menos de 300 m de un píxel de la última pasada.
     Se da su longitud en km.
   - **Progresión:** superficie tras cada pasada y crecimiento en ha/h entre pasadas.
   - Código en [`vigia/perimeter.py`](vigia/perimeter.py).

### Análisis por pasadas

Cada incendio de 100 ha o más cuyo perímetro estimado cambió al menos una vez tiene su
propia página, `incendio/<id>.html`, enlazada desde su tarjeta («Por pasadas»). En ella:

- un mapa en relieve 3D (MapLibre, con el MDT de [Mapterhorn](https://mapterhorn.com):
  IGN en España y Francia, sin clave);
- una línea de tiempo que reproduce el incendio pasada a pasada, con los píxeles que se
  encienden y se apagan dibujados a su tamaño real;
- las **isocronas**, que son el perímetro estimado tras cada pasada VIIRS, igual que el del
  mapa principal;
- una curva de la superficie acumulada;
- los **momentos clave**: mayor salto, pasada de más potencia, frente más largo, 50 % y 90 %
  del tamaño final, entrada en cada espacio Red Natura 2000, reactivaciones y huecos de más
  de 18 h sin observación.

Todo sale de reglas fijas, en [`vigia/ficha.py`](vigia/ficha.py).

La página explica sus límites. Con VIIRS hay unas dos ventanas al día y entre ellas no hay
datos. Un píxel de 375 m no son 14 ha quemadas. MODIS enciende focos pero no mueve el
perímetro.

### Grandes incendios

La pestaña **Grandes incendios** (`incendio/`, en cada país) reúne todos los incendios con
ficha por pasadas. Hay una tabla con buscador, filtros por año y comunidad (o región) y
orden por cualquier columna. Recoge dos tipos de incendio:

- **Los mayores de cada temporada desde 2022.** `python -m vigia mayores` descarga el
  archivo estándar de FIRMS de cada año (sin NOAA-21) y los agrupa con las mismas reglas del
  mapa. Se queda con los diez mayores de más de 1.000 ha y los nombra por el municipio de sus
  primeros píxeles, que suele ser donde empezó el fuego (no el centro de la mancha).
- **Los de este año con ficha**, que entran solos en cuanto pasan de 100 ha y su perímetro ha
  cambiado al menos una vez.

Los incendios concretos, por caja y fechas, se añaden con `python -m vigia historico`.
Así se hizo Landiras 2022, que solo cubre su primera fase. Todos se guardan en
`data/historicos.json` y `data/historicos/<id>.csv.gz`, y la vuelta horaria no descarga nada.

La superficie es la estimada desde el espacio, no la oficial. Las quemas de invierno del
Pirineo y la cornisa cantábrica, muchas y dispersas, salen como un solo incendio y exageran.
Los fuegos que corren en pocas horas entre dos pasadas se quedan cortos, como el del Aude en
2025.

Todo son reglas fijas, escritas en [`vigia/config.py`](vigia/config.py). No hay ningún
modelo entrenado ni inteligencia artificial.

## Francia

Francia es una dimensión más del mismo vigía, no un proyecto aparte: las mismas reglas,
los mismos satélites y los mismos cruces, con su contorno, su Red Natura y su registro.

- **Qué cubre:** Francia metropolitana con Córcega. Los departamentos y territorios de
  ultramar quedan fuera: el vigía sigue Europa, donde Natura 2000, CORINE y EFFIS son
  homogéneos.
- **Focos:** los mismos ficheros de FIRMS. Cada contorno lleva 2 km de margen por los píxeles de
  costa; en la frontera, donde los márgenes se solapan, decide el contorno sin margen, así
  que un foco no sale en las dos webs.
- **Identificadores:** `FR-IN-AAAAMMDD-NNN`. Los de España no cambian.
- **Communes:** la API Découpage administratif ([geo.api.gouv.fr](https://geo.api.gouv.fr))
  da la commune, su código INSEE (5 caracteres; en Córcega, 2A y 2B), el departamento y la
  región. En `signals.json` los municipios franceses van por su código INSEE. El fichero sigue
  la versión 2 del formato: cada señal lleva su país y la cobertura va por país, así que Estado
  de las IBA lee los incendios franceses en su página de Francia.
- **Red Natura 2000:** la misma capa de la AEMA; las figuras se llaman ZPS y ZSC.
- **Web en francés** en [`/fr/`](https://asensio94.github.io/vigia-incendios/fr/), con la
  tipografía francesa (espacio fino ante «%» y en los miles). Los datos (`incendios.json`,
  GeoJSON, `signals.json`) son los mismos en los dos idiomas: claves y valores canónicos.
- **Validación con BDIFF**, la base de datos de incendios forestales de Francia (ministerio
  de Agricultura, Licence Ouverte 2.0). Recoge también los incendios del arco mediterráneo
  que publicaba Prométhée, así que no hace falta descargar Prométhée aparte. No trae
  contornos: un incendio de BDIFF cuenta como visto si la huella de un incendio del vigía
  toca su commune y la primera alerta cae en sus fechas. BDIFF se completa una vez al año,
  así que solo sirve para validar, no en tiempo real.
- **Certificado de BDIFF:** su servidor envía un certificado intermedio que no es el que
  firma el suyo. [`vigia/bdiff.py`](vigia/bdiff.py) descarga el intermedio correcto de la
  dirección AIA del certificado y lo añade a las autoridades de `certifi`; la cadena se
  sigue comprobando hasta una raíz de confianza.

## Contraste con temporadas pasadas

Las mismas reglas se aplicaron al archivo de FIRMS de 2023 y 2024 y se compararon con los
incendios que cartografió EFFIS. Detalle en [docs/validacion.md](docs/validacion.md).

| Tamaño según EFFIS | 2023 | 2024 |
|---|---:|---:|
| 30–100 ha | 83 % | 76 % |
| 100–500 ha | 93 % | 76 % |
| ≥ 500 ha | 91 % | 100 % |

El perímetro se acerca más a EFFIS que la huella de píxeles. En los incendios que
corresponden a una sola área EFFIS de 30 ha o más, la coincidencia mediana (IoU) sube de
0,30 a 0,35 en 2023 y de 0,28 a 0,34 en 2024. El error típico de superficie baja del 93 %
al 68 % en 2023 y del 118 % al 68 % en 2024. Los parámetros se eligieron con 2023, y 2024
sirvió de comprobación.

Los que se escapan apenas tienen focos en el archivo de FIRMS. Son incendios que ardieron
entre dos pasadas o bajo nubes, como los de invierno en la cornisa cantábrica. Los filtros
del vigía no los tapan.

Los umbrales se eligieron contrastando el cálculo con los perímetros de EFFIS de una
muestra de 2023 y 2024: [docs/validacion_perimetro.md](docs/validacion_perimetro.md).

### Francia: 2022 y 2025

Las mismas reglas, sin tocar ningún umbral, sobre el archivo de FIRMS de Francia en 2022 (los
grandes incendios de Gironde y las Landas) y 2025 (Aude), frente a EFFIS y frente a BDIFF.
Detalle, con los grandes incendios uno a uno, en [docs/validation_fr.md](docs/validation_fr.md)
(en francés, como la web que lo enlaza).

| Tamaño | EFFIS 2022 | EFFIS 2025 | BDIFF 2022 | BDIFF 2025 |
|---|---:|---:|---:|---:|
| 30–100 ha | 187 de 206 (91 %) | 170 de 186 (91 %) | 60 de 88 (68 %) | 34 de 45 (76 %) |
| 100–500 ha | 66 de 69 (96 %) | 58 de 64 (91 %) | 28 de 32 (88 %) | 13 de 16 (81 %) |
| ≥ 500 ha | 15 de 15 | 5 de 5 | 14 de 15 | 3 de 3 |

Frente a BDIFF el acierto es menor en los pequeños porque BDIFF cuenta incendios que EFFIS
no cartografía (muchos de ellos con la superficie solo estimada) y porque el cruce va por
commune, no por contorno. El primer foco llega, en mediana, entre 0,2 y 3,5 horas después
de la primera alerta de BDIFF según el año y el tamaño: lo que tarda la siguiente pasada. En
tiempo real hay que sumar las unas tres horas que tarda FIRMS en publicarla.

El único incendio de 500 ha o más que no se empareja es la reanudación de Landiras de agosto
de 2022 (6.743 ha). El vigía la siguió como un solo incendio de 1.742 focos entre el 9 y el
13 de agosto, pero ardió a unos 15 km de la commune de Landiras, que es a la que BDIFF la
atribuye, y sin contorno el cruce por commune no puede unirlos.

## Límites

- **La superficie de los píxeles con focos no es superficie quemada.** En incendios pequeños
  la exagera: un fuego de una hectárea enciende un píxel de 14 ha. La superficie citable es
  la de EFFIS o la oficial.
- **El perímetro estimado tampoco lo es.** Mejora la huella, pero en los incendios de más
  de 500 ha de 2024 se quedó en la mitad de EFFIS (mediana 0,49): el humo y las pasadas
  perdidas dejan zonas quemadas sin ningún píxel. Es una estimación para seguir el
  incendio mientras arde, no una cartografía.
- **La superficie de Sentinel-2 es una estimación propia.** Puede quedarse corta bajo nubes
  persistentes o con fuego de superficie bajo arbolado, que apenas cambia el NBR visto desde
  arriba. Como cifra oficial, la de EFFIS o la de la comunidad autónoma.
- FIRMS publica cada pasada unas tres horas después. El humo espeso, las nubes y el fuego
  bajo arbolado pueden esconder un incendio que sigue ardiendo.
- «Activo» quiere decir que el satélite vio calor en las últimas 24 h, no que el incendio
  esté sin controlar.
- La cubierta del suelo es de 2018.

### Datos de censos de especies

**El vigía no incorpora datos de censos de especies** (colonias, nidos, dormideros,
territorios ni cualquier otra ubicación precisa de individuos o poblaciones).

- Esa información es interna de las entidades que la producen y les pertenece a ellas.
- No se publica en la web, no se guarda en este repositorio, ni en su historial ni en sus
  artefactos, y no interviene en ningún cálculo.
- Una ubicación precisa de una colonia junto a un incendio, publicada en abierto, puede
  poner en riesgo a la especie (molestias, expolio, persecución).

Si algún día se cruzara con censos, sería en una instalación privada de la entidad
propietaria, que leería los incendios de este repositorio (el GeoJSON o la fuente Atom) y
haría el cruce en su lado. Nada de ese cruce volvería aquí.

## Pendiente

- **Atlas de aves.** Se cruzará con las cuadrículas de 10×10 km de los atlas de
  distribución cuando las entidades que los publican faciliten los datos y su licencia lo
  permita. Será la presencia de especies por cuadrícula, nunca censos (ver arriba).
- **Clave de FIRMS** (opcional). Con una `MAP_KEY` gratuita se podría consultar el área de
  España directamente y pedir días concretos. Hoy no hace falta.

## Uso

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
python -m vigia zonas      # capas fijas de cada país: contorno, Red Natura 2000, fuentes fijas (una vez)
python -m vigia vigilar    # una vuelta: focos, incendios, EFFIS, Sentinel-2 y web en site/ y site/fr/
python -m vigia web        # rehacer las webs sin descargar nada
python -m vigia validar    # contraste con 2023 y 2024 (descarga el archivo de FIRMS)
python -m vigia historico 2025-jarilla --pais ES --bbox=-6.35,39.90,-5.55,40.45   --desde 2025-08-10 --hasta 2025-08-28 --titulo "Jarilla (Cáceres), agosto de 2025"   # ficha histórica
python -m vigia mayores --pais ES --anios 2022-2025   # los mayores de cada temporada (archivo de FIRMS)
python -c "from vigia import validacion_fr; validacion_fr.main()"   # Francia: 2022 y 2025, EFFIS y BDIFF
```

`zonas` acepta `--pais ES` o `--pais FR` para rehacer solo uno.

El workflow [`vigilancia.yml`](.github/workflows/vigilancia.yml) ejecuta `vigilar` cada
hora en GitHub Actions. Guarda `data/` cuando entran focos nuevos y publica `site/` en la
rama `gh-pages`.

## Datos que se guardan

| Fichero | Contenido |
|---|---|
| `data/focos/AAAA.csv` | Todos los focos que pasaron los filtros, con el incendio al que pertenecen |
| `data/incendios.json` | Registro de incendios con cifras, huella, perímetro estimado, frente, progresión, cruces, estado y perímetro de Sentinel-2 |
| `data/validacion_perimetro.json` | Contraste de los perímetros de Sentinel-2 con EFFIS |
| `data/effis.json` | Áreas quemadas de EFFIS (perímetros simplificados a ~20 m) |
| `data/historicos.json`, `data/historicos/` | Incendios históricos con ficha por pasadas: su registro y sus focos del archivo de FIRMS |
| `data/cache.json` | Cubierta CORINE por celda y municipios ya consultados |
| `data/zonas/` | Contorno de España, Red Natura 2000 y fuentes fijas |
| `data/fr/` | Lo mismo para Francia, más `validacion.json` (2022 y 2025 frente a EFFIS y BDIFF) |

De BDIFF solo se usa lo necesario para cruzar y citar el lugar: commune, código INSEE,
departamento, hora de la primera alerta y superficie. Ni personas ni causas. En el
repositorio solo quedan los recuentos de la validación y, uno a uno, los incendios de
1.000 ha o más.

## Fuentes y licencias

- **Focos activos:** NASA FIRMS (LANCE), parte del Earth Science Data and Information System
  (ESDIS) de la NASA. Uso libre con atribución.
- **Áreas quemadas:** EFFIS, Copernicus Emergency Management Service, © Unión Europea.
- **Imágenes Sentinel-2:** Copernicus, © Unión Europea; catálogo y copia en AWS de Earth
  Search (Element 84).
- **Red Natura 2000 y CORINE Land Cover 2018:** Agencia Europea de Medio Ambiente.
- **Municipios y contorno de España:** Nominatim, © colaboradores de OpenStreetMap (ODbL).
- **Ortofoto:** PNOA, CC BY 4.0 scne.es.
- **Relieve (fichas por pasadas):** Mapterhorn, con los MDT del IGN (CC BY 4.0 scne.es), el
  RGE ALTI y el LiDAR HD del IGN francés (Licence Ouverte 2.0) y Copernicus GLO-30.
- **Francia — communes y contorno:** API Découpage administratif (geo.api.gouv.fr, Licence
  Ouverte 2.0) y, para el contorno, OpenStreetMap (ODbL). **Validación:** BDIFF, ministère de
  l'Agriculture et de la Souveraineté alimentaire (Licence Ouverte 2.0). **Ortofoto:** IGN,
  Géoplateforme.

El código se publica bajo licencia MIT.

Forma parte de [Terra Aperta](https://asensio94.github.io/terra-aperta/), un conjunto de proyectos hermanos de
datos abiertos sobre naturaleza:
[Sub Nocte](https://github.com/Asensio94/sub-nocte) ·
[Vigía de incendios](https://github.com/Asensio94/vigia-incendios) ·
[Centinela Natura](https://github.com/Asensio94/centinela-natura) ·
[Estado de las IBA](https://github.com/Asensio94/estado-iba) ·
[Riesgo de tendidos para aves](https://github.com/Asensio94/riesgo-tendidos-aves) ·
[Observatorio de alegaciones](https://github.com/Asensio94/observatorio-alegaciones) ·
[Grafo de promotores](https://github.com/Asensio94/grafo-promotores) ·
[Vigilancia de humedales](https://github.com/Asensio94/vigilancia-humedales) ·
[Caudal ecológico](https://github.com/Asensio94/caudal-ecologico) ·
[Acuíferos de Francia](https://github.com/Asensio94/acuiferos-francia) ·
[Depuración y baño](https://github.com/Asensio94/depuracion-y-bano) ·
[Construir en zona inundable](https://github.com/Asensio94/zona-inundable).
