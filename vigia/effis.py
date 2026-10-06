"""Áreas quemadas cartografiadas por EFFIS (Copernicus) y su enlace con los incendios.

EFFIS dibuja el perímetro quemado con imágenes MODIS, VIIRS y Sentinel-2 días después del
fuego. Aquí sirve de segunda opinión: un incendio con perímetro EFFIS ya no es solo una
nube de focos, y su superficie es la cartografiada, no la de los píxeles calientes.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone

import requests
from shapely import STRtree
from shapely.geometry import shape

from . import config, focos as F, zonas

log = logging.getLogger(__name__)


def descargar(desde: str, hasta: str | None = None, area_min: float = 0) -> list[dict]:
    """Áreas quemadas de España con fecha de fuego en [desde, hasta)."""
    params = {"country": "ES", "limit": 100, "ordering": "firedate",
              "firedate__gte": f"{desde}T00:00:00Z"}
    if hasta:
        params["firedate__lt"] = f"{hasta}T00:00:00Z"
    if area_min:
        params["area_ha__gte"] = area_min
    url, out = config.EFFIS_URL, []
    while url:
        r = requests.get(url, params=params, timeout=180, headers=config.UA)
        r.raise_for_status()
        d = r.json()
        for x in d["results"]:
            if not x.get("shape"):
                continue
            fd = datetime.fromisoformat(x["firedate"]).astimezone(timezone.utc)
            out.append({"id": x["id"], "firedate": F.iso(fd), "area_ha": x["area_ha"] or 0,
                        "provincia": x.get("province"), "municipio": x.get("commune"),
                        "natura_pct": float(x["percna2k"]) if x.get("percna2k") else None,
                        "actualizado": (x.get("lastupdate") or "")[:10],
                        # ~20 m: sobra para cruzarlo con píxeles de 375 m.
                        "geometry": zonas._redondear(shape(x["shape"]).simplify(0.0002).__geo_interface__, 5)})
        url, params = (d.get("next") or "").replace("http://", "https://") or None, None
    return out


def actualizar(forzar: bool = False) -> list[dict]:
    """Áreas de los últimos config.EFFIS_DIAS días, como mucho cada EFFIS_CADA_HORAS."""
    previo = (json.loads(config.EFFIS_JSON.read_text(encoding="utf-8"))
              if config.EFFIS_JSON.exists() else {"consultado": None, "areas": []})
    if not forzar and previo["consultado"] and \
            F.horas_entre(previo["consultado"], F.iso(F.ahora())) < config.EFFIS_CADA_HORAS:
        return previo["areas"]
    desde = (datetime.now(timezone.utc) - timedelta(days=config.EFFIS_DIAS)).strftime("%Y-%m-%d")
    try:
        nuevas = descargar(desde)
    except requests.RequestException as e:
        log.warning("EFFIS no responde (%s); se usan las áreas de la consulta anterior", e)
        return previo["areas"]
    # Las antiguas se conservan: el registro de la temporada no depende de la ventana.
    por_id = {a["id"]: a for a in previo["areas"]}
    por_id.update({a["id"]: a for a in nuevas})
    areas = sorted(por_id.values(), key=lambda a: (a["firedate"], a["id"]))
    config.EFFIS_JSON.write_text(json.dumps({"consultado": F.iso(F.ahora()), "areas": areas},
                                            ensure_ascii=False), encoding="utf-8")
    return areas


def enlazar(incendios: list[dict], areas: list[dict]) -> int:
    """Pone en cada incendio las áreas EFFIS que caen en su huella y en sus fechas."""
    if not areas:
        return 0
    geoms = [shape(a["geometry"]) for a in areas]
    arbol = STRtree(geoms)
    holgura = timedelta(days=config.EFFIS_HOLGURA_DIAS)
    n = 0
    for inc in incendios:
        if inc.get("estado") == "unido" or not inc.get("geometry"):
            continue
        g = shape(inc["geometry"]).buffer(config.EFFIS_HOLGURA_KM / 111)
        t0 = F._dt(inc["primera"]) - holgura
        t1 = F._dt(inc["ultima"]) + holgura
        hits = []
        for i in arbol.query(g, predicate="intersects"):
            a = areas[i]
            if t0 <= F._dt(a["firedate"]) <= t1:
                hits.append(a)
        inc["effis"] = [{k: a[k] for k in ("id", "firedate", "area_ha", "actualizado")} for a in hits]
        inc["effis_ha"] = round(sum(a["area_ha"] for a in hits), 1) if hits else None
        n += bool(hits)
    return n
