"""Rutas, fuentes y umbrales. Todo lo que decide qué es un incendio está aquí."""
from __future__ import annotations

from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DATA = RAIZ / "data"
ZONAS_DIR = DATA / "zonas"
FOCOS_DIR = DATA / "focos"
INCENDIOS_JSON = DATA / "incendios.json"
EFFIS_JSON = DATA / "effis.json"
CACHE_JSON = DATA / "cache.json"          # cobertura CORINE por celda y municipios
SITE = RAIZ / "site"

REPO = "Asensio94/vigia-incendios"
WEB = "https://asensio94.github.io/vigia-incendios/"
UA = {"User-Agent": f"vigia-incendios/0.1 (+https://github.com/{REPO})"}

# ── Focos activos de NASA FIRMS ─────────────────────────────────────────────────────────
# Los ficheros públicos de las últimas 24 h, 48 h y 7 días no piden clave. La región
# «Europe» llega hasta 34° N; Canarias está en «Northern_and_Central_Africa».
FIRMS = "https://firms.modaps.eosdis.nasa.gov/data/active_fire"
FIRMS_FUENTES = {
    "N": ("suomi-npp-viirs-c2", "SUOMI_VIIRS_C2"),
    "N20": ("noaa-20-viirs-c2", "J1_VIIRS_C2"),
    "N21": ("noaa-21-viirs-c2", "J2_VIIRS_C2"),
    "MODIS": ("modis-c6.1", "MODIS_C6_1"),
}
FIRMS_REGIONES = ("Europe", "Northern_and_Central_Africa")
# Archivo anual por países (producto estándar, con el campo «type»): se lee por rangos
# HTTP, sin bajar el zip entero.
FIRMS_ARCHIVO = "https://firms.modaps.eosdis.nasa.gov/data/country/zips/{producto}_{anio}_all_countries.zip"
ARCHIVO_PRODUCTOS = ("viirs-snpp", "viirs-jpss1", "modis")

MODIS_CONFIANZA_MIN = 30          # 0-100; por debajo, casi todo son reflejos y bordes de nube
# Los focos VIIRS de confianza baja son sobre todo destellos de sol en tejados e
# invernaderos: fuera.

# ── Fuentes fijas ───────────────────────────────────────────────────────────────────────
# FIRMS marca en su archivo como «type 2» los puntos calientes que se repiten año tras año
# en el mismo sitio (cementeras, acerías, refinerías, antorchas). Un foco nuevo a menos de
# esta distancia de uno de ellos se descarta.
FIJAS_RADIO_KM = 0.5
FIJAS_ANIOS = (2023, 2024)

# ── Agrupación de focos en incendios ────────────────────────────────────────────────────
# Dos focos son del mismo incendio si sus píxeles quedan a menos de ENLACE_KM (o de 0,75
# veces la suma de sus tamaños, para los píxeles grandes del borde de pasada) y se vieron
# con menos de ENLACE_HORAS de diferencia. Las cadenas valen: un incendio que avanza va
# enlazando píxeles nuevos con los de la pasada anterior.
ENLACE_KM = 2.0
ENLACE_HORAS = 72
VENTANA_DIAS = 21                 # focos que se reagrupan en cada pasada

ACTIVO_HORAS = 24
RECIENTE_DIAS = 7

# ── Cruces ──────────────────────────────────────────────────────────────────────────────
NATURA_URL = ("https://bio.discomap.eea.europa.eu/arcgis/rest/services/"
              "ProtectedSites/Natura2000Sites/MapServer/{capa}/query")
NATURA_CAPAS = (0, 1)             # 0: Directiva Hábitats (ZEC/LIC); 1: Directiva Aves (ZEPA)
CLC_URL = ("https://image.discomap.eea.europa.eu/arcgis/rest/services/Corine/"
           "CLC2018_WM/MapServer/0/query")
CLC_MUESTRAS = 30                 # celdas consultadas a CORINE por incendio, como mucho
CLC_CELDA = 0.004                 # grados (~400 m): una consulta por celda, con caché

EFFIS_URL = "https://api.effis.emergency.copernicus.eu/rest/2/burntareas/current/"
EFFIS_DIAS = 60                   # áreas quemadas que se vuelven a pedir en cada consulta
EFFIS_CADA_HORAS = 6
EFFIS_HOLGURA_DIAS = 3            # margen de fechas para casar un perímetro con un incendio
EFFIS_HOLGURA_KM = 1.0

NOMINATIM = "https://nominatim.openstreetmap.org"

# ── Superficie quemada con Sentinel-2 ──────────────────────────────────────────────────
# Escenas L2A de Earth Search (AWS), sin clave. NBR con B8A (nir08) y B12 (swir22), a 20 m.
STAC_URL = "https://earth-search.aws.element84.com/v1"
STAC_COLECCION = "sentinel-2-l2a"
PERIMETRO_RES_M = 20
PERIMETRO_MARGEN_M = 2000      # recorte alrededor de la huella de focos
PRE_DIAS = 40                  # antes: escenas de las semanas previas al primer foco...
PRE_ESCENAS_MAX = 6            # ...las más recientes...
PRE_NUBES_MAX = 60             # ...con menos de este % de nubes en la tesela
POST_DIAS = 20                 # después: desde el primer foco hasta 20 días tras el último
POST_NUBES_MAX = 80
POST_ESCENAS_TRAS = 4          # escenas de después del último foco que se usan
# Clases SCL aceptadas. Después del fuego se acepta también la 2 («zona oscura»), que es
# como Sen2Cor suele clasificar la ceniza; antes no, porque ahí es sombra o agua turbia.
SCL_PRE = (4, 5, 7)
SCL_POST = (2, 4, 5, 7)
DNBR_UMBRAL = 0.15             # contrastado con EFFIS 2023-2024: docs/validacion_perimetro.md
PERIMETRO_ANCLA_M = 3000       # a menos de esto de los focos (y dentro de la ventana de cálculo);
                               # con 750 m se cortaban las lenguas de los grandes, con huecos entre focos
# Severidad según el dNBR (Key y Benson, 2006, simplificada a tres clases).
SEVERIDAD = (("baja", -9.0, 0.27), ("moderada", 0.27, 0.66), ("alta", 0.66, 9.0))
# Producción
PERIMETRO_MIN_FOCOS = 3        # o en Red Natura o con EFFIS: los focos aislados no se calculan
PERIMETRO_CADA_HORAS = 6       # cada incendio se revisa en el catálogo como mucho cada 6 h
PERIMETRO_PRESUPUESTO_S = 15 * 60   # tiempo máximo por vuelta; lo demás, en la siguiente
# Si las nubes dejan ver menos de esta fracción de la zona de los focos, la cifra no se da
# como medida: «0 ha» bajo un cielo cubierto no es «no ardió nada».
PERIMETRO_COBERTURA_MIN = 0.5
