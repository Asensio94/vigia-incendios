"""Focos activos: descarga de FIRMS, filtros y registro anual en data/focos/AAAA.csv.

Un foco es un píxel caliente visto por un satélite en una pasada: VIIRS (S-NPP, NOAA-20 y
NOAA-21, píxel de 375 m) o MODIS (Terra y Aqua, 1 km). No es un incendio: el agrupado en
incendios lo hace incendios.py.
"""
from __future__ import annotations

import csv
import io
import logging
from datetime import datetime, timedelta, timezone

import numpy as np
import requests
from shapely.geometry import Point

from . import config, zonas

log = logging.getLogger(__name__)

CAMPOS = ["clave", "t", "lat", "lon", "sat", "sensor", "conf", "frp", "scan", "track", "dn", "incendio"]
_SAT = {"N": "S-NPP", "N20": "NOAA-20", "N21": "NOAA-21", "1": "NOAA-20", "2": "NOAA-21",
        "T": "Terra", "A": "Aqua", "Terra": "Terra", "Aqua": "Aqua"}


def normalizar(f: dict, sensor: str) -> dict | None:
    """Fila de FIRMS (tiempo real o archivo) a foco; None si no pasa el filtro de confianza."""
    conf = f["confidence"].strip().lower()
    if sensor == "VIIRS":
        conf = conf[:1]                     # «low»/«l», «nominal»/«n», «high»/«h»
        if conf == "l":
            return None
    elif int(float(conf)) < config.MODIS_CONFIANZA_MIN:
        return None
    hhmm = f["acq_time"].zfill(4)
    t = f"{f['acq_date']}T{hhmm[:2]}:{hhmm[2:]}Z"
    sat = _SAT.get(f["satellite"].strip(), f["satellite"].strip())
    lat, lon = round(float(f["latitude"]), 5), round(float(f["longitude"]), 5)
    return {"clave": f"{sat}|{t}|{lat:.5f}|{lon:.5f}", "t": t, "lat": lat, "lon": lon,
            "sat": sat, "sensor": sensor, "conf": conf, "frp": float(f.get("frp") or 0),
            "scan": float(f["scan"]), "track": float(f["track"]), "dn": f.get("daynight", ""),
            "incendio": ""}


def filtrar(focos: list[dict]) -> list[dict]:
    """Solo España y lejos de fuentes fijas de calor."""
    esp = zonas.espana()
    focos = [f for f in focos if esp.contains(Point(f["lon"], f["lat"]))]
    arbol = zonas.fijas()
    if arbol is None or not focos:
        return focos
    d, _ = arbol.query(zonas.km_xy([f["lat"] for f in focos], [f["lon"] for f in focos]))
    return [f for f, di in zip(focos, d) if di > config.FIJAS_RADIO_KM]


def descargar(periodo: str = "48h") -> list[dict]:
    """Focos de las últimas 24h/48h/7d de todos los satélites, ya filtrados."""
    out = []
    for sat, (carpeta, prefijo) in config.FIRMS_FUENTES.items():
        sensor = "MODIS" if sat == "MODIS" else "VIIRS"
        for region in config.FIRMS_REGIONES:
            url = f"{config.FIRMS}/{carpeta}/csv/{prefijo}_{region}_{periodo}.csv"
            try:
                r = requests.get(url, timeout=180, headers=config.UA)
                r.raise_for_status()
            except requests.RequestException as e:
                log.warning("FIRMS %s %s: %s", sat, region, e)
                continue
            filas = csv.DictReader(io.StringIO(r.text))
            # Recorte grueso antes del punto en polígono, que es lo caro.
            for f in filas:
                la, lo = float(f["latitude"]), float(f["longitude"])
                if 27.4 < la < 44.2 and -18.6 < lo < 4.6:
                    n = normalizar(f, sensor)
                    if n:
                        out.append(n)
    return filtrar(out)


# ── Registro ────────────────────────────────────────────────────────────────────────────

def _fichero(anio: int):
    return config.FOCOS_DIR / f"{anio}.csv"


def leer(desde: str | None = None) -> list[dict]:
    """Focos guardados desde una fecha ISO (todos si no se da)."""
    anios = sorted(int(p.stem) for p in config.FOCOS_DIR.glob("*.csv"))
    if desde:
        anios = [a for a in anios if a >= int(desde[:4])]
    out = []
    for a in anios:
        with _fichero(a).open(encoding="utf-8") as fh:
            for f in csv.DictReader(fh):
                if desde and f["t"] < desde:
                    continue
                for k in ("lat", "lon", "frp", "scan", "track"):
                    f[k] = float(f[k])
                out.append(f)
    return out


def guardar(focos: list[dict]) -> None:
    """Reescribe los años presentes en `focos` (que debe traer todos los de esos años)."""
    por_anio: dict[int, list[dict]] = {}
    for f in focos:
        por_anio.setdefault(int(f["t"][:4]), []).append(f)
    config.FOCOS_DIR.mkdir(parents=True, exist_ok=True)
    for a, fs in por_anio.items():
        fs.sort(key=lambda f: (f["t"], f["clave"]))
        with _fichero(a).open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=CAMPOS, extrasaction="ignore", lineterminator="\n")
            w.writeheader()
            for f in fs:
                w.writerow({**f, "frp": f"{f['frp']:g}", "scan": f"{f['scan']:g}",
                            "track": f"{f['track']:g}"})


def anadir(nuevos: list[dict]) -> int:
    """Suma al registro los focos que no estaban; devuelve cuántos son nuevos."""
    if not nuevos:
        return 0
    desde = min(f["t"] for f in nuevos)[:4] + "-01-01"
    todos = leer(desde)
    vistos = {f["clave"] for f in todos}
    frescos = [f for f in nuevos if f["clave"] not in vistos]
    if frescos:
        guardar(todos + frescos)
    return len(frescos)


def ahora() -> datetime:
    return datetime.now(timezone.utc).replace(second=0, microsecond=0)


def iso(t: datetime) -> str:
    return t.strftime("%Y-%m-%dT%H:%MZ")


def horas_entre(a: str, b: str) -> float:
    return (_dt(b) - _dt(a)).total_seconds() / 3600


def _dt(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc)


def hace(horas: float, desde: datetime | None = None) -> str:
    return iso((desde or ahora()) - timedelta(hours=horas))


def tiempos(focos: list[dict]) -> np.ndarray:
    """Horas desde 1970 de cada foco, para comparar con numpy."""
    return np.array([_dt(f["t"]).timestamp() / 3600 for f in focos])
