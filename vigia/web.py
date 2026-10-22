"""Web estática: mapa, fichas de incendios, fuente Atom y GeoJSON descargable."""
from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape

from shapely.geometry import shape

from . import config, ficha, focos as F, i18n, incendios as I, signals, zonas
from .config import Country
from .logo import LOGO_SVG, favicon_link

TEMPORADA_DIAS = 120
# Shared stylesheet of the sibling projects, copied verbatim and inlined into the page.
COMMON_CSS = (Path(__file__).with_name("common.css")).read_text(encoding="utf-8").strip()


def relevante(i: dict) -> bool:
    """Lo que no es un foco aislado: tres focos o más, perímetro EFFIS o Red Natura."""
    return i.get("n_focos", 0) >= 3 or bool(i.get("effis")) or bool(i.get("natura"))


def _ligero(i: dict) -> dict:
    claves = ("id", "estado", "primera", "ultima", "n_focos", "pasadas", "satelites", "frp_max",
              "ha_focos", "centro", "lugar", "cobertura", "natura", "effis", "effis_ha", "unidos",
              "perimeter_ha", "front_km", "front_t", "max_growth_ha_h")
    out = {k: i[k] for k in claves if i.get(k) is not None}
    if i.get("progression"):
        out["progression"] = [[r["t"], r["ha"]] for r in i["progression"]]
    out["tipo"] = I.tipo(i)
    out["relevante"] = relevante(i)
    if i.get("perimetro"):
        out["s2"] = s2_ligero(i["perimetro"])
    return out


def s2_ligero(per: dict) -> dict:
    """El perímetro de Sentinel-2 sin la geometría ni las claves internas."""
    return {k: v for k, v in per.items() if k not in ("geometry", "clave", "revisado")}


def _quemado(incs: list[dict], simplificar: float = 0) -> dict:
    feats = []
    for i in incs:
        per = i.get("perimetro") or {}
        if not per.get("geometry"):
            continue
        g = per["geometry"]
        if simplificar:
            g = zonas._redondear(shape(g).simplify(simplificar).__geo_interface__, 5)
        feats.append({"type": "Feature", "geometry": g,
                      "properties": {"incendio": i["id"], "ha": per["ha"], "severidad": per["severidad"],
                                     "imagenes": per["imagenes"], "definitivo": per["definitivo"],
                                     "nublado": bool(per.get("nublado")), "una_imagen": per.get("una_imagen"),
                                     "fecha_antes": per.get("fecha_antes"), "fecha_despues": per.get("fecha_despues")}})
    return {"type": "FeatureCollection", "features": feats}


def construir(reg: dict, todos: list[dict], areas: list[dict], pais: Country) -> list[dict]:
    """Web de un país en pais.site; devuelve sus incendios vivos para signals.json."""
    ahora = reg["actualizado"]
    lang = pais.lang
    desde = F.hace(TEMPORADA_DIAS * 24, F._dt(ahora))
    vivos = [i for i in reg["incendios"] if i.get("estado") != "unido" and i.get("ultima")]
    visibles = [i for i in vivos if i["estado"] in ("activo", "reciente")
                or (relevante(i) and i["ultima"] >= desde)]
    fichas = ficha.construir(visibles, todos, pais, PLANTILLA)
    feats = [{"type": "Feature", "geometry": _forma(i),
              "properties": {**_ligero(i), **({"ficha": fichas[i["id"]]} if i["id"] in fichas else {})}}
             for i in visibles]
    frentes = [{"type": "Feature", "geometry": i["front"], "properties": {"id": i["id"], "t": i["front_t"]}}
               for i in visibles if i["estado"] == "activo" and i.get("front")]

    hace7 = F.hace(config.RECIENTE_DIAS * 24, F._dt(ahora))
    sats = sorted({f["sat"] for f in todos})
    puntos = [[f["lat"], f["lon"], f["t"], sats.index(f["sat"]), round(f["frp"], 1), f["incendio"]]
              for f in todos if f["t"] >= hace7]
    ids_effis = {e["id"] for i in visibles for e in i.get("effis", [])}
    perimetros = [{"type": "Feature", "properties": {k: a[k] for k in ("id", "firedate", "area_ha")},
                   "geometry": zonas._redondear(shape(a["geometry"]).simplify(0.0003).__geo_interface__, 5)}
                  for a in areas if a["id"] in ids_effis]

    activos = [i for i in vivos if i["estado"] == "activo"]
    datos = {
        "incendios": {"type": "FeatureCollection", "features": feats},
        "focos": puntos, "sats": sats,
        "effis": {"type": "FeatureCollection", "features": perimetros},
        "frentes": {"type": "FeatureCollection", "features": frentes},
        "s2": _quemado(visibles, 0.0002),
        "redir": {i["id"]: i["unido_en"] for i in reg["incendios"] if i.get("unido_en")},
        "estados": I.ESTADOS if lang == "es" else i18n.ESTADOS_FR,
        "grupos": I.GRUPOS_CLC if lang == "es" else i18n.GRUPOS_FR,
        "ahora": ahora, "ultima_pasada": max((f["t"] for f in todos), default=None),
        "temporada_dias": TEMPORADA_DIAS,
    }
    fv = pais.data / "validacion.json"
    validacion = json.loads(fv.read_text(encoding="utf-8")) if fv.exists() else {}
    vista = f"[{pais.map_view[0]},{pais.map_view[1]}],{pais.map_view[2]}"
    html = (i18n.page(PLANTILLA, lang)
            .replace("__LOGO__", LOGO_SVG)
            .replace("__FAVICON__", favicon_link("#c2410c", "#fb7b3e"))
            .replace("__COMMON_CSS__", COMMON_CSS)
            .replace("__TABS_CSS__", ficha.TABS_CSS)
            .replace("__TABS__", ficha.tabs(lang, "mapa", ""))
            .replace("__ACTIVOS__", str(sum(relevante(i) for i in activos)))
            .replace("__AISLADOS__", str(sum(not relevante(i) for i in activos)))
            .replace("__NATURA__", str(sum(bool(i.get("natura")) for i in activos if relevante(i))))
            .replace("__FOCOS24__", str(sum(f["t"] >= F.hace(24, F._dt(ahora)) for f in todos)))
            .replace("__TEMPORADA__", str(TEMPORADA_DIAS))
            .replace("__VISTA__", vista)
            .replace("__METODO__", _parametros(lang) + _ejemplos(pais, fichas))
            .replace("__VALIDACION__", _validacion(validacion, lang))
            .replace("__VALIDACION_S2__", _validacion_s2(pais))
            .replace("__DATOS__", json.dumps(datos, ensure_ascii=False, separators=(",", ":"))
                     .replace("</", "<\\/")))

    site = pais.site
    site.mkdir(parents=True, exist_ok=True)
    (site / "index.html").write_text(html, encoding="utf-8")
    shutil.copy(zonas.natura_web_path(pais), site / "natura.geojson")
    todos_gj = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "geometry": _forma(i),
         "properties": {**{k: v for k, v in i.items() if k not in ("geometry", "perimeter", "front", "perimetro")},
                        **({"perimetro_s2": s2_ligero(i["perimetro"])} if i.get("perimetro") else {})}}
        for i in vivos]}
    (site / "incendios.geojson").write_text(json.dumps(todos_gj, ensure_ascii=False), encoding="utf-8")
    (site / "quemado.geojson").write_text(json.dumps(_quemado(vivos), ensure_ascii=False), encoding="utf-8")
    (site / "feed.xml").write_text(_feed(vivos, ahora, pais), encoding="utf-8")
    return vivos


def _ejemplos(pais: Country, fichas: dict[str, str]) -> str:
    """Links to the historical fires replayed overpass by overpass (method section)."""
    hs = [h for h in ficha.historicos(pais) if h["id"] in fichas]
    if not hs:
        return ""
    T = i18n.FICHA[pais.lang]
    hs = sorted(hs, key=lambda h: -(h["inc"].get("perimeter_ha") or 0))[:3]
    enlaces = ", ".join(f'<a href="{fichas[h["id"]]}">{h["titulo"]}</a>' for h in hs)
    return f"<p>{T['ejemplos'].format(enlaces=enlaces)}</p>"


def escribir_signals(vivos: dict[str, list[dict]], ahora: str) -> None:
    """The fires of every country in the sibling projects' common format, for Estado de las
    IBA: one file at the root of the site."""
    config.SITE.mkdir(exist_ok=True)
    todos = [i for incs in vivos.values() for i in incs]
    (config.SITE / "signals.json").write_text(json.dumps(signals.document(todos, ahora), ensure_ascii=False),
                                              encoding="utf-8")
    (config.SITE / ".nojekyll").write_text("")


def _forma(i: dict) -> dict:
    """Perimeter when there is one (three VIIRS pixels or more), else the pixel footprint."""
    return i.get("perimeter") or i["geometry"]


def _titulo(i: dict, lang: str = "es") -> str:
    l = i.get("lugar") or {}
    sitio = l.get("municipio") or l.get("provincia") or ("lugar sin nombre" if lang == "es" else "lieu sans nom")
    if l.get("provincia") and l.get("provincia") != sitio:
        sitio += f" ({l['provincia']})"
    if lang == "fr":
        return ("Incendie à " if relevante(i) else "Foyer isolé à ") + sitio
    return ("Incendio en " if relevante(i) else "Foco aislado en ") + sitio


def _resumen(i: dict) -> str:
    nat = ", ".join(f"{e['tipo']} {e['nombre']}" for e in i.get("natura", [])[:3])
    return (f"{i['n_focos']} focos en {i['pasadas']} pasadas, del {i['primera']} al {i['ultima']} (UTC). "
            f"Píxeles con focos: {i['ha_focos']:g} ha."
            + (f" Perímetro estimado: {i['perimeter_ha']:g} ha; frente activo de {i['front_km']:g} km"
               f" en la última pasada." if i.get("perimeter_ha") else "")
            + f" Arde sobre: {I.tipo(i)}."
            + (f" Red Natura: {nat}." if nat else "")
            + (f" Superficie quemada estimada con Sentinel-2: {'al menos ' if i['perimetro'].get('nublado') else ''}{i['perimetro']['ha']:g} ha"
               f"{'' if i['perimetro'].get('definitivo') else ' (provisional)'}"
               f"{', medida con una sola imagen' if i['perimetro'].get('una_imagen', 0) > 0.5 else ''}."
               if (i.get("perimetro") or {}).get("ha") else "")
            + (f" Perímetro EFFIS: {i['effis_ha']:g} ha." if i.get("effis_ha") else ""))


def _resumen_fr(i: dict) -> str:
    fr = "fr"
    nat = ", ".join(f"{e['tipo']} {e['nombre']}" for e in i.get("natura", [])[:3])
    per = i.get("perimetro") or {}
    return (f"{i18n.n(i['n_focos'], fr)} foyers en {i18n.n(i['pasadas'], fr)} passages, du {i['primera']} au "
            f"{i['ultima']} (UTC). Pixels avec foyers : {i18n.d(i['ha_focos'], fr)} ha."
            + (f" Périmètre estimé : {i18n.d(i['perimeter_ha'], fr)} ha ; front actif de "
               f"{i18n.d(i['front_km'], fr)} km au dernier passage." if i.get("perimeter_ha") else "")
            + f" Brûle sur : {i18n.TIPOS_FR.get(I.tipo(i), I.tipo(i))}."
            + (f" Natura 2000 : {nat}." if nat else "")
            + (f" Surface brûlée estimée avec Sentinel-2 : {'au moins ' if per.get('nublado') else ''}"
               f"{i18n.d(per['ha'], fr)} ha{'' if per.get('definitivo') else ' (provisoire)'}"
               f"{', mesurée avec une seule image' if per.get('una_imagen', 0) > 0.5 else ''}." if per.get("ha") else "")
            + (f" Contour EFFIS : {i18n.d(i['effis_ha'], fr)} ha." if i.get("effis_ha") else ""))


def _feed(vivos: list[dict], ahora: str, pais: Country = config.ES) -> str:
    lang, web = pais.lang, pais.web
    rel = sorted((i for i in vivos if relevante(i) and i["ultima"] >= F.hace(7 * 24, F._dt(ahora))),
                 key=lambda i: i["ultima"], reverse=True)[:60]
    ent = []
    for i in rel:
        resumen = _resumen_fr(i) if lang == "fr" else _resumen(i)
        ent.append(f"""<entry><id>{web}#{i['id']}</id><title>{escape(_titulo(i, lang))}</title>
<link href="{web}#{i['id']}"/><updated>{i['ultima'][:16]}:00Z</updated>
<summary>{escape(resumen)}</summary></entry>""")
    nombre = "Vigie des incendies" if lang == "fr" else "Vigía de incendios"
    return f"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"><title>{nombre}</title>
<id>{web}</id><link href="{web}"/><link rel="self" href="{web}feed.xml"/>
<updated>{ahora[:16]}:00Z</updated><author><name>{nombre}</name></author>
{chr(10).join(ent)}
</feed>
"""


def _es(x: float, decimales: int | None = None) -> str:
    """Número a la española: 1.500 y 0,15 (con `decimales`, fijos: 0,70)."""
    ent, _, dec = (f"{x:g}" if decimales is None else f"{x:.{decimales}f}").partition(".")
    ent = f"{int(ent):,}".replace(",", ".")
    return f"{ent},{dec}" if dec else ent


def _filas_es() -> list[tuple[str, str]]:
    return [
        ("Satélites", "VIIRS en S-NPP, NOAA-20 y NOAA-21 (píxel de 375 m) y MODIS en Terra y Aqua (1 km), vía NASA FIRMS"),
        ("Confianza mínima", f"VIIRS nominal o alta; MODIS {config.MODIS_CONFIANZA_MIN} sobre 100"),
        ("Fuentes fijas", f"fuera los focos a menos de {config.FIJAS_RADIO_KM:g} km de un punto marcado como fuente fija por FIRMS en {config.FIJAS_ANIOS[0]}–{config.FIJAS_ANIOS[-1]}".replace(".", ",")),
        ("Mismo incendio", f"píxeles a menos de {config.ENLACE_KM:g} km (más si son píxeles grandes) y vistos con menos de {config.ENLACE_HORAS} h de diferencia, en cadena".replace(".", ",")),
        ("Foco aislado", "uno o dos focos, sin perímetro EFFIS ni Red Natura"),
        ("Activo", f"algún foco en las últimas {config.ACTIVO_HORAS} h"),
        ("Qué arde", f"CORINE Land Cover 2018 en hasta {config.CLC_MUESTRAS} celdas con focos; vegetación natural si bosque, matorral, dehesa y roquedo suman la mitad"),
        ("Perímetro EFFIS", f"área quemada que toca la huella (con {config.EFFIS_HOLGURA_KM:g} km de margen) y empezó entre {config.EFFIS_HOLGURA_DIAS} días antes del primer foco y {config.EFFIS_HOLGURA_DIAS} días después del último"),
        ("Perímetro estimado", f"con {config.PERIMETER_MIN_VIIRS} píxeles VIIRS o más: cada píxel es un disco de {config.PIXEL_RADIUS_FACTOR:g} veces medio píxel de radio; tras cada pasada se suma a lo anterior y se cierran los huecos de menos de {2 * config.CLOSING_KM:g} km, así que nunca encoge (como FEDS, de la NASA)".replace(".", ",")),
        ("Frente activo", f"borde del perímetro a menos de {config.FRONT_KM * 1000:g} m de un píxel de la última pasada"),
        ("Quemado (Sentinel-2)", f"dNBR mayor que {_es(config.DNBR_UMBRAL)}, a {config.PERIMETRO_RES_M} m, en manchas que tocan los focos y a menos de {_es(config.PERIMETRO_ANCLA_M)} m de ellos; antes, mediana de hasta {config.PRE_ESCENAS_MAX} escenas de los {config.PRE_DIAS} días previos; después, el segundo NBR más bajo (el más bajo si solo hay una imagen) desde el primer foco hasta {config.POST_ESCENAS_TRAS} escenas tras el último"),
        ("Severidad", "dNBR hasta 0,27 baja; de 0,27 a 0,66 moderada; más de 0,66 alta (Key y Benson, simplificado)"),
        ("Frecuencia", "cada hora; FIRMS publica los focos unas tres horas después de la pasada"),
        ("Horas", "peninsulares; en Canarias, una hora menos"),
    ]


def _filas_fr() -> list[tuple[str, str]]:
    def g(x: float) -> str:          # like :g, with a decimal comma and French thousands
        return i18n.d(x, "fr", 0) if float(x).is_integer() else f"{x:g}".replace(".", ",")
    return [
        ("Satellites", "VIIRS sur S-NPP, NOAA-20 et NOAA-21 (pixel de 375 m) et MODIS sur Terra et Aqua (1 km), via NASA FIRMS"),
        ("Confiance minimale", f"VIIRS nominale ou haute ; MODIS {config.MODIS_CONFIANZA_MIN} sur 100"),
        ("Sources fixes", f"foyers écartés à moins de {g(config.FIJAS_RADIO_KM)} km d’un point marqué comme source fixe par FIRMS en {config.FIJAS_ANIOS[0]}–{config.FIJAS_ANIOS[-1]}"),
        ("Même incendie", f"pixels à moins de {g(config.ENLACE_KM)} km (davantage pour les grands pixels) et vus à moins de {config.ENLACE_HORAS} h d’intervalle, en chaîne"),
        ("Foyer isolé", "un ou deux foyers, sans contour EFFIS ni Natura 2000"),
        ("Actif", f"au moins un foyer ces dernières {config.ACTIVO_HORAS} h"),
        ("Ce qui brûle", f"CORINE Land Cover 2018 dans jusqu’à {config.CLC_MUESTRAS} cellules avec foyers ; végétation naturelle si forêt, landes, mosaïque agroforestière et roches font la moitié"),
        ("Contour EFFIS", f"surface brûlée qui touche l’empreinte (avec {g(config.EFFIS_HOLGURA_KM)} km de marge) et a commencé entre {config.EFFIS_HOLGURA_DIAS} jours avant le premier foyer et {config.EFFIS_HOLGURA_DIAS} jours après le dernier"),
        ("Périmètre estimé", f"à partir de {config.PERIMETER_MIN_VIIRS} pixels VIIRS : chaque pixel est un disque de {g(config.PIXEL_RADIUS_FACTOR)} fois le demi-pixel de rayon ; après chaque passage il s’ajoute au précédent et les trous de moins de {g(2 * config.CLOSING_KM)} km sont fermés, donc il ne rétrécit jamais (comme FEDS, de la NASA)"),
        ("Front actif", f"bord du périmètre à moins de {g(config.FRONT_KM * 1000)} m d’un pixel du dernier passage"),
        ("Brûlé (Sentinel-2)", f"dNBR supérieur à {g(config.DNBR_UMBRAL)}, à {config.PERIMETRO_RES_M} m, en taches qui touchent les foyers et à moins de {i18n.n(config.PERIMETRO_ANCLA_M, 'fr')} m d’eux ; avant, médiane d’au plus {config.PRE_ESCENAS_MAX} scènes des {config.PRE_DIAS} jours précédents ; après, le deuxième NBR le plus bas (le plus bas s’il n’y a qu’une image) du premier foyer à {config.POST_ESCENAS_TRAS} scènes après le dernier"),
        ("Sévérité", "dNBR jusqu’à 0,27 faible ; de 0,27 à 0,66 modérée ; au-delà de 0,66 élevée (Key et Benson, simplifié)"),
        ("Fréquence", "toutes les heures ; FIRMS publie les foyers environ trois heures après le passage"),
        ("Heures", "heure de Paris"),
        ("Communes", "commune où tombe le centre des foyers, avec son code INSEE (API Découpage administratif) ; le département et la région entre parenthèses"),
    ]


def _parametros(lang: str = "es") -> str:
    filas = _filas_fr() if lang == "fr" else _filas_es()
    return '<table class="params">' + "".join(
        f"<tr><th>{escape(a)}</th><td>{escape(b)}</td></tr>" for a, b in filas) + "</table>"


def _clase(c: dict, lang: str) -> str:
    if lang == "fr":
        return f"{c['desde']}–{i18n.n(c['hasta'], 'fr')} ha" if c["hasta"] else f"≥ {i18n.n(c['desde'], 'fr')} ha"
    return f"{c['desde']}–{c['hasta']} ha" if c["hasta"] else f"≥ {c['desde']} ha"


def _validacion(v: dict, lang: str = "es") -> str:
    if not v:
        return ""
    if lang == "fr":
        return _validacion_fr(v)
    filas = []
    for anio, r in v.items():
        for c in r["clases"]:
            t = _clase(c, lang)
            pct = round(100 * c["detectados"] / c["effis"]) if c["effis"] else 0
            filas.append(f"<tr><td>{anio}</td><td>{t}</td><td class='dato'>{c['detectados']} de {c['effis']}</td>"
                         f"<td class='dato'>{pct} %</td></tr>")
    return ('<table class="params valid"><tr><th>Año</th><th>Tamaño según EFFIS</th><th>Detectados</th><th></th></tr>'
            + "".join(filas) + "</table>")


def _horas_fr(x: float | None) -> str:
    return "—" if x is None else ("+" if x >= 0 else "−") + i18n.d(abs(x), "fr") + " h"


def _validacion_fr(v: dict) -> str:
    """Two tables, as in docs/validation_fr.md: against EFFIS and against BDIFF, plus the
    largest fires of each season one by one."""
    fr = "fr"
    pc = lambda a, b: i18n.p(a / b, fr) if b else "—"
    effis, bdiff, grandes = [], [], []
    for anio, r in v.items():
        for c in r["clases"]:
            effis.append(f"<tr><td>{anio}</td><td>{_clase(c, fr)}</td><td class='dato'>{c['detectados']} sur {c['effis']}</td>"
                         f"<td class='dato'>{pc(c['detectados'], c['effis'])}</td></tr>")
        b = r.get("bdiff") or {}
        for c in b.get("clases", []):
            bdiff.append(f"<tr><td>{anio}</td><td>{_clase(c, fr)}</td><td class='dato'>{c['detectados']} sur {c['bdiff']}</td>"
                         f"<td class='dato'>{pc(c['detectados'], c['bdiff'])}</td>"
                         f"<td class='dato'>{_horas_fr(c['retraso_mediana_h'])}</td></tr>")
        for f in b.get("destacados", []):
            grandes.append(f"<tr><td>{escape(f['commune'])} <span class='dato'>({escape(f['departement'])})</span></td>"
                           f"<td>{anio}</td><td class='dato'>{i18n.n(f['ha'], fr)} ha</td>"
                           f"<td>{'oui' if f['detectado'] else 'non'}</td><td class='dato'>{_horas_fr(f.get('retraso_h'))}</td></tr>")
    out = ('<p>Face à EFFIS :</p><table class="params valid"><tr><th>Année</th><th>Taille selon EFFIS</th>'
           "<th>Détectés</th><th></th></tr>" + "".join(effis) + "</table>")
    if bdiff:
        out += ('<p>Face à BDIFF, avec le retard médian de la vigie sur la première alerte (négatif : le satellite '
                "l’a vu avant l’alerte, à l’heure près du passage) :</p>"
                '<table class="params valid"><tr><th>Année</th><th>Surface parcourue selon BDIFF</th><th>Détectés</th>'
                "<th></th><th>Retard médian</th></tr>" + "".join(bdiff) + "</table>")
    if grandes:
        out += (f"<p>Les feux de {i18n.n(1000, fr)} ha ou plus selon BDIFF, un par un :</p>"
                '<table class="params valid"><tr><th>Commune (département)</th><th>Année</th><th>Surface BDIFF</th>'
                "<th>Vu</th><th>Retard</th></tr>" + "".join(grandes) + "</table>")
        from .validacion_fr import NOTAS
        out += "".join(f"<p>{escape(NOTAS[int(a)])}</p>" for a in v if int(a) in NOTAS)
    return out


def _validacion_s2(pais: Country = config.ES) -> str:
    f = pais.data / "validacion_perimetro.json"
    if not f.exists():
        return ""
    from .validacion import resumen_perimetros
    v = resumen_perimetros(json.loads(f.read_text(encoding="utf-8")), config.DNBR_UMBRAL, config.PERIMETRO_ANCLA_M)
    if pais.lang == "fr":
        filas = "".join(
            f"<tr><td>{'Tous' if c['clase'] == 'Todos' else c['clase']}</td><td class='dato'>{c['n']}</td>"
            f"<td class='dato'>{i18n.d(c['iou'], 'fr', 2)}</td><td class='dato'>{i18n.p(c['buenos'], 'fr')}</td>"
            f"<td class='dato'>{i18n.d(c['ratio'], 'fr', 2)}</td></tr>" for c in v["clases"])
        return (f'<h3>Le brûlé selon Sentinel-2 face à EFFIS</h3><p>Échantillon de {v["n"]} feux de 2022 et 2025 '
                "avec contour EFFIS. La concordance est la surface commune divisée par la réunion des deux (1 s’ils "
                "sont identiques) ; au-dessus de 0,5 les deux contours racontent la même histoire.</p>"
                '<table class="params valid"><tr><th>Taille selon EFFIS</th><th>Feux</th><th>Concordance médiane</th>'
                "<th>Concordance ≥ 0,5</th><th>Surface face à EFFIS</th></tr>" + filas + "</table>")
    filas = "".join(
        f"<tr><td>{c['clase']}</td><td class='dato'>{c['n']}</td><td class='dato'>{_es(c['iou'], 2)}</td>"
        f"<td class='dato'>{round(100 * c['buenos'])} %</td><td class='dato'>{_es(c['ratio'], 2)}</td></tr>"
        for c in v["clases"])
    return (f'<h3>Lo quemado según Sentinel-2 frente a EFFIS</h3><p>Muestra de {v["n"]} incendios de 2023 y 2024 '
            'con perímetro EFFIS. La coincidencia es el área común dividida por la unión de los dos (1 si son '
            'idénticos); por encima de 0,5 los dos perímetros cuentan la misma historia.</p>'
            '<table class="params valid"><tr><th>Tamaño según EFFIS</th><th>Incendios</th><th>Coincidencia mediana</th>'
            '<th>Con coincidencia ≥ 0,5</th><th>Superficie frente a EFFIS</th></tr>' + filas + "</table>")


PLANTILLA = r"""<!doctype html>
@@lang@@
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
__FAVICON__
@@project_title@@
<meta name="description" content="@@meta_description@@">
<link rel="alternate" type="application/atom+xml" @@project_feed@@ href="feed.xml">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='6' fill='%23221d1a'/%3E%3Cpath d='M16 5c1 5 7 7 7 14a7 7 0 0 1-14 0c0-4 2-6 4-8 0 3 1 5 3 5-1-4 0-8 0-11z' fill='%23f06a2b'/%3E%3C/svg%3E">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;600;700&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css">
<style>
__COMMON_CSS__
:root{--accent:#c2410c;--accent-dark:#fb7b3e}
/* Spanish tokens point at the common ones; map and state colours stay here. */
:root{
  --suelo:var(--ground); --papel:var(--paper); --tinta:var(--ink); --gris:var(--muted); --linea:var(--line);
  --brasa:var(--accent); --sombra:var(--shadow);
  --activo:#d0310f; --reciente:#a8660a; --inactivo:#857a72;
  --natura-f:rgba(47,122,85,.10); --effis:#6b3fa0;
  --quemado:#6e2a12; --sev-baja:#e3b48c; --sev-mod:#b5582b; --sev-alta:#4f1a0b;
  --f6:#b0140a; --f24:#e8590c; --f72:#f2a33a; --fviejo:#a99d94;
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    --activo:#ff6b45; --reciente:#e8a547; --inactivo:#8f847c;
    --natura-f:rgba(98,184,138,.12); --effis:#b08ce0;
    --quemado:#e9804e; --sev-baja:#6b4a37; --sev-mod:#b8612f; --sev-alta:#ff9a66;
    --f6:#ff4d3a; --f24:#ff8a3d; --f72:#f5c26b; --fviejo:#6f655e;
  }
}
:root[data-theme="dark"]{
  --activo:#ff6b45; --reciente:#e8a547; --inactivo:#8f847c;
  --natura-f:rgba(98,184,138,.12); --effis:#b08ce0;
  --quemado:#e9804e; --sev-baja:#6b4a37; --sev-mod:#b8612f; --sev-alta:#ff9a66;
  --f6:#ff4d3a; --f24:#ff8a3d; --f72:#f5c26b; --fviejo:#6f655e;
}
html{-webkit-text-size-adjust:100%}
.rotulo{font-family:var(--font-title);text-transform:uppercase;letter-spacing:.08em;font-weight:600}
.dato{font-family:var(--font-data);font-variant-numeric:tabular-nums}
.marca{display:flex;align-items:baseline;gap:14px;flex-wrap:wrap}
.marca .rotulo{color:var(--gris);font-size:14px}
.marca .pais{margin-left:auto;font-size:14px}
__TABS_CSS__
.site-header .lede{text-wrap:pretty}
.figures .vivo b{color:var(--activo)}
.figures .meta b{font-size:17px;line-height:1.75}
main{max-width:1440px;margin:0 auto;padding:0 16px;display:grid;grid-template-columns:minmax(0,1.35fr) minmax(360px,1fr);gap:18px;align-items:start}
.mapa-caja{position:sticky;top:12px;display:grid;gap:6px}
#mapa{height:calc(100vh - 60px);min-height:420px;border:1px solid var(--linea);background:var(--papel)}
.leyenda{display:flex;flex-wrap:wrap;gap:4px 14px;font-size:12.5px;color:var(--gris);align-items:center}
.leyenda i{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:5px;vertical-align:-1px}
.leyenda i.cuadro{border-radius:0;background:transparent!important;border:2px solid}
.lista{display:grid;gap:14px;padding-bottom:40px}
.filtros{display:flex;flex-wrap:wrap;gap:8px 14px;align-items:center;padding:10px 0;border-bottom:1px solid var(--linea);position:sticky;top:0;background:var(--suelo);z-index:5}
.filtros label{font-size:13px;color:var(--gris);display:flex;gap:6px;align-items:center}
.filtros select{max-width:min(240px,62vw);font:14px var(--font-text);background:var(--papel);color:var(--tinta);border:1px solid var(--linea);padding:4px 6px}
.filtros input{accent-color:var(--brasa)}
.cuenta{margin-left:auto;font-size:13px;color:var(--gris)}
.ficha{background:var(--papel);border:1px solid var(--linea);box-shadow:var(--sombra);padding:14px 16px 16px;display:grid;gap:9px;scroll-margin-top:60px}
.ficha.sel{border-color:var(--brasa);box-shadow:0 0 0 1px var(--brasa),var(--sombra)}
.ficha header{display:flex;flex-wrap:wrap;gap:6px 10px;align-items:center}
.ficha h2{margin:0;font:600 22px/1.15 var(--font-title);letter-spacing:.01em;flex:1 1 100%;text-wrap:balance}
.id{font-size:12px;color:var(--gris)}
.sello{font:600 12px/1 var(--font-title);text-transform:uppercase;letter-spacing:.09em;padding:4px 7px 3px;border:1.5px solid currentColor}
.sello.activo{color:var(--activo);background:color-mix(in srgb,var(--activo) 10%,transparent)}
.sello.reciente{color:var(--reciente)} .sello.inactivo{color:var(--inactivo)}
.sello.natura{color:var(--natura)} .sello.effis{color:var(--effis)}
.cuando{margin:0;font-size:15px;color:var(--gris)}
.cuando strong{color:var(--tinta);font-weight:600}
dl.medidas{margin:0;display:grid;grid-template-columns:repeat(auto-fit,minmax(118px,1fr));gap:8px 12px}
dl.medidas div{display:grid;gap:1px}
dl.medidas dt{font-size:11.5px;color:var(--gris)}
dl.medidas dd{margin:0;font:500 15px var(--font-data);font-variant-numeric:tabular-nums}
.barra{display:flex;height:8px;background:var(--linea);overflow:hidden}
.barra span{display:block;height:100%}
.reparto{display:grid;gap:4px;font-size:13.5px}
.progresion{margin:0;color:var(--activo)}
.progresion svg{width:100%;max-width:300px;height:56px;display:block}
.progresion figcaption{font-size:12.5px;color:var(--gris)}
.reparto p{margin:0;color:var(--gris)}
.espacios{margin:0;padding:0;list-style:none;display:grid;gap:3px;font-size:14.5px}
.espacios li{padding-left:10px;border-left:2px solid var(--natura)}
.espacios .dato{font-size:12px;color:var(--gris)}
.nota{font-size:13.5px;color:var(--gris);margin:0}
.quemado{display:grid;gap:5px;font-size:14px;padding:8px 0 2px;border-top:1px solid var(--linea)}
.quemado p{margin:0}
.quemado .cifra-q{font:600 15px "IBM Plex Mono",monospace;font-variant-numeric:tabular-nums}
.sev{display:flex;flex-wrap:wrap;gap:2px 12px;font-size:12.5px;color:var(--gris)}
.sev i{display:inline-block;width:9px;height:9px;margin-right:4px;vertical-align:-1px}
.leyenda i.relleno{background:color-mix(in srgb,var(--quemado) 35%,transparent)!important;border-color:var(--quemado)}
.acciones{display:flex;flex-wrap:wrap;gap:6px 16px;font-size:14px}
.acciones button{font:inherit;background:none;border:0;padding:0;color:inherit;text-decoration:underline;text-decoration-color:var(--brasa);text-underline-offset:3px;cursor:pointer}
.vacio{padding:28px 16px;border:1px dashed var(--linea);color:var(--gris);text-align:center}
.method{margin-top:24px;padding-bottom:40px;border-top:1.5px solid var(--tinta);display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:28px}
.method p{margin:0 0 10px}
.method ol{margin:0 0 10px;padding-left:1.4em}
.method ol li{margin-bottom:8px}
.method > div > h3:first-child{margin-top:0}
.aviso{border-left:3px solid var(--brasa);padding:2px 0 2px 12px}
.method table.params th{white-space:normal;width:34%}
.method table.valid th{width:auto}
.site-footer p{margin:0}
.leaflet-container{background:var(--papel);font:13px var(--font-text)}
.leaflet-control-layers,.leaflet-bar a{background:var(--papel);color:var(--tinta)}
.leaflet-popup-content-wrapper,.leaflet-popup-tip{background:var(--papel);color:var(--tinta)}
@media (max-width: 900px){
  main{grid-template-columns:1fr}
  .mapa-caja{position:relative;top:0}
  #mapa{height:56vh}
  .method{grid-template-columns:1fr}
  .filtros{position:static}
}
@media (max-width: 560px){
  .figures{display:grid;grid-template-columns:1fr 1fr;column-gap:12px}
  .figures .meta{grid-column:1/-1}
}
@media (prefers-reduced-motion: reduce){*{scroll-behavior:auto!important}}
</style>
</head>
<body>
<header class="site-header">
  <div class="marca">
    <h1>__LOGO__@@h1@@</h1>
    @@tagline@@@@switch@@
  </div>
  __TABS__
  <p class="lede">@@lede@@</p>
  <div class="figures">
    <div class="vivo"><b>__ACTIVOS__</b>@@fig_active@@</div>
    <div><b>__NATURA__</b>@@fig_natura@@</div>
    <div><b>__AISLADOS__</b>@@fig_isolated@@</div>
    <div><b>__FOCOS24__</b>@@fig_focos24@@</div>
    <div class="meta"><b class="dato" id="pasada">—</b>@@fig_last@@<span id="actualizado"></span></span></div>
  </div>
</header>

<main>
  <div class="mapa-caja">
    <div id="mapa" role="region" @@map_aria@@></div>
    <div class="leyenda" @@legend_aria@@>
@@legend@@
    </div>
  </div>
  <div class="lista">
    <div class="filtros">
@@filters@@
      <span class="cuenta" id="cuenta" aria-live="polite"></span>
    </div>
    <div id="fichas"></div>
  </div>
</main>

<section class="method" id="metodo">
  <div>
    @@method_title@@
    <ol>
@@steps@@
    </ol>
    @@params_title@@
    __METODO__
  </div>
  <div>
    @@s2_section@@
    @@val_title@@
    @@val_intro@@
    __VALIDACION__
    @@val_note@@
    __VALIDACION_S2__
    @@caveats@@@@extra@@
    @@species@@
    @@open_data@@
  </div>
</section>

<footer class="site-footer">
  <p class="principle">@@principle@@</p>
  @@credits@@
  @@siblings@@
</footer>

<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>
<script>
const D = __DATOS__;
const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const esc = s => String(s??"").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const num = (x,d=0) => x==null ? "—" : x.toLocaleString(@@locale@@,{minimumFractionDigits:d,maximumFractionDigits:d});
const ms = t => Date.parse(t.replace("Z",":00Z"));
const AHORA = ms(D.ahora);
const fmt = new Intl.DateTimeFormat(@@locale@@,{timeZone:@@tz@@,day:"numeric",month:"short",hour:"2-digit",minute:"2-digit"});
const hora = t => fmt.format(new Date(ms(t)));
const hace = t => { const h = (AHORA-ms(t))/36e5; return @@js_ago@@; };

document.getElementById("pasada").textContent = D.ultima_pasada ? hora(D.ultima_pasada) : "—";
document.getElementById("actualizado").textContent = @@js_updated@@;

const todas = D.incendios.features;
const tipos = {}; for (const f of todas) tipos[f.properties.tipo] = (tipos[f.properties.tipo]||0)+1;
for (const t of ["vegetación natural","mixto","cultivos","suelo urbano o industrial","sin datos"]) if (tipos[t])
  document.getElementById("f-tipo").insertAdjacentHTML("beforeend",`<option value="${t}">${@@js_tipo_label@@}</option>`);

// ── Mapa ──
const mapa = L.map("mapa",{zoomControl:true}).setView(__VISTA__);
const osm = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",{maxZoom:19,attribution:"© OpenStreetMap"}).addTo(mapa);
@@js_ortho@@
const capaNatura = L.geoJSON(null,{style:()=>({color:css("--natura"),weight:1,fillColor:css("--natura"),fillOpacity:.10}),
  onEachFeature:(f,l)=>l.bindTooltip(`${esc(f.properties.tipo)} · ${esc(f.properties.nombre)}`,{sticky:true})});
let naturaCargada = false;
mapa.on("overlayadd", e => { if (e.layer===capaNatura && !naturaCargada){ naturaCargada = true;
  fetch("natura.geojson").then(r=>r.json()).then(g=>{capaNatura.addData(g); capaNatura.bringToBack();}); }});
const capaS2 = L.geoJSON(D.s2,{style:()=>({color:css("--quemado"),weight:1,fillColor:css("--quemado"),fillOpacity:.35}),
  onEachFeature:(f,l)=>l.bindTooltip(`@@js_s2_tip@@`,{sticky:true})}).addTo(mapa);
const capaEffis = L.geoJSON(D.effis,{style:()=>({color:css("--effis"),weight:1.5,dashArray:"4 3",fill:false})}).addTo(mapa);
const capaFrentes = L.geoJSON(D.frentes,{style:()=>({color:css("--activo"),weight:4,opacity:.9}),
  onEachFeature:(f,l)=>l.bindTooltip(`@@js_front_tip@@${hora(f.properties.t)}`,{sticky:true})}).addTo(mapa);
const capaFocos = L.layerGroup().addTo(mapa);
const capaHuellas = L.layerGroup().addTo(mapa);
L.control.layers(@@js_layers@@,{collapsed:true}).addTo(mapa);

const colorEdad = t => { const h=(AHORA-ms(t))/36e5; return css(h<6?"--f6":h<24?"--f24":h<72?"--f72":"--fviejo"); };
const colorEstado = e => css(e==="activo"?"--activo":e==="reciente"?"--reciente":"--inactivo");
const capas = {};
for (const f of todas){
  const p = f.properties;
  capas[p.id] = L.geoJSON(f,{style:()=>({color:colorEstado(p.estado),weight:1.5,fillOpacity:.12})})
    .on("click",()=>{ tocado=true; seleccionar(p.id,false); });
}
const visibles = new Set();
function pintarFocos(){
  capaFocos.clearLayers();
  for (const [la,lo,t,s,frp,inc] of D.focos){
    if (inc && !visibles.has(inc)) continue;
    L.circleMarker([la,lo],{radius:3.5,weight:0,fillOpacity:.9,fillColor:colorEdad(t)})
      .bindTooltip(`${hora(t)} · ${esc(D.sats[s])} · ${num(frp,1)} MW`).addTo(capaFocos);
  }
}

// ── Fichas ──
const titulo = p => { const l=p.lugar||{}; @@js_title@@ };
const COLG = {bosque:"#3f7a3a",matorral:"#8a9a3c",agroforestal:"#b59b45",desnudo:"#9b8c7e",agricola:"#d8b55b",artificial:"#7b6f86",agua:"#3f7fb0"};
// Superficie del perímetro tras cada pasada: una escalera, porque solo cambia cuando pasa un satélite.
function progresion(p){
  const r = p.progression||[]; if (r.length<3) return "";
  const t0=ms(r[0][0]), t1=Math.max(ms(r[r.length-1][0]),t0+1), hmax=Math.max(...r.map(x=>x[1]));
  const X=t=>4+292*(ms(t)-t0)/(t1-t0), Y=h=>52-48*h/hmax;
  let d=`M${X(r[0][0]).toFixed(1)},${Y(r[0][1]).toFixed(1)}`;
  for (const [t,h] of r.slice(1)) d+=`H${X(t).toFixed(1)}V${Y(h).toFixed(1)}`;
  return `<figure class="progresion"><svg viewBox="0 0 300 56" role="img" @@js_prog_aria@@>
    <path d="${d}" fill="none" stroke="currentColor" stroke-width="1.5"/></svg>
    <figcaption>@@js_prog_caption@@</figcaption></figure>`;
}
function ficha(p){
  const reparto = p.cobertura && Object.keys(p.cobertura).length ? `<div class="reparto">
    <div class="barra" role="img" @@js_cover_aria@@>${Object.entries(p.cobertura).map(([k,v])=>`<span style="width:${v*100}%;background:${COLG[k]||"#999"}" title="${esc(D.grupos[k])}"></span>`).join("")}</div>
    @@js_burns_on@@${Object.entries(p.cobertura).map(([k,v])=>`${esc(D.grupos[k])} ${Math.round(v*100)} %`).join(", ")} <span class="dato">(CORINE 2018)</span></p></div>` : "";
  // Espacios Natura: los que tocan los focos y los que toca lo quemado, con las hectáreas
  // quemadas de cada uno cuando ya hay perímetro de Sentinel-2.
  const nub = p.s2?.nublado;
  const q = p.s2 && p.s2.ha!=null && !(nub && !p.s2.ha) ? Object.fromEntries((p.s2.natura||[]).map(e=>[e.codigo,e])) : null;
  const espacios = [...(p.natura||[])];
  for (const e of (p.s2?.natura||[])) if (!espacios.some(x=>x.codigo===e.codigo)) espacios.push(e);
  if (q) espacios.sort((a,b)=>(q[b.codigo]?.ha||0)-(q[a.codigo]?.ha||0));
  const enNat = e => @@js_in_natura@@;
  const nat = espacios.length ? `<ul class="espacios">${espacios.slice(0,4).map(e=>`<li>${esc(e.tipo)} <strong>${esc(e.nombre)}</strong> <span class="dato">${esc(e.codigo)} · ${enNat(e)}</span></li>`).join("")}</ul>${espacios.length>4?`<p class="nota">@@js_more_sites@@</p>`:""}` : "";
  const s2 = bloqueS2(p);
  const ef = p.effis_ha!=null ? @@js_effis@@ : "";
  const un = (p.unidos||[]).length ? `<p class="nota">@@js_merged@@ (${p.unidos.map(esc).join(", ")}).</p>` : "";
  const d0 = p.primera.slice(0,10), d1 = p.ultima.slice(0,10);
  const firms = `https://firms.modaps.eosdis.nasa.gov/map/#d:${d0}..${d1};@${p.centro[0]},${p.centro[1]},12.0z`;
  return `<article class="ficha" id="${esc(p.id)}">
    <header>
      <h2>${esc(titulo(p))}</h2>
      <span class="sello ${p.estado}">${esc(D.estados[p.estado])}</span>
      ${(p.natura||[]).length ? `@@js_seal_natura@@` : ""}
      ${p.effis_ha!=null ? `@@js_seal_effis@@` : ""}
      <span class="id dato">${esc(p.id)}</span>
    </header>
    <p class="cuando">@@js_when@@${hora(p.ultima)}</strong>, ${hace(p.ultima)}</p>
    <dl class="medidas">
      <div>@@js_dt_focos@@<dd>${num(p.n_focos)}</dd></div>
      <div>@@js_dt_passes@@<dd>${num(p.pasadas)}</dd></div>
      <div>@@js_dt_pixels@@<dd>${num(p.ha_focos)} ha</dd></div>
      ${p.perimeter_ha!=null ? `<div>@@js_dt_perimeter@@<dd>${num(p.perimeter_ha)} ha</dd></div>` : ""}
      ${p.estado==="activo" && p.front_km ? `<div>@@js_dt_front@@<dd>${num(p.front_km,1)} km</dd></div>` : ""}
      ${p.max_growth_ha_h ? `<div>@@js_dt_growth@@<dd>${num(p.max_growth_ha_h)} ha/h</dd></div>` : ""}
      ${p.s2?.ha ? `<div>@@js_dt_s2@@<dd>${p.s2.nublado?"≥ ":""}${num(p.s2.ha)} ha</dd></div>` : ""}
      <div>@@js_dt_frp@@<dd>${num(p.frp_max)} MW</dd></div>
    </dl>
    ${progresion(p)}
    ${reparto}${nat}${s2}${ef}${un}
    <div class="acciones"><button type="button" data-zoom="${esc(p.id)}"@@js_actions@@</div>
  </article>`;
}

const fdia = new Intl.DateTimeFormat(@@locale@@,{day:"numeric",month:"short"});
const dia = d => fdia.format(new Date(d+"T12:00:00Z"));
// Copernicus Browser en el compuesto de infrarrojo de onda corta (B12-B8A-B4), donde lo
// quemado sale granate y la vegetación verde: cualquiera puede comprobar la cifra con sus ojos.
const urlCB = (f, p) => "https://browser.dataspace.copernicus.eu/?" + new URLSearchParams({zoom:14,
  lat:p.centro[1].toFixed(5), lng:p.centro[0].toFixed(5), themeId:"MONITORING", datasetId:"S2_L2A_CDAS",
  layerId:"6-SWIR", fromTime:`${f}T00:00:00.000Z`, toTime:`${f}T23:59:59.999Z`, dateMode:"SINGLE"});
const verCB = (s, p) => s.fecha_antes && s.fecha_despues && p.centro ? `<p class="nota ver">@@js_check@@</p>` : "";
function bloqueS2(p){
  const s = p.s2;
  if (!s) return "";
  if (s.sin_imagen) return `<div class="quemado"><p class="nota">@@js_s2_none@@</p></div>`;
  const ult = `${s.imagenes.length} @@js_s2_images@@${dia(s.imagenes.at(-1))}`;
  if (s.nublado && !s.ha) return `<div class="quemado"><p class="nota">@@js_s2_cloudy@@</p>${verCB(s,p)}</div>`;
  if (!s.ha) return `<div class="quemado"><p class="nota">@@js_s2_nothing@@</p>${verCB(s,p)}</div>`;
  const sev = @@js_sev@@;
  const tot = Object.values(s.severidad).reduce((a,b)=>a+b,0) || 1;
  return `<div class="quemado">
    <p>@@js_s2_area@@</p>
    <div class="barra" role="img" @@js_sev_aria@@>${sev.map(([k,c])=>`<span style="width:${100*s.severidad[k]/tot}%;background:var(${c})"></span>`).join("")}</div>
    <div class="sev">${sev.map(([k,c])=>`<span><i style="background:var(${c})"></i>@@js_sev_label@@</span>`).join("")}</div>
    <p class="nota">@@js_s2_notes@@</p>
    ${verCB(s,p)}
  </div>`;
}

function filtrar(){
  const per = document.getElementById("f-periodo").value, tp = document.getElementById("f-tipo").value;
  const sn = document.getElementById("f-natura").checked, ais = document.getElementById("f-aislados").checked;
  const ok = todas.filter(f=>{ const p=f.properties;
    if (per==="activo" && p.estado!=="activo") return false;
    if (per==="semana" && p.estado==="inactivo") return false;
    if (tp && p.tipo!==tp) return false;
    if (sn && !(p.natura||[]).length) return false;
    if (!ais && !p.relevante) return false;
    return true; });
  const orden = {activo:0,reciente:1,inactivo:2};
  ok.sort((a,b)=> orden[a.properties.estado]-orden[b.properties.estado] || (b.properties.relevante-a.properties.relevante) || b.properties.ultima.localeCompare(a.properties.ultima));
  capaHuellas.clearLayers(); visibles.clear();
  for (const f of ok){ capas[f.properties.id].addTo(capaHuellas); visibles.add(f.properties.id); }
  pintarFocos();
  document.getElementById("fichas").innerHTML = ok.length ? ok.map(f=>ficha(f.properties)).join("")
    : `<p class="vacio">@@js_empty@@</p>`;
  document.getElementById("cuenta").textContent = @@js_count@@;
}

function seleccionar(id, zoom, animar=true){
  document.querySelectorAll(".ficha.sel").forEach(e=>e.classList.remove("sel"));
  const el = document.getElementById(id);
  if (el){ el.classList.add("sel"); if(!zoom) el.scrollIntoView({block:"start"}); }
  if (zoom && capas[id]) mapa.fitBounds(capas[id].getBounds(),{maxZoom:13,padding:[40,40],animate:animar});
  history.replaceState(null,"","#"+id);
}

document.getElementById("fichas").addEventListener("click",e=>{
  const b = e.target.closest("[data-zoom]"); if (b){ tocado = true; seleccionar(b.dataset.zoom,true); }
});
for (const id of ["f-periodo","f-tipo","f-natura","f-aislados"]) document.getElementById(id).addEventListener("change",filtrar);

// Al abrir un enlace a un incendio, se amplían los filtros hasta que aparezca; un enlace a
// un incendio que se unió a otro lleva al superviviente.
let h = decodeURIComponent(location.hash.slice(1)), tocado = false;
if (D.redir[h]) { h = D.redir[h]; history.replaceState(null,"","#"+h); }
const pf = todas.find(f=>f.properties.id===h)?.properties;
if (pf){ if (pf.estado==="inactivo") document.getElementById("f-periodo").value="temporada";
         if (!pf.relevante) document.getElementById("f-aislados").checked = true; }
filtrar();
// El encuadre se hace sin animación y otra vez cada vez que el mapa cambia de tamaño,
// mientras nadie lo toque: si se calcula antes de que el contenedor tenga su altura,
// Leaflet elige un zoom para un mapa vacío.
const encuadrar = () => {
  if (capas[h]) return seleccionar(h,true,false);
  const b = capaHuellas.getLayers().length ? L.featureGroup(capaHuellas.getLayers()).getBounds() : null;
  b && b.isValid() ? mapa.fitBounds(b,{padding:[30,30],maxZoom:9,animate:false}) : mapa.setView(__VISTA__,{animate:false});
};
for (const ev of ["mousedown","touchstart","wheel","keydown"]) document.getElementById("mapa").addEventListener(ev,()=>{tocado=true},{passive:true});
encuadrar();
if (capas[h]) document.getElementById(h)?.scrollIntoView({block:"start"});
new ResizeObserver(()=>{ mapa.invalidateSize(); if(!tocado) encuadrar(); }).observe(document.getElementById("mapa"));
</script>
</body>
</html>
"""
