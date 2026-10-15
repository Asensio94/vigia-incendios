"""Validación en Francia: las temporadas de 2022 (Gironde y Landes) y 2025 (Aude).

Las mismas reglas que en España, aplicadas al archivo estándar de FIRMS de Francia, y dos
referencias: las áreas quemadas de EFFIS, como en España, y BDIFF, el registro oficial de
incendios forestales de Francia. BDIFF no trae contornos: un incendio de BDIFF cuenta como
detectado si la huella de focos de un incendio del vigía toca su commune (con el mismo
margen que con EFFIS) y la primera alerta cae entre las fechas del incendio, con la misma
holgura. Como BDIFF da la hora de la primera alerta, el retraso se mide contra ella.

La máscara de fuentes fijas de cada año sale del otro año, como en España.
"""
from __future__ import annotations

import json
from datetime import timedelta
from functools import lru_cache

import numpy as np
import requests
from shapely import STRtree
from shapely.geometry import shape
from shapely.ops import unary_union

from . import bdiff, config, effis, focos as F, validacion as V
from .i18n import d as _d, n as _n

PAIS = config.FR
ANIOS = (2022, 2025)
# Incendios que se citan uno a uno en el informe: los mayores de cada temporada.
DESTACADOS_HA = 1000
# Missed large fires, explained by hand after checking the watch's own fires around them.
NOTAS = {
    2022: "La reprise de Landiras d'août (6 743 ha) n'est pas un oubli de la veille : elle l'a suivie "
          "comme un seul feu de 1 742 foyers du 9 au 13 août, mais à une quinzaine de kilomètres de "
          "la commune de Landiras, à laquelle BDIFF rattache le feu. Sans contour, le croisement par "
          "commune ne peut pas les relier.",
}


@lru_cache(None)
def contorno_commune(insee: str):
    """Contorno de una commune, también de las delegadas que BDIFF aún usa tras una fusión."""
    try:
        r = requests.get(config.GEO_API_GOUV, headers=config.UA, timeout=60, params={
            "code": insee, "type": "commune-actuelle,commune-deleguee,commune-associee",
            "format": "geojson", "geometry": "contour"})
        r.raise_for_status()
        feats = [f for f in r.json().get("features", []) if f.get("geometry")]
    except (requests.RequestException, ValueError):
        return None
    return unary_union([shape(f["geometry"]) for f in feats]) if feats else None


def emparejar_bdiff(incs: list[dict], fuegos: list[dict]) -> list[int | None]:
    """Para cada incendio de BDIFF, el del vigía (el de más focos) que toca su commune en fecha."""
    arbol = STRtree([i["g"].buffer(config.EFFIS_HOLGURA_KM / 111) for i in incs])
    hol = timedelta(days=config.EFFIS_HOLGURA_DIAS)
    out = []
    for f in fuegos:
        g = contorno_commune(f["insee"])
        if g is None:
            out.append(None)
            continue
        t = F._dt(f["alerta"])
        hit = None
        for k in arbol.query(g, predicate="intersects"):
            i = incs[k]
            if F._dt(i["primera"]) - hol <= t <= F._dt(i["ultima"]) + hol:
                if hit is None or i["n"] > incs[hit]["n"]:
                    hit = int(k)
        out.append(hit)
    return out


def medir_bdiff(incs: list[dict], fuegos: list[dict]) -> dict:
    grandes = [f for f in fuegos if f["ha"] >= V.CLASES[0][0]]
    sin_commune = [f for f in grandes if contorno_commune(f["insee"]) is None]
    grandes = [f for f in grandes if f not in sin_commune]
    hits = emparejar_bdiff(incs, grandes)
    filas = []
    for f, h in zip(grandes, hits):
        fila = {**{k: f[k] for k in ("insee", "commune", "departement", "alerta", "ha", "precision")},
                "detectado": h is not None}
        if h is not None:
            i = incs[h]
            fila.update(retraso_h=round(F.horas_entre(f["alerta"], i["primera"]), 1), focos=i["n"],
                        ha_focos=round(i["ha"], 1))
        filas.append(fila)
    clases = []
    for lo, hi in V.CLASES:
        fs = [f for f in filas if lo <= f["ha"] < hi]
        det = [f for f in fs if f["detectado"]]
        ret = np.array([f["retraso_h"] for f in det])
        clases.append({"desde": lo, "hasta": hi if hi < 1e9 else None, "bdiff": len(fs), "detectados": len(det),
                       "retraso_mediana_h": round(float(np.median(ret)), 1) if len(ret) else None,
                       "medidas": sum(f["precision"].lower().startswith("mesur") for f in fs)})
    return {"bdiff_total": len(fuegos), "bdiff_30ha": len(grandes) + len(sin_commune),
            "sin_commune": len(sin_commune), "clases": clases,
            "destacados": sorted((f for f in filas if f["ha"] >= DESTACADOS_HA), key=lambda f: -f["ha"])}


def contrastar(anios=ANIOS) -> dict:
    datos = {a: V._archivo(a, PAIS) for a in anios}
    res = {}
    for a in anios:
        incs, n = V.incendios_archivo(a, datos, PAIS)
        areas = effis.descargar(f"{a}-01-01", f"{a + 1}-01-01", pais=PAIS.code)
        r = V._medir(incs, areas)
        r["focos"] = n
        r["bdiff"] = medir_bdiff(incs, bdiff.descargar(a))
        res[a] = r
    return res


# ── Informe (en francés: lo enlaza la página de Francia) ───────────────────────────────

def _h(x: float | None) -> str:
    return "—" if x is None else ("+" if x >= 0 else "−") + _d(abs(x), "fr") + " h"


def _cl(c: dict) -> str:
    return f"{c['desde']}–{c['hasta']} ha" if c["hasta"] else f"≥ {c['desde']} ha"


def _pc(a: int, b: int) -> str:
    return f" ({100 * a / b:.0f} %)" if b else ""


def informe(res: dict, perimetros: list[dict] | None = None) -> str:
    hk, hd = config.EFFIS_HOLGURA_KM, config.EFFIS_HOLGURA_DIAS
    L = ["# Validation en France : saisons 2022 et 2025", "",
         "Les règles de la veille, appliquées à l'archive standard de FIRMS pour la France "
         "métropolitaine (VIIRS S-NPP, NOAA-20 et MODIS), comparées à deux références :", "",
         "- **EFFIS** (Copernicus), les surfaces brûlées cartographiées par satélite, comme en Espagne. "
         f"Un feu EFFIS est détecté si son contour touche l'empreinte des foyers d'un feu de la veille "
         f"(avec {_d(hk, 'fr')} km de marge) et si sa date tombe dans celles du feu (± {hd} jours).",
         "- **BDIFF**, la base de données officielle des incendies de forêt en France (ministère de "
         "l'Agriculture, Licence Ouverte 2.0), qui reprend aussi les feux de Prométhée. Elle ne donne "
         "pas de contour : un feu BDIFF est détecté si l'empreinte d'un feu de la veille touche sa "
         f"commune (avec {_d(hk, 'fr')} km de marge) et si la première alerte tombe dans ses dates "
         f"(± {hd} jours). Le retard est mesuré depuis l'heure de la première alerte.", "",
         "Le masque des sources fixes de chaque année vient de l'autre année, pour ne pas utiliser "
         "d'information qu'on n'aurait pas en temps réel.", ""]
    for a, r in res.items():
        b = r["bdiff"]
        L += [f"## {a}", "",
              f"{_n(r['focos'], 'fr')} foyers après les filtres ; {_n(r['vigia_total'], 'fr')} feux de la veille ; "
              f"{_n(r['effis_total'], 'fr')} surfaces EFFIS ; {_n(b['bdiff_total'], 'fr')} feux BDIFF, dont "
              f"{_n(b['bdiff_30ha'], 'fr')} de 30 ha ou plus"
              + (f" ({b['sin_commune']} sans commune retrouvée, écartés)" if b["sin_commune"] else "") + ".", "",
              "### Face à EFFIS", "",
              "| Taille (EFFIS) | Feux EFFIS | Détectés | Retard médian sur la date EFFIS | Vus avant la date EFFIS |",
              "|---|---:|---:|---:|---:|"]
        for c in r["clases"]:
            L.append(f"| {_cl(c)} | {c['effis']} | {c['detectados']}{_pc(c['detectados'], c['effis'])} | "
                     f"{_h(c['retraso_mediana_h'])} | {c['antes_que_effis']} |")
        L += ["", "### Face à BDIFF", "",
              "| Surface parcourue (BDIFF) | Feux BDIFF | dont surfaces mesurées | Détectés | Retard médian sur la première alerte |",
              "|---|---:|---:|---:|---:|"]
        for c in b["clases"]:
            L.append(f"| {_cl(c)} | {c['bdiff']} | {c['medidas']} | {c['detectados']}{_pc(c['detectados'], c['bdiff'])} | "
                     f"{_h(c['retraso_mediana_h'])} |")
        if b["destacados"]:
            L += ["", f"Feux BDIFF de {_n(DESTACADOS_HA, 'fr')} ha ou plus :", "",
                  "| Commune (INSEE) | Première alerte (UTC) | Surface BDIFF | Détecté | Retard | Foyers |",
                  "|---|---|---:|---|---:|---:|"]
            for f in b["destacados"]:
                L.append(f"| {f['commune']} ({f['insee']}) | {f['alerta'][:16].replace('T', ' ')} | "
                         f"{_n(f['ha'], 'fr')} ha | {'oui' if f['detectado'] else 'non'} | "
                         f"{_h(f.get('retraso_h'))} | {f.get('focos', '—')} |")
        if int(a) in NOTAS:
            L += ["", NOTAS[int(a)]]
        L.append("")
    if perimetros:
        v = V.resumen_perimetros(perimetros, config.DNBR_UMBRAL, config.PERIMETRO_ANCLA_M)
        L += ["## Surface brûlée Sentinel-2 face à EFFIS", "",
              f"Échantillon de {len(perimetros)} feux de 2022 et 2025 avec contour EFFIS, stratifié par taille "
              f"et par année ; {v['n']} avec une image avant et après. Mêmes réglages qu'en Espagne "
              f"(dNBR > {_d(config.DNBR_UMBRAL, 'fr', 2)}, à moins de {_n(config.PERIMETRO_ANCLA_M, 'fr')} m des foyers). "
              "IoU : surface commune divisée par la surface des deux réunis (1 = même contour).", "",
              "| Taille (EFFIS) | Feux | IoU médian | IoU ≥ 0,5 | Surface / EFFIS (médiane) |", "|---|---:|---:|---:|---:|"]
        for c in v["clases"]:
            clase = "Tous" if c["clase"] == "Todos" else c["clase"]
            L.append(f"| {clase} | {c['n']} | {_d(c['iou'], 'fr', 2)} | {100 * c['buenos']:.0f} % | "
                     f"{_d(c['ratio'], 'fr', 2)} |")
        L.append("")
    return "\n".join(L)


def _perimetros() -> list[dict] | None:
    f = PAIS.data / "validacion_perimetro.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None


def main() -> dict:
    res = contrastar()
    (PAIS.data / "validacion.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    escribir_informe(res)
    return res


def escribir_informe(res: dict | None = None) -> None:
    if res is None:
        res = json.loads((PAIS.data / "validacion.json").read_text(encoding="utf-8"))
    (config.RAIZ / "docs" / "validation_fr.md").write_text(informe(res, _perimetros()), encoding="utf-8")


def main_perimetros(por_clase: int = 10) -> list[dict]:
    res = V.contrastar_perimetros(ANIOS, por_clase=por_clase, pais=PAIS)
    (PAIS.data / "validacion_perimetro.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    escribir_informe()
    return res
