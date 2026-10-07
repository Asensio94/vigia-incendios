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

# ── Perímetro, frente y progresión (después de FEDS, Chen et al. 2022) ─────────────────
# Calibrados con la temporada 2023 contra EFFIS y comprobados en 2024 (docs/validacion.md).
PIXEL_RADIUS_FACTOR = 0.5         # radio del disco de cada píxel, en medios píxeles
CLOSING_KM = 0.75                 # cierre morfológico: rellena huecos de menos de 2 × 0,75 km
STEP_MERGE_HOURS = 1.0            # píxeles a menos de 1 h son la misma pasada
FRONT_KM = 0.3                    # borde a menos de 300 m de un píxel de la última pasada = frente
PERIMETER_MIN_VIIRS = 3           # con menos, el perímetro no añade nada a la huella de píxeles
