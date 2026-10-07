"""Contraste con temporadas pasadas: ¿cuántos incendios cartografiados por EFFIS habría
detectado el vigía, y cuándo?

Se usa el archivo estándar de FIRMS (no el de tiempo real, que no se guarda), con las
mismas reglas que la vigilancia. La máscara de fuentes fijas de cada año sale del otro año,
para no usar información que en tiempo real no se tendría.
"""
from __future__ import annotations

import json
from datetime import timedelta

import numpy as np
from scipy.spatial import cKDTree
from shapely import STRtree
from shapely.geometry import Point, shape

from . import config, effis, focos as F, incendios as I, perimeter, zonas

CLASES = [(30, 100), (100, 500), (500, 1e9)]


def _archivo(anio: int) -> tuple[list[dict], list[dict]]:
    """Focos normalizados y filas «type 2» (fuentes fijas) de un año."""
    out, fijas = [], []
    for prod in config.ARCHIVO_PRODUCTOS:
        sensor = "MODIS" if prod == "modis" else "VIIRS"
        for f in zonas.archivo_firms(prod, anio):
            if f.get("type") == "2":
                fijas.append(f)
                continue
            if f.get("type") in ("1", "3"):     # volcán, mar adentro
                continue
            n = F.normalizar(f, sensor)
            if n:
                out.append(n)
    return out, fijas


def contrastar(anios=(2023, 2024)) -> dict:
    datos = {a: _archivo(a) for a in anios}
    esp = zonas.espana()
    res = {}
    for a in anios:
        focos = [f for f in datos[a][0] if esp.contains(Point(f["lon"], f["lat"]))]
        otras = [r for b in anios if b != a for r in datos[b][1]]
        if otras:
            arbol = cKDTree(zonas.km_xy([float(r["latitude"]) for r in otras],
                                        [float(r["longitude"]) for r in otras]))
            d, _ = arbol.query(zonas.km_xy([f["lat"] for f in focos], [f["lon"] for f in focos]))
            focos = [f for f, di in zip(focos, d) if di > config.FIJAS_RADIO_KM]
        et = I.agrupar(focos)
        grupos: dict[int, list[dict]] = {}
        for f, e in zip(focos, et):
            grupos.setdefault(int(e), []).append(f)
        incs = []
        for fs in grupos.values():
            g = I.huella(fs)
            n_viirs = sum(f["sensor"] == "VIIRS" for f in fs)
            incs.append({"primera": min(f["t"] for f in fs), "ultima": max(f["t"] for f in fs),
                         "n": len(fs), "ha": zonas.ha_geo(g), "g": g,
                         "p": perimeter.geometry(fs) if n_viirs >= config.PERIMETER_MIN_VIIRS else None})
        areas = effis.descargar(f"{a}-01-01", f"{a + 1}-01-01")
        res[a] = _medir(incs, areas)
        res[a]["focos"] = len(focos)
    return res


def _medir(incs: list[dict], areas: list[dict]) -> dict:
    geoms = [i["g"].buffer(config.EFFIS_HOLGURA_KM / 111) for i in incs]
    arbol = STRtree(geoms)
    hol = timedelta(days=config.EFFIS_HOLGURA_DIAS)
    usados = set()
    filas = []
    for a in areas:
        fd = F._dt(a["firedate"])
        hit = None
        for k in arbol.query(shape(a["geometry"]), predicate="intersects"):
            i = incs[k]
            if F._dt(i["primera"]) - hol <= fd <= F._dt(i["ultima"]) + hol:
                if hit is None or i["n"] > incs[hit]["n"]:
                    hit = int(k)
        fila = {"area_ha": a["area_ha"], "hit": hit, "retraso_h": None, "ha_focos": None}
        if hit is not None:
            usados.add(hit)
            i, e = incs[hit], shape(a["geometry"])
            p = i["p"] if i.get("p") is not None else i["g"]
            fila.update(retraso_h=F.horas_entre(a["firedate"], i["primera"]), ha_focos=i["ha"],
                        ha_perimetro=zonas.ha_geo(p), iou_huella=_iou(i["g"], e), iou_perimetro=_iou(p, e))
        filas.append(fila)

    out = {"effis_total": len(areas), "clases": []}
    for lo, hi in CLASES:
        fs = [f for f in filas if lo <= f["area_ha"] < hi]
        det = [f for f in fs if f["hit"] is not None]
        ret = np.array([f["retraso_h"] for f in det]) if det else np.zeros(0)
        out["clases"].append({
            "desde": lo, "hasta": hi if hi < 1e9 else None, "effis": len(fs), "detectados": len(det),
            "retraso_mediana_h": round(float(np.median(ret)), 1) if len(ret) else None,
            "antes_que_effis": int((ret <= 0).sum()),
            "ratio_ha_mediana": _mediana([f["ha_focos"] / f["area_ha"] for f in det]),
            "ratio_perimetro_mediana": _mediana([f["ha_perimetro"] / f["area_ha"] for f in det]),
            "iou_huella_mediana": _mediana([f["iou_huella"] for f in det]),
            "iou_perimetro_mediana": _mediana([f["iou_perimetro"] for f in det]),
        })
    # Incendios del vigía sin ningún perímetro EFFIS (de cualquier tamaño).
    sin = [i for k, i in enumerate(incs) if k not in usados]
    out["vigia_total"] = len(incs)
    out["vigia_sin_effis"] = len(sin)
    out["vigia_sin_effis_3_focos"] = sum(i["n"] >= 3 for i in sin)
    out["vigia_sin_effis_10_focos"] = sum(i["n"] >= 10 for i in sin)
    out["vigia_con_effis_por_focos"] = {
        str(n): [sum(1 for k, i in enumerate(incs) if k in usados and i["n"] >= n),
                 sum(1 for i in incs if i["n"] >= n)] for n in (1, 3, 10, 30)}
    return out


def _iou(a, b) -> float:
    """Intersection over union; areas in square degrees are fine for a ratio at one latitude."""
    a, b = a.buffer(0), b.buffer(0)
    u = a.union(b).area
    return a.intersection(b).area / u if u else 0.0


def _mediana(xs: list[float]) -> float | None:
    return round(float(np.median(xs)), 2) if xs else None


def _d(x: float | None) -> str:
    return f"{x:.2f}".replace(".", ",") if x is not None else "—"


def informe(res: dict) -> str:
    L = ["# Contraste con temporadas pasadas", "",
         "Reglas de la vigilancia aplicadas al archivo estándar de FIRMS (VIIRS S-NPP, NOAA-20 y "
         "MODIS) y comparadas con las áreas quemadas de EFFIS en España. Un incendio de EFFIS "
         "cuenta como detectado si su perímetro toca la huella de focos de un incendio del vigía "
         f"(con {config.EFFIS_HOLGURA_KM:g} km de margen) y su fecha cae dentro de las del incendio "
         f"(± {config.EFFIS_HOLGURA_DIAS} días). La máscara de fuentes fijas de cada año sale del otro año.", "",
         "Las dos últimas columnas comparan con EFFIS la huella de píxeles y el perímetro estimado "
         "(solo en incendios con al menos " f"{config.PERIMETER_MIN_VIIRS} píxeles VIIRS). El IoU es "
         "superficie común entre superficie unida: 1 sería el mismo dibujo. Sale bajo cuando un "
         "incendio del vigía abarca varias áreas EFFIS, porque se compara con cada una por separado. "
         f"Parámetros del perímetro ({config.PIXEL_RADIUS_FACTOR:g} de radio, {config.CLOSING_KM:g} km de "
         "cierre) elegidos con 2023; 2024 sirve de comprobación.", ""]
    for a, r in res.items():
        L += [f"## {a}", "", f"{r['focos']:,} focos tras los filtros; {r['vigia_total']:,} incendios del vigía; "
              f"{r['effis_total']:,} áreas EFFIS de cualquier tamaño.".replace(",", "."), "",
              "| Tamaño (EFFIS) | Incendios EFFIS | Detectados | Retraso mediano | Vistos antes que la fecha EFFIS "
              "| Superficie / EFFIS: píxeles · perímetro | Coincidencia (IoU): píxeles · perímetro |",
              "|---|---:|---:|---:|---:|---:|---:|"]
        for c in r["clases"]:
            t = f"{c['desde']}–{c['hasta']} ha" if c["hasta"] else f"≥ {c['desde']} ha"
            pct = f" ({100 * c['detectados'] / c['effis']:.0f} %)" if c["effis"] else ""
            ret = f"{c['retraso_mediana_h']:+.1f} h".replace(".", ",") if c["retraso_mediana_h"] is not None else "—"
            rat = f"{_d(c['ratio_ha_mediana'])} · {_d(c.get('ratio_perimetro_mediana'))}"
            iou = f"{_d(c.get('iou_huella_mediana'))} · {_d(c.get('iou_perimetro_mediana'))}"
            L.append(f"| {t} | {c['effis']} | {c['detectados']}{pct} | {ret} | {c['antes_que_effis']} | {rat} | {iou} |")
        L += ["", "Incendios del vigía que coinciden con algún perímetro EFFIS, según su número de focos:", "",
              "| Focos | Con perímetro EFFIS | Total |", "|---:|---:|---:|"]
        for n, (con, tot) in r["vigia_con_effis_por_focos"].items():
            L.append(f"| ≥ {n} | {con} ({100 * con / tot:.0f} %) | {tot} |" if tot else f"| ≥ {n} | 0 | 0 |")
        L.append("")
    return "\n".join(L).replace("(1", "(1")


def main() -> dict:
    res = contrastar()
    (config.DATA / "validacion.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    (config.RAIZ / "docs" / "validacion.md").write_text(informe(res), encoding="utf-8")
    return res
