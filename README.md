# Vigía de incendios

Incendios con focos activos en España vistos por satélite cada hora, sin esperar a la
estadística oficial. Los focos de NASA FIRMS se agrupan en incendios con reglas fijas y se
cruzan con la Red Natura 2000, con la cubierta del suelo (CORINE Land Cover 2018) y con las
áreas quemadas que cartografía EFFIS, el servicio europeo de incendios de Copernicus. La
superficie quemada se estima con imágenes de Sentinel-2 en cuanto hay una pasada despejada.

**Web:** https://asensio94.github.io/vigia-incendios/ · **Fuente Atom:**
[feed.xml](https://asensio94.github.io/vigia-incendios/feed.xml) · **GeoJSON:**
[incendios.geojson](https://asensio94.github.io/vigia-incendios/incendios.geojson) ·
**Quemado según Sentinel-2:** [quemado.geojson](https://asensio94.github.io/vigia-incendios/quemado.geojson)

Está pensado para que periodistas y entidades de conservación sepan en pocas horas qué
arde, dónde y si toca un espacio protegido. No sustituye a la información oficial de
extinción: un foco es un píxel caliente, no un parte.

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

Todo son reglas fijas, escritas en [`vigia/config.py`](vigia/config.py). No hay ningún
modelo entrenado ni inteligencia artificial.

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
python -m vigia zonas      # capas fijas: España, Red Natura 2000, fuentes fijas (una vez)
python -m vigia vigilar    # una vuelta: focos, incendios, EFFIS, Sentinel-2 y web en site/
python -m vigia web        # rehacer la web sin descargar nada
python -m vigia validar    # contraste con 2023 y 2024 (descarga el archivo de FIRMS)
```

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
| `data/cache.json` | Cubierta CORINE por celda y municipios ya consultados |
| `data/zonas/` | Contorno de España, Red Natura 2000 y fuentes fijas |

## Fuentes y licencias

- **Focos activos:** NASA FIRMS (LANCE), parte del Earth Science Data and Information System
  (ESDIS) de la NASA. Uso libre con atribución.
- **Áreas quemadas:** EFFIS, Copernicus Emergency Management Service, © Unión Europea.
- **Imágenes Sentinel-2:** Copernicus, © Unión Europea; catálogo y copia en AWS de Earth
  Search (Element 84).
- **Red Natura 2000 y CORINE Land Cover 2018:** Agencia Europea de Medio Ambiente.
- **Municipios y contorno de España:** Nominatim, © colaboradores de OpenStreetMap (ODbL).
- **Ortofoto:** PNOA, CC BY 4.0 scne.es.

El código se publica bajo licencia MIT.

Forma parte de un conjunto de proyectos hermanos:
[Observatorio de alegaciones](https://asensio94.github.io/observatorio-alegaciones/) ·
[Centinela Natura](https://asensio94.github.io/centinela-natura/) ·
[Vigilancia de humedales](https://asensio94.github.io/vigilancia-humedales/) ·
[Sub Nocte](https://asensio94.github.io/sub-nocte/) ·
[Riesgo de tendidos para aves](https://asensio94.github.io/riesgo-tendidos-aves/) ·
[Grafo de promotores](https://asensio94.github.io/grafo-promotores/) ·
[Cartera de las cotizadas](https://asensio94.github.io/cartera-cotizadas/) ·
[Cuaderno de campo](https://asensio94.github.io/cuaderno-campo/).
