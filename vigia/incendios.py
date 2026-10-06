"""De focos a incendios, por reglas fijas y sin modelos entrenados.

Dos focos son del mismo incendio si sus píxeles están cerca (config.ENLACE_KM, o más para
los píxeles grandes del borde de pasada) y se vieron con menos de config.ENLACE_HORAS de
diferencia. Las cadenas valen, así que un frente que avanza sigue siendo el mismo incendio.

En cada pasada se reagrupan los focos de las últimas semanas. Los incendios conservan su
identificador: un grupo nuevo que contiene focos de un incendio ya conocido es ese
incendio, y si junta dos conocidos, el más antiguo absorbe al otro, que queda como «unido»
y su enlace lleva al superviviente.
"""
from __future__ import annotations

import json
import logging
import math
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import requests
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree
from shapely.geometry import box, mapping, shape
from shapely.ops import unary_union

from . import config, focos as F, zonas

log = logging.getLogger(__name__)

ESTADOS = {"activo": "Con focos en las últimas 24 h",
           "reciente": "Sin focos desde hace 1 a 7 días",
           "inactivo": "Sin focos desde hace más de 7 días",
           "unido": "Unido a otro incendio"}

# Grupos de CORINE 2018 para describir qué arde.
GRUPOS_CLC = {"bosque": "bosque", "matorral": "matorral y pasto", "agroforestal": "dehesa y mosaico agroforestal",
              "desnudo": "roquedo o suelo desnudo", "agricola": "cultivos", "artificial": "suelo urbano o industrial",
              "agua": "humedal o agua"}


def grupo_clc(code: str | None) -> str | None:
    if not code:
        return None
    if code.startswith("31"):
        return "bosque"
    if code.startswith("32"):
        return "matorral"
    if code.startswith("33"):
        return "desnudo"
    if code in ("243", "244"):
        return "agroforestal"
    if code.startswith("2"):
        return "agricola"
    if code.startswith("1"):
        return "artificial"
    return "agua"


# ── Agrupado ────────────────────────────────────────────────────────────────────────────

def agrupar(focos: list[dict]) -> np.ndarray:
    """Etiqueta de grupo para cada foco."""
    n = len(focos)
    if n == 0:
        return np.zeros(0, int)
    xy = zonas.km_xy([f["lat"] for f in focos], [f["lon"] for f in focos])
    t = F.tiempos(focos)
    tam = np.array([max(f["scan"], f["track"]) for f in focos])
    arbol = cKDTree(xy)
    pares = [arbol.query_pairs(config.ENLACE_KM, output_type="ndarray")]
    # Píxeles grandes (MODIS o VIIRS en el borde de la pasada): radio propio.
    umbral = 0.75 * (tam + tam.max())
    for i in np.flatnonzero(umbral > config.ENLACE_KM):
        js = np.array(arbol.query_ball_point(xy[i], umbral[i]), int)
        js = js[js != i]
        pares.append(np.column_stack([np.full(len(js), i), js]))
    p = np.concatenate([q for q in pares if len(q)]) if any(len(q) for q in pares) else np.zeros((0, 2), int)
    if len(p):
        i, j = p[:, 0], p[:, 1]
        d = np.hypot(*(xy[i] - xy[j]).T)
        ok = (d <= np.maximum(config.ENLACE_KM, 0.75 * (tam[i] + tam[j]))) & \
             (np.abs(t[i] - t[j]) <= config.ENLACE_HORAS)
        i, j = i[ok], j[ok]
    else:
        i = j = np.zeros(0, int)
    m = coo_matrix((np.ones(len(i)), (i, j)), shape=(n, n))
    return connected_components(m, directed=False)[1]


def huella(fs: list[dict]):
    """Unión de los píxeles: los VIIRS si los hay (375 m), si no los MODIS (1 km)."""
    v = [f for f in fs if f["sensor"] == "VIIRS"] or fs
    cajas = []
    for f in v:
        dx = f["scan"] / 2 / (111.32 * math.cos(math.radians(f["lat"])))
        dy = f["track"] / 2 / 110.57
        cajas.append(box(f["lon"] - dx, f["lat"] - dy, f["lon"] + dx, f["lat"] + dy))
    return unary_union(cajas)


# ── Registro de incendios ───────────────────────────────────────────────────────────────

def cargar() -> dict:
    if config.INCENDIOS_JSON.exists():
        return json.loads(config.INCENDIOS_JSON.read_text(encoding="utf-8"))
    return {"incendios": [], "actualizado": None}


def guardar(reg: dict) -> None:
    reg["incendios"].sort(key=lambda i: i["id"])
    config.INCENDIOS_JSON.write_text(json.dumps(reg, ensure_ascii=False, indent=1), encoding="utf-8")


def _nuevo_id(primera: str, usados: set[str]) -> str:
    base = "IN-" + primera[:10].replace("-", "")
    n = 1
    while f"{base}-{n:03d}" in usados:
        n += 1
    return f"{base}-{n:03d}"


def actualizar(reg: dict, todos: list[dict], ahora: str, detalle: bool = True) -> dict:
    """Reagrupa los focos recientes y rehace los incendios afectados.

    `todos` son los focos de los años en juego; se les escribe el campo «incendio».
    Devuelve un resumen de la pasada.
    """
    por_id = {i["id"]: i for i in reg["incendios"]}

    def final(iid: str) -> str:
        while iid in por_id and por_id[iid].get("unido_en"):
            iid = por_id[iid]["unido_en"]
        return iid

    desde = F.hace(config.VENTANA_DIAS * 24, F._dt(ahora))
    rec = [f for f in todos if f["t"] >= desde]
    etiquetas = agrupar(rec)
    grupos: dict[int, list[int]] = {}
    for k, e in enumerate(etiquetas):
        grupos.setdefault(int(e), []).append(k)

    # Los grupos grandes eligen primero: si un incendio conocido se parte, se queda su
    # nombre la parte con más focos suyos.
    orden = sorted(grupos.values(), key=lambda ks: -len(ks))
    reclamados: set[str] = set()
    tocados: set[str] = set()
    nuevos = unidos = 0
    for ks in orden:
        cuenta: dict[str, int] = {}
        for k in ks:
            if rec[k]["incendio"]:
                iid = final(rec[k]["incendio"])
                cuenta[iid] = cuenta.get(iid, 0) + 1
        conocidos = [i for i in cuenta if i in por_id and i not in reclamados]
        if conocidos:
            conocidos.sort(key=lambda i: (por_id[i]["primera"], i))
            sid = conocidos[0]
            for otro in conocidos[1:]:
                o = por_id[otro]
                o.update({"estado": "unido", "unido_en": sid})
                s = por_id[sid]
                s["unidos"] = sorted(set(s.get("unidos", []) + [otro] + o.get("unidos", [])))
                unidos += 1
        else:
            primera = min(rec[k]["t"] for k in ks)
            sid = _nuevo_id(primera, set(por_id))
            por_id[sid] = {"id": sid, "primera": primera}
            reg["incendios"].append(por_id[sid])
            nuevos += 1
        reclamados.add(sid)
        tocados.add(sid)
        for k in ks:
            rec[k]["incendio"] = sid

    # Los focos antiguos de un incendio absorbido pasan al superviviente.
    for f in todos:
        if f["incendio"]:
            f["incendio"] = final(f["incendio"])

    miembros: dict[str, list[dict]] = {}
    for f in todos:
        if f["incendio"] in tocados:
            miembros.setdefault(f["incendio"], []).append(f)
    for iid in tocados:
        describir(por_id[iid], miembros.get(iid, []), detalle)

    for i in reg["incendios"]:
        if i.get("estado") != "unido" and i.get("ultima"):
            h = F.horas_entre(i["ultima"], ahora)
            i["estado"] = ("activo" if h <= config.ACTIVO_HORAS else
                           "reciente" if h <= config.RECIENTE_DIAS * 24 else "inactivo")
    reg["actualizado"] = ahora
    return {"focos_recientes": len(rec), "incendios_nuevos": nuevos, "unidos": unidos,
            "tocados": len(tocados)}


def describir(inc: dict, fs: list[dict], detalle: bool = True) -> None:
    """Cifras, huella y cruces de un incendio a partir de sus focos."""
    if not fs:
        return
    antes = inc.get("n_focos")
    g = huella(fs)
    c = g.representative_point()
    vi = [f for f in fs if f["sensor"] == "VIIRS"]
    inc.update({
        "primera": min(f["t"] for f in fs),
        "ultima": max(f["t"] for f in fs),
        "n_focos": len(fs),
        "n_viirs": len(vi),
        "pasadas": len({(f["sat"], f["t"]) for f in fs}),
        "satelites": sorted({f["sat"] for f in fs}),
        "frp_max": round(max(f["frp"] for f in fs), 1),
        "frp_total": round(sum(f["frp"] for f in fs), 1),
        "ha_focos": round(zonas.ha_geo(g), 1),
        "centro": [round(c.x, 5), round(c.y, 5)],
        "bbox": [round(v, 5) for v in g.bounds],
        "geometry": _geo(g.simplify(0.0003)),
    })
    if not detalle or antes == len(fs):
        return
    inc["natura"] = zonas.natura_de(g)
    inc["cobertura"] = cobertura(fs)
    if not inc.get("lugar") or len(fs) >= 2 * (inc.get("lugar_focos") or 1):
        inc["lugar"] = lugar(c.y, c.x) or inc.get("lugar")
        inc["lugar_focos"] = len(fs)


def _geo(g) -> dict:
    return zonas._redondear(mapping(g), 5)


def tipo(inc: dict) -> str:
    """Qué arde, según CORINE en los píxeles con focos."""
    c = inc.get("cobertura") or {}
    if not c:
        return "sin datos"
    natural = sum(c.get(k, 0) for k in ("bosque", "matorral", "agroforestal", "desnudo"))
    if natural >= 0.5:
        return "vegetación natural"
    if c.get("agricola", 0) >= 0.5:
        return "cultivos"
    if c.get("artificial", 0) >= 0.5:
        return "suelo urbano o industrial"
    return "mixto"


# ── CORINE y municipio, con caché ───────────────────────────────────────────────────────

_cache: dict | None = None


def cache() -> dict:
    global _cache
    if _cache is None:
        _cache = (json.loads(config.CACHE_JSON.read_text(encoding="utf-8"))
                  if config.CACHE_JSON.exists() else {})
        _cache.setdefault("clc", {})
        _cache.setdefault("lugar", {})
    return _cache


def guardar_cache() -> None:
    if _cache is not None:
        config.CACHE_JSON.write_text(json.dumps(_cache, ensure_ascii=False, sort_keys=True),
                                     encoding="utf-8")


def _clc(clave: str) -> str | None:
    la, lo = (float(v) for v in clave.split(","))
    try:
        r = requests.get(config.CLC_URL, timeout=60, params={
            "geometry": f"{lo},{la}", "geometryType": "esriGeometryPoint", "inSR": "4326",
            "spatialRel": "esriSpatialRelIntersects", "outFields": "Code_18",
            "returnGeometry": "false", "f": "json"})
        feats = r.json().get("features", [])
    except (requests.RequestException, ValueError):
        return None
    return feats[0]["attributes"]["Code_18"] if feats else ""


def cobertura(fs: list[dict]) -> dict:
    """Reparto por grupos de CORINE de las celdas con focos (una muestra si son muchas)."""
    cel = config.CLC_CELDA
    cuenta: dict[str, int] = {}
    for f in fs:
        k = f"{round(f['lat'] / cel) * cel:.4f},{round(f['lon'] / cel) * cel:.4f}"
        cuenta[k] = cuenta.get(k, 0) + 1
    claves = sorted(cuenta)
    if len(claves) > config.CLC_MUESTRAS:
        paso = len(claves) / config.CLC_MUESTRAS
        claves = [claves[int(i * paso)] for i in range(config.CLC_MUESTRAS)]
    c = cache()["clc"]
    falta = [k for k in claves if k not in c]
    if falta:
        with ThreadPoolExecutor(6) as ex:
            for k, v in zip(falta, ex.map(_clc, falta)):
                if v is not None:
                    c[k] = v
    peso: dict[str, float] = {}
    for k in claves:
        gr = grupo_clc(c.get(k))
        if gr:
            peso[gr] = peso.get(gr, 0) + cuenta[k]
    tot = sum(peso.values())
    return {k: round(v / tot, 2) for k, v in sorted(peso.items(), key=lambda x: -x[1])} if tot else {}


def lugar(lat: float, lon: float) -> dict | None:
    """Municipio, provincia y comunidad de un punto (Nominatim, una consulta por segundo)."""
    import time
    clave = f"{lat:.2f},{lon:.2f}"
    c = cache()["lugar"]
    if clave in c:
        return c[clave]
    try:
        time.sleep(1.1)
        r = requests.get(f"{config.NOMINATIM}/reverse", headers=config.UA, timeout=60, params={
            "lat": lat, "lon": lon, "zoom": 10, "format": "jsonv2", "accept-language": "es"})
        a = r.json().get("address", {})
    except (requests.RequestException, ValueError):
        return None
    # En España el municipio (nivel 8 de OSM) llega como city, town o village; «municipality»
    # y «county» son a veces la comarca. La provincia llega como province o state_district; en
    # las comunidades uniprovinciales no llega y vale «state».
    out = {"municipio": a.get("city") or a.get("town") or a.get("village") or a.get("municipality"),
           "provincia": a.get("province") or a.get("state_district") or a.get("state"),
           "comunidad": a.get("state")}
    if not any(out.values()):
        return None
    c[clave] = out
    return out
