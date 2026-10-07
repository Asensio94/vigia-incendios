"""Contraste con temporadas pasadas: ¿cuántos incendios cartografiados por EFFIS habría
detectado el vigía, y cuándo?

Se usa el archivo estándar de FIRMS (no el de tiempo real, que no se guarda), con las
mismas reglas que la vigilancia. La máscara de fuentes fijas de cada año sale del otro año,
para no usar información que en tiempo real no se tendría.
"""
from __future__ import annotations

import json
from itertools import product
from datetime import timedelta

import numpy as np
from scipy.spatial import cKDTree
from shapely import STRtree
from shapely.geometry import Point, shape

from . import config, effis, focos as F, incendios as I, zonas

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


def incendios_archivo(anio: int, datos: dict) -> tuple[list[dict], int]:
    """Incendios del vigía en un año pasado: focos del archivo con las reglas de siempre.

    `datos` es {año: _archivo(año)}; la máscara de fuentes fijas sale de los otros años.
    Devuelve los incendios y el número de focos que pasaron los filtros.
    """
    esp = zonas.espana()
    focos = [f for f in datos[anio][0] if esp.contains(Point(f["lon"], f["lat"]))]
    otras = [r for b in datos if b != anio for r in datos[b][1]]
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
        incs.append({"primera": min(f["t"] for f in fs), "ultima": max(f["t"] for f in fs),
                     "n": len(fs), "ha": zonas.ha_geo(g), "g": g})
    return incs, len(focos)


def emparejar(incs: list[dict], areas: list[dict]) -> list[int | None]:
    """Para cada área EFFIS, el incendio del vigía que la explica (el de más focos), o None."""
    arbol = STRtree([i["g"].buffer(config.EFFIS_HOLGURA_KM / 111) for i in incs])
    hol = timedelta(days=config.EFFIS_HOLGURA_DIAS)
    out = []
    for a in areas:
        fd = F._dt(a["firedate"])
        hit = None
        for k in arbol.query(shape(a["geometry"]), predicate="intersects"):
            i = incs[k]
            if F._dt(i["primera"]) - hol <= fd <= F._dt(i["ultima"]) + hol:
                if hit is None or i["n"] > incs[hit]["n"]:
                    hit = int(k)
        out.append(hit)
    return out


def contrastar(anios=(2023, 2024)) -> dict:
    datos = {a: _archivo(a) for a in anios}
    res = {}
    for a in anios:
        incs, n = incendios_archivo(a, datos)
        areas = effis.descargar(f"{a}-01-01", f"{a + 1}-01-01")
        res[a] = _medir(incs, areas)
        res[a]["focos"] = n
    return res


def _medir(incs: list[dict], areas: list[dict]) -> dict:
    usados = set()
    filas = []
    for a, hit in zip(areas, emparejar(incs, areas)):
        if hit is not None:
            usados.add(hit)
        filas.append({"area_ha": a["area_ha"], "hit": hit,
                      "retraso_h": F.horas_entre(a["firedate"], incs[hit]["primera"]) if hit is not None else None,
                      "ha_focos": incs[hit]["ha"] if hit is not None else None})

    out = {"effis_total": len(areas), "clases": []}
    for lo, hi in CLASES:
        fs = [f for f in filas if lo <= f["area_ha"] < hi]
        det = [f for f in fs if f["hit"] is not None]
        ret = np.array([f["retraso_h"] for f in det]) if det else np.zeros(0)
        out["clases"].append({
            "desde": lo, "hasta": hi if hi < 1e9 else None, "effis": len(fs), "detectados": len(det),
            "retraso_mediana_h": round(float(np.median(ret)), 1) if len(ret) else None,
            "antes_que_effis": int((ret <= 0).sum()),
            "ratio_ha_mediana": round(float(np.median([f["ha_focos"] / f["area_ha"] for f in det])), 2) if det else None,
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


def informe(res: dict) -> str:
    L = ["# Contraste con temporadas pasadas", "",
         "Reglas de la vigilancia aplicadas al archivo estándar de FIRMS (VIIRS S-NPP, NOAA-20 y "
         "MODIS) y comparadas con las áreas quemadas de EFFIS en España. Un incendio de EFFIS "
         "cuenta como detectado si su perímetro toca la huella de focos de un incendio del vigía "
         f"(con {config.EFFIS_HOLGURA_KM:g} km de margen) y su fecha cae dentro de las del incendio "
         f"(± {config.EFFIS_HOLGURA_DIAS} días). La máscara de fuentes fijas de cada año sale del otro año.", ""]
    for a, r in res.items():
        L += [f"## {a}", "", f"{r['focos']:,} focos tras los filtros; {r['vigia_total']:,} incendios del vigía; "
              f"{r['effis_total']:,} áreas EFFIS de cualquier tamaño.".replace(",", "."), "",
              "| Tamaño (EFFIS) | Incendios EFFIS | Detectados | Retraso mediano | Vistos antes que la fecha EFFIS | Superficie de focos / EFFIS (mediana) |",
              "|---|---:|---:|---:|---:|---:|"]
        for c in r["clases"]:
            t = f"{c['desde']}–{c['hasta']} ha" if c["hasta"] else f"≥ {c['desde']} ha"
            pct = f" ({100 * c['detectados'] / c['effis']:.0f} %)" if c["effis"] else ""
            ret = f"{c['retraso_mediana_h']:+.1f} h".replace(".", ",") if c["retraso_mediana_h"] is not None else "—"
            rat = f"{c['ratio_ha_mediana']:.2f}".replace(".", ",") if c["ratio_ha_mediana"] is not None else "—"
            L.append(f"| {t} | {c['effis']} | {c['detectados']}{pct} | {ret} | {c['antes_que_effis']} | {rat} |")
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


# ── Perímetros de Sentinel-2 frente a EFFIS ─────────────────────────────────────────────

UMBRALES = (0.10, 0.15, 0.20, 0.27)
ANCLAS_M = (750, 1500, 3000)


def _caso_perimetro(c: dict) -> dict | None:
    from odc.geo.geom import Geometry
    from rasterio import features
    from shapely.ops import unary_union
    from . import perimetro as P

    inc = c["inc"]
    t0, t1 = F._dt(inc["primera"]), F._dt(inc["ultima"])
    try:
        d = P.dnbr(inc["g"], t0, t1, t1 + timedelta(days=config.POST_DIAS))
    except Exception as e:                       # una escena rota no tumba la muestra
        return {"error": str(e)[:200], **{k: c[k] for k in ("anio", "effis_ha")}}
    if d is None:
        return {"sin_imagen": True, **{k: c[k] for k in ("anio", "effis_ha")}}
    ref = unary_union([shape(a["geometry"]) for a in c["areas"]])
    ef = features.rasterize([(Geometry(ref, "EPSG:4326").to_crs(d["crs"]).geom, 1)],
                            out_shape=d["gb"].shape, transform=d["gb"].affine, dtype="uint8").astype(bool)
    px = config.PERIMETRO_RES_M ** 2 / 10_000
    out = {"anio": c["anio"], "effis_ha": c["effis_ha"], "effis_ha_recorte": round(float(ef.sum()) * px, 1),
           "primera": inc["primera"], "centro": [round(inc["g"].centroid.x, 4), round(inc["g"].centroid.y, 4)],
           "post": d["post_fechas"], "combos": {}}
    # Con el compuesto del vigía (segundo NBR más bajo) y, para comparar, con el mínimo.
    for (capa, pref), u, m in product((("dnbr", ""), ("dnbr_min", "min|")), UMBRALES, ANCLAS_M):
        mk = P.recortar(d, u, m, capa)
        out["combos"][f"{pref}{u}|{m}"] = {"ha": round(float(mk.sum()) * px, 1),
                                           "iou": round(float((mk & ef).sum() / max((mk | ef).sum(), 1)), 3)}
    return out


def contrastar_perimetros(anios=(2023, 2024), por_clase: int = 25, hilos: int = 4) -> list[dict]:
    """Calcula el perímetro de Sentinel-2 de una muestra de incendios con perímetro EFFIS.

    Muestra estratificada por tamaño (30–100, 100–500 y ≥ 500 ha) y año, con semilla fija.
    """
    import random
    from concurrent.futures import ThreadPoolExecutor

    datos = {a: _archivo(a) for a in anios}
    casos = []
    for a in anios:
        incs, _ = incendios_archivo(a, datos)
        areas = effis.descargar(f"{a}-01-01", f"{a + 1}-01-01", 30)
        por_inc: dict[int, list[dict]] = {}
        for ar, h in zip(areas, emparejar(incs, areas)):
            if h is not None:
                por_inc.setdefault(h, []).append(ar)
        for h, ars in por_inc.items():
            casos.append({"anio": a, "inc": incs[h], "areas": ars,
                          "effis_ha": round(sum(x["area_ha"] for x in ars), 1)})
    rng = random.Random(2026)
    muestra = []
    for a in anios:
        for lo, hi in CLASES:
            grupo = [c for c in casos if c["anio"] == a and lo <= c["effis_ha"] < hi]
            muestra += rng.sample(grupo, min(por_clase, len(grupo)))
    # Cada caso se apunta en cuanto termina, para poder retomar una tanda cortada.
    parcial = config.DATA / "validacion_perimetro.jsonl"
    hechos = {}
    if parcial.exists():
        for linea in parcial.read_text(encoding="utf-8").splitlines():
            r = json.loads(linea)
            hechos[r["clave"]] = r
    for c in muestra:
        c["clave"] = f"{c['anio']}|{c['inc']['primera']}|{c['inc']['g'].centroid.x:.4f}"
    pendientes = [c for c in muestra if c["clave"] not in hechos]
    print(f"{len(muestra)} casos, {len(pendientes)} pendientes", flush=True)

    def uno(c):
        r = _caso_perimetro(c)
        if r is not None:
            r["clave"] = c["clave"]
            with parcial.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(r) + "\n")
            print(c["clave"], c["effis_ha"], "ha", flush=True)
        return r

    with ThreadPoolExecutor(hilos) as ex:
        list(ex.map(uno, pendientes))
    hechos = {}
    for linea in parcial.read_text(encoding="utf-8").splitlines():
        r = json.loads(linea)
        hechos[r["clave"]] = r
    return [hechos[c["clave"]] for c in muestra if c["clave"] in hechos]


def _clases_todos():
    for lo, hi in [(30, 1e9)] + CLASES:
        yield lo, hi, ("Todos" if (lo, hi) == (30, 1e9) else f"{lo}–{int(hi)} ha" if hi < 1e9 else f"≥ {lo} ha")


def resumen_perimetros(res: list[dict], umbral: float, ancla_m: int) -> dict:
    """Cifras por clase de tamaño para una combinación de umbral y anclaje."""
    clave = f"{umbral}|{ancla_m}"
    ok = [r for r in res if "combos" in r]
    clases = []
    for lo, hi, t in _clases_todos():
        grupo = [r for r in ok if lo <= r["effis_ha"] < hi]
        if not grupo:
            continue
        iou = np.array([r["combos"][clave]["iou"] for r in grupo])
        rat = [r["combos"][clave]["ha"] / r["effis_ha_recorte"] for r in grupo if r["effis_ha_recorte"]]
        clases.append({"clase": t, "n": len(grupo), "iou": float(np.median(iou)),
                       "buenos": float((iou >= 0.5).mean()), "ratio": float(np.median(rat))})
    return {"n": len(ok), "umbral": umbral, "ancla_m": ancla_m, "clases": clases}


def informe_perimetros(res: list[dict]) -> str:
    ok = [r for r in res if "combos" in r]
    elegida = f"{config.DNBR_UMBRAL}|{config.PERIMETRO_ANCLA_M}"
    L = ["# Superficie quemada con Sentinel-2 frente a EFFIS", "",
         f"Muestra de {len(res)} incendios de 2023 y 2024 con perímetro EFFIS, estratificada por "
         f"tamaño y año. {len(ok)} con imagen de antes y de después; "
         f"{sum(1 for r in res if r.get('sin_imagen'))} sin imagen útil y "
         f"{sum(1 for r in res if 'error' in r)} con error de lectura.", "",
         "IoU: superficie común entre el perímetro calculado y el de EFFIS dividida por la "
         "superficie de los dos juntos (1 es coincidencia exacta). Razón: hectáreas calculadas "
         "entre hectáreas de EFFIS.", "",
         f"En negrita, la combinación que usa el vigía (`DNBR_UMBRAL` y `PERIMETRO_ANCLA_M` en "
         f"[config.py](../vigia/config.py)).", "",
         "«Después del fuego» es cómo se resume cada píxel con las imágenes posteriores. El NBR "
         "mínimo y el segundo más bajo quedan casi iguales en esta muestra, que es de verano y con "
         "cielos limpios. El vigía usa el segundo más bajo porque fuera del verano una sombra de "
         "nube o una bruma que la máscara no detecta en una sola imagen basta para que el mínimo "
         "la cuente como quemada: en Campoo de Suso (octubre de 2026) daba 123 ha donde EFFIS "
         "cartografió 13. Exigir que lo vean dos imágenes cuesta un poco en los incendios grandes, "
         "que salen algo más cortos.", ""]
    for lo, hi, t in _clases_todos():
        grupo = [r for r in ok if lo <= r["effis_ha"] < hi]
        if not grupo:
            continue
        L += [f"## {t} ({len(grupo)} incendios)", "",
              "| Después del fuego | Umbral dNBR | Anclaje a los focos | IoU mediano | IoU ≥ 0,5 | Razón de superficie (mediana) |",
              "|---|---:|---:|---:|---:|---:|"]
        for clave in grupo[0]["combos"]:
            *capa, u, m = clave.split("|")
            iou = np.array([r["combos"][clave]["iou"] for r in grupo])
            rat = np.array([r["combos"][clave]["ha"] / r["effis_ha_recorte"] for r in grupo if r["effis_ha_recorte"]])
            dec = lambda x: f"{x:.2f}".replace(".", ",")
            miles = f"{int(m):,}".replace(",", ".")
            celdas = ["NBR mínimo" if capa else "2.º NBR más bajo", dec(float(u)), f"{miles} m", dec(np.median(iou)),
                      f"{100 * (iou >= 0.5).mean():.0f} %", dec(np.median(rat))]
            if clave == elegida:
                celdas = [f"**{c}**" for c in celdas]
            L.append("| " + " | ".join(celdas) + " |")
        L.append("")
    return "\n".join(L)


def main_perimetros(por_clase: int = 25) -> list[dict]:
    res = contrastar_perimetros(por_clase=por_clase)
    (config.DATA / "validacion_perimetro.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    (config.RAIZ / "docs" / "validacion_perimetro.md").write_text(informe_perimetros(res), encoding="utf-8")
    return res
