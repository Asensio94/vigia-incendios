"""Capas fijas de cada país: contorno, Red Natura 2000 y fuentes fijas de calor.

Se descargan una vez con `python -m vigia zonas` y van en el repositorio (data/zonas y
data/fr/zonas), para que la vigilancia de cada hora no dependa de que la EEA,
OpenStreetMap o el archivo de FIRMS respondan.
"""
from __future__ import annotations

import csv
import gzip
import io
import json
import math
import zipfile
from functools import lru_cache

import numpy as np
import requests
from scipy.spatial import cKDTree
from shapely import STRtree
from shapely.geometry import box, mapping, shape
from shapely.ops import unary_union

from . import config
from .config import Country

# Nombre del contorno en OpenStreetMap, y figuras de Natura 2000 según SITETYPE (A: Directiva
# Aves, B: Directiva Hábitats, C: las dos sobre el mismo polígono) con las siglas de cada país.
CONTORNO = {"ES": ("espana.geojson", "España"), "FR": ("france.geojson", "France")}
FIGURAS = {"ES": {"A": "ZEPA", "B": "ZEC", "C": "ZEC y ZEPA"},
           "FR": {"A": "ZPS", "B": "ZSC", "C": "ZSC et ZPS"}}


def contorno_path(c: Country):
    return c.zonas_dir / CONTORNO[c.code][0]


def natura_path(c: Country):
    return c.zonas_dir / "natura.geojson.gz"         # detalle de ~20 m, para los cruces


def natura_web_path(c: Country):
    return c.zonas_dir / "natura_web.geojson"        # simplificada, para el mapa


def fijas_path(c: Country):
    return c.zonas_dir / "fuentes_fijas.csv"


# ── Descarga ────────────────────────────────────────────────────────────────────────────

def descargar_contorno(c: Country) -> None:
    nombre = CONTORNO[c.code][1]
    r = requests.get(f"{config.NOMINATIM}/search", headers=config.UA, timeout=120, params={
        "q": nombre, "countrycodes": c.code.lower(), "featuretype": "country",
        "polygon_geojson": 1, "polygon_threshold": 0.001, "format": "json", "limit": 1})
    r.raise_for_status()
    g = shape(r.json()[0]["geojson"]).buffer(0)
    if c.boundary_clip:
        g = g.intersection(box(*c.boundary_clip))
    c.zonas_dir.mkdir(parents=True, exist_ok=True)
    contorno_path(c).write_text(json.dumps({"type": "Feature", "geometry": mapping(g),
                                            "properties": {"nombre": nombre}}), encoding="utf-8")


def descargar_natura(c: Country) -> int:
    """Espacios Natura 2000 de un país desde el servicio de la EEA, en páginas de 200."""
    espacios: dict[str, dict] = {}
    for capa in config.NATURA_CAPAS:
        offset = 0
        while True:
            r = requests.get(config.NATURA_URL.format(capa=capa), timeout=300, params={
                "where": f"SITECODE LIKE '{c.code}%'", "outFields": "SITECODE,SITENAME,SITETYPE",
                "returnGeometry": "true", "outSR": "4326", "maxAllowableOffset": 0.0002,
                "orderByFields": "SITECODE", "resultOffset": offset, "resultRecordCount": 200,
                "f": "geojson"})
            r.raise_for_status()
            feats = r.json()["features"]
            for f in feats:
                p = f["properties"]
                if f["geometry"]:
                    espacios.setdefault(p["SITECODE"], {"props": p, "geoms": []})["geoms"].append(
                        shape(f["geometry"]).buffer(0))
            if len(feats) < 200:
                break
            offset += 200

    feats, web = [], []
    for code, e in sorted(espacios.items()):
        g = unary_union(e["geoms"])
        p = e["props"]
        tipo = FIGURAS[c.code].get(p.get("SITETYPE"), p.get("SITETYPE"))
        props = {"codigo": code, "nombre": p["SITENAME"], "tipo": tipo}
        feats.append({"type": "Feature", "geometry": mapping(g), "properties": props})
        gw = g.simplify(0.003, preserve_topology=True)
        if not gw.is_empty:
            web.append({"type": "Feature", "geometry": _redondear(mapping(gw)), "properties": props})
    with gzip.open(natura_path(c), "wt", encoding="utf-8") as fh:
        json.dump({"type": "FeatureCollection", "features": feats}, fh, ensure_ascii=False)
    natura_web_path(c).write_text(json.dumps({"type": "FeatureCollection", "features": web},
                                     ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return len(feats)


def _redondear(geom: dict, dec: int = 4) -> dict:
    def r(c):
        return [r(x) for x in c] if isinstance(c[0], (list, tuple)) else [round(c[0], dec), round(c[1], dec)]
    return {"type": geom["type"], "coordinates": r(geom["coordinates"])}


class _Remoto(io.RawIOBase):
    """Fichero remoto que se lee por rangos HTTP: zipfile solo pide el índice del zip y el
    trozo del país, no los 400 MB del archivo mundial."""

    def __init__(self, url: str):
        self.url, self.pos = url, 0
        self.size = int(requests.head(url, timeout=120).headers["Content-Length"])

    def seekable(self): return True
    def readable(self): return True
    def tell(self): return self.pos

    def seek(self, off, whence=0):
        self.pos = off if whence == 0 else self.pos + off if whence == 1 else self.size + off
        return self.pos

    def readinto(self, b):
        n = min(len(b), self.size - self.pos)
        if n <= 0:
            return 0
        r = requests.get(self.url, timeout=600,
                         headers={"Range": f"bytes={self.pos}-{self.pos + n - 1}"})
        r.raise_for_status()
        b[:len(r.content)] = r.content
        self.pos += len(r.content)
        return len(r.content)


def archivo_firms(producto: str, anio: int, pais: str = "Spain") -> list[dict]:
    """Focos de un año y un país del archivo estándar de FIRMS (con el campo «type»)."""
    url = config.FIRMS_ARCHIVO.format(producto=producto, anio=anio)
    z = zipfile.ZipFile(io.BufferedReader(_Remoto(url), buffer_size=1 << 20))
    nombre = next(n for n in z.namelist() if n.endswith(f"_{pais}.csv"))
    return list(csv.DictReader(io.StringIO(z.read(nombre).decode("utf-8"))))


def descargar_fijas(c: Country) -> int:
    """Fuentes fijas: los focos «type 2» del archivo de FIRMS, juntados en celdas de ~200 m."""
    celdas: dict[tuple, int] = {}
    for anio in config.FIJAS_ANIOS:
        for prod in config.ARCHIVO_PRODUCTOS:
            for f in archivo_firms(prod, anio, c.firms_country):
                if f.get("type") == "2":
                    k = (round(float(f["latitude"]) / 0.002), round(float(f["longitude"]) / 0.002))
                    celdas[k] = celdas.get(k, 0) + 1
    with fijas_path(c).open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["lat", "lon", "focos"])
        for (a, b), n in sorted(celdas.items()):
            w.writerow([round(a * 0.002, 4), round(b * 0.002, 4), n])
    return len(celdas)


# ── Uso ─────────────────────────────────────────────────────────────────────────────────

def km_xy(lat, lon):
    """Coordenadas planas en km (equirrectangular local): basta para distancias de pocos km."""
    lat, lon = np.asarray(lat, float), np.asarray(lon, float)
    return np.column_stack([lon * 111.32 * np.cos(np.radians(lat)), lat * 110.57])


@lru_cache(None)
def contorno(c: Country, margen: float = 0.02):
    """Contorno preparado del país. Por defecto con 2 km de margen: los píxeles de costa y
    frontera tienen el centro a veces fuera."""
    from shapely.prepared import prep
    g = shape(json.loads(contorno_path(c).read_text(encoding="utf-8"))["geometry"])
    return prep(g.buffer(margen) if margen else g)


@lru_cache(None)
def fijas(c: Country) -> cKDTree | None:
    if not fijas_path(c).exists():
        return None
    filas = list(csv.DictReader(fijas_path(c).open(encoding="utf-8")))
    if not filas:
        return None
    return cKDTree(km_xy([float(f["lat"]) for f in filas], [float(f["lon"]) for f in filas]))


@lru_cache(None)
def natura(c: Country) -> tuple[list[dict], list, STRtree]:
    with gzip.open(natura_path(c), "rt", encoding="utf-8") as fh:
        fc = json.load(fh)
    props = [f["properties"] for f in fc["features"]]
    geoms = [shape(f["geometry"]) for f in fc["features"]]
    return props, geoms, STRtree(geoms)


def ha_geo(g) -> float:
    """Hectáreas de una geometría en grados, con la escala de su latitud."""
    if g.is_empty:
        return 0.0
    lat = g.centroid.y
    return g.area * 111.32 * 110.57 * math.cos(math.radians(lat)) * 100


def natura_de(g, c: Country) -> list[dict]:
    """Espacios Natura que toca una huella, con las hectáreas dentro de cada uno."""
    props, geoms, arbol = natura(c)
    out = []
    for i in arbol.query(g, predicate="intersects"):
        ha = ha_geo(g.intersection(geoms[i]))
        if ha >= 0.5:
            out.append({**props[i], "ha": round(ha, 1)})
    return sorted(out, key=lambda e: -e["ha"])
