"""Per-fire analysis page: the fire replayed overpass by overpass.

For every fire of 100 ha or more whose perimeter changed at least once, the bot writes
`<site>/incendio/<id>.json` (canonical, language-independent data) and `<id>.html` (the page,
in the language of its country), plus one shared `ficha.js`.

- Timeline: every overpass with fire pixels (VIIRS or MODIS; satellites less than an hour apart
  are one overpass, as in perimeter._steps).
- Isochrones: the estimated perimeter after each VIIRS step, exactly as perimeter.track builds
  it, so the last isochrone is the perimeter on the map. MODIS overpasses light pixels but do
  not move the perimeter (1 km pixels would swamp it).
- Key moments: fixed rules over those numbers (see `momentos`), no model.

Historical fires (`data/historicos.json`) get the same page from the FIRMS standard archive,
so the method can be shown on fires that lasted days, like Landiras 2022.
"""
from __future__ import annotations

import csv
import json
import logging
import shutil
from collections import defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo

from shapely.geometry import box, mapping, shape

from . import config, focos as F, i18n, incendios as I, perimeter as P, zonas
from .config import Country
from .ficha_plantilla import FICHA_JS, PLANTILLA

log = logging.getLogger(__name__)

MIN_HA = 100            # smaller fires: one or two overpasses, nothing to replay
MIN_STEPS = 2           # perimeter steps: with one, there is no progression
HUECO_H = 18            # this long without fire pixels in the middle of a fire = observation gap
REACTIVACION_H = 24     # pixels again after this long = flare-up
SIMPLIFICAR = 0.0002    # ~20 m, as the perimeter on the main map
HISTORICOS = config.DATA / "historicos.json"


def elegible(i: dict) -> bool:
    return (i.get("perimeter_ha") or 0) >= MIN_HA and (i.get("steps") or 0) >= MIN_STEPS \
        and i.get("estado") != "unido"


# ── Data ────────────────────────────────────────────────────────────────────────────────

def pasadas(fs: list[dict]) -> list[list[dict]]:
    """All fire pixels grouped into overpasses (same rule as the perimeter steps)."""
    return P._steps(fs)


def datos(inc: dict, fs: list[dict], pais: Country) -> dict:
    """Everything the page draws, from the fire record and its pixels."""
    tr = P.track(fs)
    isos = tr["_isochrones"]
    grupos = pasadas(fs)
    filas, puntos = [], []
    j = -1
    for k, g in enumerate(grupos):
        t0, t1 = g[0]["t"], g[-1]["t"]
        while j + 1 < len(isos) and isos[j + 1][0]["t"] <= t1:
            j += 1
        viirs = any(f["sensor"] == "VIIRS" for f in g)
        fila = {"t": t0, "sats": sorted({f["sat"] for f in g}), "viirs": viirs, "n": len(g),
                "frp": round(sum(f["frp"] for f in g), 1), "iso": j}
        if k:
            fila["h"] = round(F.horas_entre(grupos[k - 1][-1]["t"], t0), 1)
        filas.append(fila)
        for f in g:
            puntos.append([round(f["lon"], 5), round(f["lat"], 5), k, round(f["frp"], 1),
                           round(f["scan"], 2), round(f["track"], 2)])
    iso_feats = []
    for k, (r, g) in enumerate(isos):
        iso_feats.append({"type": "Feature", "properties": {"k": k, "t": r["t"], "ha": r["ha"],
                                                           "front_km": r["front_km"]},
                          "geometry": zonas._redondear(mapping(g.simplify(SIMPLIFICAR)), 5)})
    final = isos[-1][1]
    per = inc.get("perimetro") or {}
    out = {
        "v": 1, "id": inc["id"], "pais": pais.code,
        "primera": inc["primera"], "ultima": inc["ultima"], "estado": inc.get("estado"),
        "centro": inc.get("centro"), "bbox": [round(v, 5) for v in final.bounds],
        "lugar": inc.get("lugar"),
        "perimeter_ha": tr["perimeter_ha"], "effis_ha": inc.get("effis_ha"),
        "s2": ({k: per[k] for k in ("ha", "definitivo", "nublado", "fecha_despues") if k in per}
               if per.get("ha") else None),
        "pasadas": filas,
        "isocronas": {"type": "FeatureCollection", "features": iso_feats},
        "focos": puntos,
        "natura": _natura(final, pais),
        "quemado_s2": (zonas._redondear(mapping(shape(per["geometry"]).simplify(SIMPLIFICAR)), 5)
                       if per.get("geometry") and per.get("ha") else None),
    }
    out["momentos"] = momentos(out, isos)
    return out


def _natura(g, pais: Country) -> dict:
    """Natura 2000 sites the final perimeter touches, cut to the fire's surroundings."""
    try:
        props, geoms, arbol = zonas.natura(pais)
    except FileNotFoundError:
        return {"type": "FeatureCollection", "features": []}
    marco = box(*g.buffer(0.03).bounds)
    feats = []
    for i in arbol.query(g, predicate="intersects"):
        recorte = geoms[i].intersection(marco).simplify(0.0005)
        if recorte.is_empty:
            continue
        p = props[i]
        feats.append({"type": "Feature", "geometry": zonas._redondear(mapping(recorte), 5),
                      "properties": {"codigo": p.get("codigo"), "nombre": p.get("nombre"), "tipo": p.get("tipo")}})
    return {"type": "FeatureCollection", "features": feats}


def momentos(d: dict, isos: list) -> list[dict]:
    """Key moments as canonical records {k (overpass), tipo, …}; the page words them.

    - inicio / ultimo: first and last overpass with pixels.
    - salto: the step where the perimeter grew most, with its hectares per hour.
    - potencia: the overpass with the highest total radiative power (FRP).
    - frente: the longest active front.
    - mitad / noventa: first step at 50 % and 90 % of the final perimeter.
    - natura: first step whose perimeter touches each Natura 2000 site.
    - hueco: HUECO_H hours or more without pixels between two overpasses (clouds, smoke, or
      no overpass): the fire may have grown unseen.
    - reactivacion: pixels again after REACTIVACION_H hours without them.
    - s2: the Sentinel-2 burnt area, when measured.
    """
    pas, feats = d["pasadas"], d["isocronas"]["features"]
    if not pas:
        return []
    k_de_iso = {}
    for k, p in enumerate(pas):
        k_de_iso.setdefault(p["iso"], k)
    out = [{"k": 0, "tipo": "inicio", "t": pas[0]["t"]}]
    ha = [f["properties"]["ha"] for f in feats]
    final = ha[-1] if ha else 0
    if len(ha) >= 2:
        crec = [(ha[j] - ha[j - 1], j) for j in range(1, len(ha))]
        dha, j = max(crec)
        if dha > 0:
            h = F.horas_entre(feats[j - 1]["properties"]["t"], feats[j]["properties"]["t"])
            out.append({"k": k_de_iso[j], "tipo": "salto", "ha": round(dha), "horas": round(h, 1),
                        "desde": feats[j - 1]["properties"]["t"]})
    kp = max(range(len(pas)), key=lambda k: pas[k]["frp"])
    out.append({"k": kp, "tipo": "potencia", "frp": round(pas[kp]["frp"])})
    if feats:
        jf = max(range(len(feats)), key=lambda j: feats[j]["properties"]["front_km"])
        if feats[jf]["properties"]["front_km"] > 0:
            out.append({"k": k_de_iso[jf], "tipo": "frente", "km": feats[jf]["properties"]["front_km"]})
    for frac, tipo in ((0.5, "mitad"), (0.9, "noventa")):
        j = next((j for j, v in enumerate(ha) if v >= frac * final), None)
        if j is not None and j > 0:
            out.append({"k": k_de_iso[j], "tipo": tipo, "ha": round(ha[j])})
    vistos = set()
    for f in d["natura"]["features"]:
        site = shape(f["geometry"])
        for j, (_, g) in enumerate(isos):
            if g.intersects(site):
                cod = f["properties"]["codigo"]
                if cod not in vistos:
                    vistos.add(cod)
                    pr = f["properties"]
                    out.append({"k": k_de_iso.get(j, 0), "tipo": "natura", "codigo": cod,
                                "nombre": pr["nombre"], "tipo_espacio": pr["tipo"]})
                break
    for k in range(1, len(pas)):
        h = pas[k].get("h") or 0
        if h >= REACTIVACION_H and k_de_iso.get(pas[k]["iso"]) == k and ha and \
                pas[k]["iso"] > 0 and ha[pas[k]["iso"]] - ha[pas[k]["iso"] - 1] >= 0.02 * final:
            out.append({"k": k, "tipo": "reactivacion", "horas": round(h)})
        elif h >= HUECO_H:
            out.append({"k": k, "tipo": "hueco", "horas": round(h)})
    if len(pas) > 1:
        out.append({"k": len(pas) - 1, "tipo": "ultimo", "t": pas[-1]["t"]})
    if d.get("s2"):
        out.append({"k": len(pas) - 1, "tipo": "s2", **d["s2"]})
    orden = ["inicio", "hueco", "reactivacion", "natura", "salto", "potencia", "frente", "mitad", "noventa",
             "ultimo", "s2"]
    return sorted(out, key=lambda m: (m["k"], orden.index(m["tipo"])))


# ── Page ────────────────────────────────────────────────────────────────────────────────

def _hora(t: str, pais: Country, lang: str) -> str:
    dt = datetime.strptime(t, "%Y-%m-%dT%H:%MZ").replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo(pais.tz))
    mes = i18n.FICHA[lang]["meses"][dt.month - 1]
    return f"{dt.day} {mes} {dt.year}, {dt:%H:%M}"


def texto_momento(m: dict, d: dict, pais: Country) -> str:
    """One key moment in words, in the language of the country (plain text)."""
    lang = pais.lang
    T = i18n.FICHA[lang]
    n = lambda v: i18n.n(v, lang)
    tipo = m["tipo"]
    if tipo == "salto":
        ha_h = m["ha"] / m["horas"] if m["horas"] >= 1 else None
        return T["m_salto"].format(ha=n(m["ha"]), horas=i18n.d(m["horas"], lang),
                                   ritmo=T["m_ritmo"].format(v=n(ha_h)) if ha_h else "")
    if tipo == "natura":
        return T["m_natura"].format(tipo=m.get("tipo_espacio") or "", nombre=m.get("nombre") or "",
                                    codigo=m.get("codigo") or "")
    if tipo == "s2":
        pre = T["al_menos"] if m.get("nublado") else ""
        return T["m_s2"].format(ha=pre + n(m["ha"]))
    vals = {"frp": n(m.get("frp", 0)), "km": i18n.d(m.get("km", 0), lang), "ha": n(m.get("ha", 0)),
            "horas": n(m.get("horas", 0))}
    return T[f"m_{tipo}"].format(**vals)


def _titulo(inc: dict, lang: str) -> str:
    l = inc.get("lugar") or {}
    sitio = l.get("municipio") or l.get("provincia") or i18n.FICHA[lang]["sin_nombre"]
    region = l.get("provincia") or l.get("departamento") or l.get("departement")
    if region and region != sitio:
        sitio += f" ({region})"
    return i18n.FICHA[lang]["titulo"].format(sitio=sitio)


def html(inc: dict, d: dict, pais: Country, plantilla_web: str, extra: dict | None = None) -> str:
    """The page of one fire. `plantilla_web` is web.PLANTILLA, for the shared footer."""
    from xml.sax.saxutils import escape
    from .logo import LOGO_SVG, favicon_link
    from .web import COMMON_CSS
    lang = pais.lang
    T = i18n.FICHA[lang]
    n = lambda v: i18n.n(v, lang)
    pas = d["pasadas"]
    titulo = (extra or {}).get("titulo") or _titulo(inc, lang)
    horas = F.horas_entre(pas[0]["t"], pas[-1]["t"])
    viirs = sum(p["viirs"] for p in pas)
    huecos = [p["h"] for p in pas[1:] if p.get("h")]
    mediana = sorted(huecos)[len(huecos) // 2] if huecos else None
    lis = "".join(
        f'<li data-k="{m["k"]}" class="m-{m["tipo"]}"><button type="button">'
        f'<time datetime="{pas[m["k"]]["t"]}">{escape(_hora(pas[m["k"]]["t"], pais, lang))}</time>'
        f'<span>{escape(texto_momento(m, d, pais))}</span></button></li>'
        for m in d["momentos"])
    cifras = [
        (n(d["perimeter_ha"]) + " ha", T["fig_perimetro"]),
        (n(len(pas)), T["fig_pasadas"].format(viirs=n(viirs))),
        (i18n.d(horas / 24, lang), T["fig_dias"]),
        ((i18n.d(mediana, lang) + " h") if mediana is not None else "—", T["fig_hueco"]),
    ]
    if d.get("s2"):
        cifras.insert(1, (("≥ " if d["s2"].get("nublado") else "") + n(d["s2"]["ha"]) + " ha", T["fig_s2"]))
    elif d.get("effis_ha"):
        cifras.insert(1, (n(d["effis_ha"]) + " ha", T["fig_effis"]))
    figs = "".join(f'<div><b>{escape(a)}</b><span>{escape(b)}</span></div>' for a, b in cifras)
    # The footer of the main page (principle, credits and sibling projects), so both stay in step.
    pie = plantilla_web[plantilla_web.index('<footer class="site-footer">'):plantilla_web.index("</footer>") + 9]
    pie = i18n.page(pie, lang).replace("</footer>", f'  <p class="nota">{T["creditos"]}</p>\n</footer>')
    nota = (extra or {}).get("nota")
    datos_url = f"{d['id']}.json"
    rep = {
        "__LANG__": lang,
        "__TITULO__": escape(titulo),
        "__DESCRIPCION__": escape(T["descripcion"].format(titulo=titulo)),
        "__FAVICON__": favicon_link("#c2410c", "#fb7b3e"),
        "__COMMON_CSS__": COMMON_CSS,
        "__LOGO__": LOGO_SVG,
        "__CIFRAS__": figs,
        "__NOTA__": f'<p class="aviso">{escape(nota)}</p>' if nota else "",
        "__MOMENTOS__": lis,
        "__PIE__": pie,
        "__CONFIG__": json.dumps({"datos": datos_url, "tz": pais.tz, "locale": T["locale"],
                                  "orto": ORTO[pais.code], "t": {k: v for k, v in T.items() if k.startswith("js_")}},
                                 ensure_ascii=False).replace("</", "<\\/"),
    }
    out = i18n.ficha_page(PLANTILLA, lang)
    for k, v in rep.items():
        out = out.replace(k, v)
    return out


# ── Writing ─────────────────────────────────────────────────────────────────────────────

def construir(incs: list[dict], todos: list[dict], pais: Country, plantilla_web: str) -> dict[str, str]:
    """Pages of the eligible fires among `incs` and of the country's historical fires, in
    <site>/incendio/. Returns {fire id: page path relative to the country's site}."""
    dest = pais.site / "incendio"
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    por_inc = defaultdict(list)
    for f in todos:
        if f.get("incendio"):
            por_inc[f["incendio"]].append(f)
    hechas = {}
    for inc in incs:
        if elegible(inc) and por_inc.get(inc["id"]):
            hechas[inc["id"]] = _escribir(dest, inc, por_inc[inc["id"]], pais, plantilla_web)
    for h in historicos(pais):
        hechas[h["id"]] = _escribir(dest, h["inc"], h["focos"], pais, plantilla_web, h)
    (dest / "ficha.js").write_text(FICHA_JS, encoding="utf-8")
    return hechas


def _escribir(dest, inc: dict, fs: list[dict], pais: Country, plantilla_web: str, extra: dict | None = None) -> str:
    d = datos(inc, fs, pais)
    (dest / f"{inc['id']}.json").write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":")),
                                            encoding="utf-8")
    (dest / f"{inc['id']}.html").write_text(html(inc, d, pais, plantilla_web, extra), encoding="utf-8")
    return f"incendio/{inc['id']}.html"


# ── Historical fires ────────────────────────────────────────────────────────────────────
# data/historicos.json lists them; each keeps its pixels in data/historicos/<id>.csv and its
# described record (place, land cover, Natura) in the list, so the hourly run never downloads.

def _hist_cargar() -> list[dict]:
    if not HISTORICOS.exists():
        return []
    return json.loads(HISTORICOS.read_text(encoding="utf-8"))["historicos"]


def historicos(pais: Country) -> list[dict]:
    out = []
    for h in _hist_cargar():
        if h["pais"] != pais.code:
            continue
        f = config.DATA / "historicos" / f"{h['id']}.csv"
        with f.open(encoding="utf-8") as fh:
            fs = [{**r, **{k: float(r[k]) for k in ("lat", "lon", "frp", "scan", "track")}}
                  for r in csv.DictReader(fh)]
        out.append({**h, "focos": fs})
    return out


def anadir_historico(id_: str, pais: Country, anio: int, bbox: tuple[float, float, float, float],
                     desde: str, hasta: str, titulo: str, nota: str = "") -> dict:
    """Pixels of one past fire from the FIRMS standard archive (S-NPP, NOAA-20 and MODIS; NOAA-21
    is not in the archive), grouped with the same rules; the largest group is the fire."""
    lon0, lat0, lon1, lat1 = bbox
    fs = []
    for prod, sensor in (("viirs-snpp", "VIIRS"), ("viirs-jpss1", "VIIRS"), ("modis", "MODIS")):
        for r in zonas.archivo_firms(prod, anio, pais.firms_country):
            if not (desde <= r["acq_date"] <= hasta):
                continue
            if not (lat0 < float(r["latitude"]) < lat1 and lon0 < float(r["longitude"]) < lon1):
                continue
            f = F.normalizar(r, sensor)
            if f:
                fs.append(f)
    fs = F.sin_fijas(sorted(fs, key=lambda f: f["t"]), pais)
    if not fs:
        raise ValueError("no fire pixels in that box and dates")
    grupos = I.agrupar(fs)
    mayor = max(set(grupos.tolist()), key=lambda g: (grupos == g).sum())
    fs = [f for f, g in zip(fs, grupos) if g == mayor]
    for f in fs:
        f["incendio"] = id_
    inc = {"id": id_, "estado": "inactivo"}
    I.describir(inc, fs, pais, detalle=True)
    I.guardar_cache()
    for k in ("geometry", "perimeter", "front"):
        inc.pop(k, None)
    destino = config.DATA / "historicos"
    destino.mkdir(exist_ok=True)
    with (destino / f"{id_}.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=F.CAMPOS)
        w.writeheader()
        w.writerows(fs)
    lista = [h for h in _hist_cargar() if h["id"] != id_]
    lista.append({"id": id_, "pais": pais.code, "titulo": titulo, "nota": nota,
                  "fuente": {"anio": anio, "bbox": list(bbox), "desde": desde, "hasta": hasta}, "inc": inc})
    HISTORICOS.write_text(json.dumps({"historicos": sorted(lista, key=lambda h: h["id"])}, ensure_ascii=False,
                                     indent=1), encoding="utf-8")
    return inc


# Orthophoto per country: tiles URL and attribution (same services as the main map).
ORTO = {
    "ES": ["https://www.ign.es/wmts/pnoa-ma?service=WMTS&request=GetTile&version=1.0.0&format=image/jpeg"
           "&layer=OI.OrthoimageCoverage&style=default&tilematrixset=GoogleMapsCompatible&tilematrix={z}"
           "&tilerow={y}&tilecol={x}", "PNOA © scne.es"],
    "FR": ["https://data.geopf.fr/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=ORTHOIMAGERY.ORTHOPHOTOS"
           "&STYLE=normal&TILEMATRIXSET=PM&FORMAT=image/jpeg&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}", "© IGN"],
}
