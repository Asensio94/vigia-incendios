"""Web estática: mapa, fichas de incendios, fuente Atom y GeoJSON descargable."""
from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from xml.sax.saxutils import escape

from shapely.geometry import shape

from . import config, focos as F, incendios as I, zonas

TEMPORADA_DIAS = 120


def relevante(i: dict) -> bool:
    """Lo que no es un foco aislado: tres focos o más, perímetro EFFIS o Red Natura."""
    return i.get("n_focos", 0) >= 3 or bool(i.get("effis")) or bool(i.get("natura"))


def _ligero(i: dict) -> dict:
    claves = ("id", "estado", "primera", "ultima", "n_focos", "pasadas", "satelites", "frp_max",
              "ha_focos", "centro", "lugar", "cobertura", "natura", "effis", "effis_ha", "unidos")
    out = {k: i[k] for k in claves if i.get(k) is not None}
    out["tipo"] = I.tipo(i)
    out["relevante"] = relevante(i)
    return out


def construir(reg: dict, todos: list[dict], areas: list[dict]) -> None:
    ahora = reg["actualizado"]
    desde = F.hace(TEMPORADA_DIAS * 24, F._dt(ahora))
    vivos = [i for i in reg["incendios"] if i.get("estado") != "unido" and i.get("ultima")]
    visibles = [i for i in vivos if i["estado"] in ("activo", "reciente")
                or (relevante(i) and i["ultima"] >= desde)]
    feats = [{"type": "Feature", "geometry": i["geometry"], "properties": _ligero(i)} for i in visibles]

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
        "redir": {i["id"]: i["unido_en"] for i in reg["incendios"] if i.get("unido_en")},
        "estados": I.ESTADOS, "grupos": I.GRUPOS_CLC,
        "ahora": ahora, "ultima_pasada": max((f["t"] for f in todos), default=None),
        "temporada_dias": TEMPORADA_DIAS,
    }
    validacion = (json.loads((config.DATA / "validacion.json").read_text(encoding="utf-8"))
                  if (config.DATA / "validacion.json").exists() else {})
    html = (PLANTILLA
            .replace("__ACTIVOS__", str(sum(relevante(i) for i in activos)))
            .replace("__AISLADOS__", str(sum(not relevante(i) for i in activos)))
            .replace("__NATURA__", str(sum(bool(i.get("natura")) for i in activos if relevante(i))))
            .replace("__FOCOS24__", str(sum(f["t"] >= F.hace(24, F._dt(ahora)) for f in todos)))
            .replace("__TEMPORADA__", str(TEMPORADA_DIAS))
            .replace("__METODO__", _parametros())
            .replace("__VALIDACION__", _validacion(validacion))
            .replace("__DATOS__", json.dumps(datos, ensure_ascii=False, separators=(",", ":"))
                     .replace("</", "<\\/")))

    config.SITE.mkdir(exist_ok=True)
    (config.SITE / "index.html").write_text(html, encoding="utf-8")
    shutil.copy(zonas.NATURA_WEB, config.SITE / "natura.geojson")
    todos_gj = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "geometry": i["geometry"],
         "properties": {k: v for k, v in i.items() if k != "geometry"}} for i in vivos]}
    (config.SITE / "incendios.geojson").write_text(json.dumps(todos_gj, ensure_ascii=False), encoding="utf-8")
    (config.SITE / "feed.xml").write_text(_feed(vivos, ahora), encoding="utf-8")
    (config.SITE / ".nojekyll").write_text("")


def _titulo(i: dict) -> str:
    l = i.get("lugar") or {}
    sitio = l.get("municipio") or l.get("provincia") or "lugar sin nombre"
    if l.get("provincia") and l.get("provincia") != sitio:
        sitio += f" ({l['provincia']})"
    return ("Incendio en " if relevante(i) else "Foco aislado en ") + sitio


def _feed(vivos: list[dict], ahora: str) -> str:
    rel = sorted((i for i in vivos if relevante(i) and i["ultima"] >= F.hace(7 * 24, F._dt(ahora))),
                 key=lambda i: i["ultima"], reverse=True)[:60]
    ent = []
    for i in rel:
        nat = ", ".join(f"{e['tipo']} {e['nombre']}" for e in i.get("natura", [])[:3])
        resumen = (f"{i['n_focos']} focos en {i['pasadas']} pasadas, del {i['primera']} al {i['ultima']} (UTC). "
                   f"Píxeles con focos: {i['ha_focos']:g} ha. Arde sobre: {I.tipo(i)}."
                   + (f" Red Natura: {nat}." if nat else "")
                   + (f" Perímetro EFFIS: {i['effis_ha']:g} ha." if i.get("effis_ha") else ""))
        ent.append(f"""<entry><id>{config.WEB}#{i['id']}</id><title>{escape(_titulo(i))}</title>
<link href="{config.WEB}#{i['id']}"/><updated>{i['ultima'][:16]}:00Z</updated>
<summary>{escape(resumen)}</summary></entry>""")
    return f"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"><title>Vigía de incendios</title>
<id>{config.WEB}</id><link href="{config.WEB}"/><link rel="self" href="{config.WEB}feed.xml"/>
<updated>{ahora[:16]}:00Z</updated><author><name>Vigía de incendios</name></author>
{chr(10).join(ent)}
</feed>
"""


def _parametros() -> str:
    filas = [
        ("Satélites", "VIIRS en S-NPP, NOAA-20 y NOAA-21 (píxel de 375 m) y MODIS en Terra y Aqua (1 km), vía NASA FIRMS"),
        ("Confianza mínima", f"VIIRS nominal o alta; MODIS {config.MODIS_CONFIANZA_MIN} sobre 100"),
        ("Fuentes fijas", f"fuera los focos a menos de {config.FIJAS_RADIO_KM:g} km de un punto marcado como fuente fija por FIRMS en {config.FIJAS_ANIOS[0]}–{config.FIJAS_ANIOS[-1]}".replace(".", ",")),
        ("Mismo incendio", f"píxeles a menos de {config.ENLACE_KM:g} km (más si son píxeles grandes) y vistos con menos de {config.ENLACE_HORAS} h de diferencia, en cadena".replace(".", ",")),
        ("Foco aislado", "uno o dos focos, sin perímetro EFFIS ni Red Natura"),
        ("Activo", f"algún foco en las últimas {config.ACTIVO_HORAS} h"),
        ("Qué arde", f"CORINE Land Cover 2018 en hasta {config.CLC_MUESTRAS} celdas con focos; vegetación natural si bosque, matorral, dehesa y roquedo suman la mitad"),
        ("Perímetro EFFIS", f"área quemada que toca la huella (con {config.EFFIS_HOLGURA_KM:g} km de margen) y empezó entre {config.EFFIS_HOLGURA_DIAS} días antes del primer foco y {config.EFFIS_HOLGURA_DIAS} días después del último"),
        ("Frecuencia", "cada hora; FIRMS publica los focos unas tres horas después de la pasada"),
        ("Horas", "peninsulares; en Canarias, una hora menos"),
    ]
    return '<table class="params">' + "".join(
        f"<tr><th>{escape(a)}</th><td>{escape(b)}</td></tr>" for a, b in filas) + "</table>"


def _validacion(v: dict) -> str:
    if not v:
        return ""
    filas = []
    for anio, r in v.items():
        for c in r["clases"]:
            t = f"{c['desde']}–{c['hasta']} ha" if c["hasta"] else f"≥ {c['desde']} ha"
            pct = round(100 * c["detectados"] / c["effis"]) if c["effis"] else 0
            filas.append(f"<tr><td>{anio}</td><td>{t}</td><td class='dato'>{c['detectados']} de {c['effis']}</td>"
                         f"<td class='dato'>{pct} %</td></tr>")
    return ('<table class="params valid"><tr><th>Año</th><th>Tamaño según EFFIS</th><th>Detectados</th><th></th></tr>'
            + "".join(filas) + "</table>")


PLANTILLA = r"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Vigía de incendios</title>
<meta name="description" content="Incendios con focos activos en España, vistos por satélite cada hora y cruzados con la Red Natura 2000 y las áreas quemadas de EFFIS.">
<link rel="alternate" type="application/atom+xml" title="Vigía de incendios" href="feed.xml">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='6' fill='%23221d1a'/%3E%3Cpath d='M16 5c1 5 7 7 7 14a7 7 0 0 1-14 0c0-4 2-6 4-8 0 3 1 5 3 5-1-4 0-8 0-11z' fill='%23f06a2b'/%3E%3C/svg%3E">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;600;700&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css">
<style>
:root{
  --suelo:#f0edea; --papel:#faf8f6; --tinta:#221d1a; --gris:#6b625c; --linea:#dad2cb;
  --brasa:#c2410c; --activo:#d0310f; --reciente:#a8660a; --inactivo:#857a72;
  --natura:#2f7a55; --natura-f:rgba(47,122,85,.10); --effis:#6b3fa0;
  --f6:#b0140a; --f24:#e8590c; --f72:#f2a33a; --fviejo:#a99d94;
  --sombra:0 1px 0 rgba(34,29,26,.06), 0 6px 18px -10px rgba(34,29,26,.28);
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    --suelo:#15110f; --papel:#1d1815; --tinta:#ede6e0; --gris:#a69a91; --linea:#362d28;
    --brasa:#fb7b3e; --activo:#ff6b45; --reciente:#e8a547; --inactivo:#8f847c;
    --natura:#62b88a; --natura-f:rgba(98,184,138,.12); --effis:#b08ce0;
    --f6:#ff4d3a; --f24:#ff8a3d; --f72:#f5c26b; --fviejo:#6f655e;
    --sombra:0 1px 0 rgba(0,0,0,.3), 0 8px 22px -12px rgba(0,0,0,.7);
  }
}
:root[data-theme="dark"]{
  --suelo:#15110f; --papel:#1d1815; --tinta:#ede6e0; --gris:#a69a91; --linea:#362d28;
  --brasa:#fb7b3e; --activo:#ff6b45; --reciente:#e8a547; --inactivo:#8f847c;
  --natura:#62b88a; --natura-f:rgba(98,184,138,.12); --effis:#b08ce0;
  --f6:#ff4d3a; --f24:#ff8a3d; --f72:#f5c26b; --fviejo:#6f655e;
  --sombra:0 1px 0 rgba(0,0,0,.3), 0 8px 22px -12px rgba(0,0,0,.7);
}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--suelo);color:var(--tinta);font:17px/1.55 "Source Serif 4",Georgia,serif}
a{color:inherit;text-decoration-color:var(--brasa);text-underline-offset:3px}
a:focus-visible,button:focus-visible,select:focus-visible,input:focus-visible{outline:2px solid var(--brasa);outline-offset:2px}
.rotulo{font-family:"Barlow Condensed","Arial Narrow",sans-serif;text-transform:uppercase;letter-spacing:.08em;font-weight:600}
.dato{font-family:"IBM Plex Mono",ui-monospace,monospace;font-variant-numeric:tabular-nums}
header.cabecera{padding:28px 16px 18px;max-width:1440px;margin:0 auto;display:grid;gap:14px}
.marca{display:flex;align-items:baseline;gap:14px;flex-wrap:wrap}
h1{margin:0;font:700 clamp(40px,6vw,64px)/.9 "Barlow Condensed","Arial Narrow",sans-serif;text-transform:uppercase;letter-spacing:.02em}
h1 span{color:var(--brasa)}
.marca .rotulo{color:var(--gris);font-size:14px}
.lede{margin:0;max-width:70ch;font-size:18px;text-wrap:pretty}
.cifras{display:flex;flex-wrap:wrap;border-top:1.5px solid var(--tinta);border-bottom:1px solid var(--linea)}
.cifra{padding:10px 18px 10px 0;margin-right:18px;display:grid;gap:2px}
.cifra b{font:600 30px/1 "IBM Plex Mono",monospace;font-variant-numeric:tabular-nums}
.cifra.vivo b{color:var(--activo)}
.cifra span{font-size:12.5px;color:var(--gris)}
.cifra.meta b{font-size:17px;line-height:1.75}
main{max-width:1440px;margin:0 auto;padding:0 16px;display:grid;grid-template-columns:minmax(0,1.35fr) minmax(360px,1fr);gap:18px;align-items:start}
.mapa-caja{position:sticky;top:12px;display:grid;gap:6px}
#mapa{height:calc(100vh - 60px);min-height:420px;border:1px solid var(--linea);background:var(--papel)}
.leyenda{display:flex;flex-wrap:wrap;gap:4px 14px;font-size:12.5px;color:var(--gris);align-items:center}
.leyenda i{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:5px;vertical-align:-1px}
.leyenda i.cuadro{border-radius:0;background:transparent!important;border:2px solid}
.lista{display:grid;gap:14px;padding-bottom:40px}
.filtros{display:flex;flex-wrap:wrap;gap:8px 14px;align-items:center;padding:10px 0;border-bottom:1px solid var(--linea);position:sticky;top:0;background:var(--suelo);z-index:5}
.filtros label{font-size:13px;color:var(--gris);display:flex;gap:6px;align-items:center}
.filtros select{max-width:min(240px,62vw);font:14px "Source Serif 4",serif;background:var(--papel);color:var(--tinta);border:1px solid var(--linea);padding:4px 6px}
.filtros input{accent-color:var(--brasa)}
.cuenta{margin-left:auto;font-size:13px;color:var(--gris)}
.ficha{background:var(--papel);border:1px solid var(--linea);box-shadow:var(--sombra);padding:14px 16px 16px;display:grid;gap:9px;scroll-margin-top:60px}
.ficha.sel{border-color:var(--brasa);box-shadow:0 0 0 1px var(--brasa),var(--sombra)}
.ficha header{display:flex;flex-wrap:wrap;gap:6px 10px;align-items:center}
.ficha h2{margin:0;font:600 22px/1.15 "Barlow Condensed","Arial Narrow",sans-serif;letter-spacing:.01em;flex:1 1 100%;text-wrap:balance}
.id{font-size:12px;color:var(--gris)}
.sello{font:600 12px/1 "Barlow Condensed",sans-serif;text-transform:uppercase;letter-spacing:.09em;padding:4px 7px 3px;border:1.5px solid currentColor}
.sello.activo{color:var(--activo);background:color-mix(in srgb,var(--activo) 10%,transparent)}
.sello.reciente{color:var(--reciente)} .sello.inactivo{color:var(--inactivo)}
.sello.natura{color:var(--natura)} .sello.effis{color:var(--effis)}
.cuando{margin:0;font-size:15px;color:var(--gris)}
.cuando strong{color:var(--tinta);font-weight:600}
dl.medidas{margin:0;display:grid;grid-template-columns:repeat(auto-fit,minmax(118px,1fr));gap:8px 12px}
dl.medidas div{display:grid;gap:1px}
dl.medidas dt{font-size:11.5px;color:var(--gris)}
dl.medidas dd{margin:0;font:500 15px "IBM Plex Mono",monospace;font-variant-numeric:tabular-nums}
.barra{display:flex;height:8px;background:var(--linea);overflow:hidden}
.barra span{display:block;height:100%}
.reparto{display:grid;gap:4px;font-size:13.5px}
.reparto p{margin:0;color:var(--gris)}
.espacios{margin:0;padding:0;list-style:none;display:grid;gap:3px;font-size:14.5px}
.espacios li{padding-left:10px;border-left:2px solid var(--natura)}
.espacios .dato{font-size:12px;color:var(--gris)}
.nota{font-size:13.5px;color:var(--gris);margin:0}
.acciones{display:flex;flex-wrap:wrap;gap:6px 16px;font-size:14px}
.acciones button{font:inherit;background:none;border:0;padding:0;color:inherit;text-decoration:underline;text-decoration-color:var(--brasa);text-underline-offset:3px;cursor:pointer}
.vacio{padding:28px 16px;border:1px dashed var(--linea);color:var(--gris);text-align:center}
section.metodo{max-width:1440px;margin:24px auto 0;padding:26px 16px 40px;border-top:1.5px solid var(--tinta);display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:28px}
section.metodo h2{margin:0 0 6px;font:700 28px/1 "Barlow Condensed",sans-serif;text-transform:uppercase;letter-spacing:.03em}
section.metodo h3{margin:18px 0 4px;font:600 18px/1.2 "Barlow Condensed",sans-serif;text-transform:uppercase;letter-spacing:.06em}
section.metodo p{margin:0 0 10px;max-width:66ch}
.aviso{border-left:3px solid var(--brasa);padding:2px 0 2px 12px}
table.params{border-collapse:collapse;width:100%;font-size:14.5px}
table.params th,table.params td{text-align:left;vertical-align:top;padding:7px 10px 7px 0;border-bottom:1px solid var(--linea)}
table.params th{font-weight:600;width:34%}
table.valid th{width:auto}
footer{max-width:1440px;margin:0 auto;padding:16px 16px 40px;font-size:13px;color:var(--gris);border-top:1px solid var(--linea)}
.leaflet-container{background:var(--papel);font:13px "Source Serif 4",serif}
.leaflet-control-layers,.leaflet-bar a{background:var(--papel);color:var(--tinta)}
.leaflet-popup-content-wrapper,.leaflet-popup-tip{background:var(--papel);color:var(--tinta)}
@media (max-width: 900px){
  main{grid-template-columns:1fr}
  .mapa-caja{position:relative;top:0}
  #mapa{height:56vh}
  section.metodo{grid-template-columns:1fr}
  .filtros{position:static}
}
@media (max-width: 560px){
  .cifras{display:grid;grid-template-columns:1fr 1fr;column-gap:12px}
  .cifra{margin-right:0;padding-right:0}
  .cifra b{font-size:26px}
  .cifra.meta{grid-column:1/-1}
}
@media (prefers-reduced-motion: reduce){*{scroll-behavior:auto!important}}
</style>
</head>
<body>
<header class="cabecera">
  <div class="marca">
    <h1>Vigía de <span>incendios</span></h1>
    <span class="rotulo">España · focos por satélite · cada hora</span>
  </div>
  <p class="lede">Incendios con focos activos vistos desde satélite, agrupados por reglas fijas y cruzados con la Red Natura 2000 y con las áreas quemadas que cartografía EFFIS. Sin esperar a la estadística oficial, y sin sustituirla: un foco es un píxel caliente, no un parte de extinción.</p>
  <div class="cifras">
    <div class="cifra vivo"><b>__ACTIVOS__</b><span>incendios con focos en las últimas 24 h</span></div>
    <div class="cifra"><b>__NATURA__</b><span>de ellos, en la Red Natura 2000</span></div>
    <div class="cifra"><b>__AISLADOS__</b><span>focos aislados aparte</span></div>
    <div class="cifra"><b>__FOCOS24__</b><span>focos en las últimas 24 h</span></div>
    <div class="cifra meta"><b class="dato" id="pasada">—</b><span>último foco visto · revisado a las <span id="actualizado"></span></span></div>
  </div>
</header>

<main>
  <div class="mapa-caja">
    <div id="mapa" role="region" aria-label="Mapa de incendios"></div>
    <div class="leyenda" aria-label="Leyenda">
      <span><i style="background:var(--f6)"></i>foco de hace menos de 6 h</span>
      <span><i style="background:var(--f24)"></i>6–24 h</span>
      <span><i style="background:var(--f72)"></i>1–3 días</span>
      <span><i style="background:var(--fviejo)"></i>3–7 días</span>
      <span><i class="cuadro" style="border-color:var(--effis)"></i>perímetro EFFIS</span>
    </div>
  </div>
  <div class="lista">
    <div class="filtros">
      <label>Periodo <select id="f-periodo">
        <option value="activo">Últimas 24 h</option><option value="semana" selected>Últimos 7 días</option>
        <option value="temporada">Últimos __TEMPORADA__ días</option></select></label>
      <label>Arde sobre <select id="f-tipo"><option value="">Cualquier cosa</option></select></label>
      <label><input type="checkbox" id="f-natura"> Solo Red Natura</label>
      <label><input type="checkbox" id="f-aislados"> Con focos aislados</label>
      <span class="cuenta" id="cuenta" aria-live="polite"></span>
    </div>
    <div id="fichas"></div>
  </div>
</main>

<section class="metodo" id="metodo">
  <div>
    <h2>Cómo vigila</h2>
    <p>Cada hora se descargan los focos activos que publica NASA FIRMS para la península, Baleares, Canarias, Ceuta y Melilla. Un foco es un píxel de 375 metros (VIIRS) o de un kilómetro (MODIS) donde el satélite ha medido más calor del normal en una pasada. Hay unas diez pasadas útiles al día entre los cinco satélites, y FIRMS publica cada una unas tres horas después.</p>
    <p>Se quitan los focos de confianza baja, que suelen ser reflejos del sol en tejados e invernaderos, y los que caen junto a fuentes fijas de calor como cementeras, acerías o refinerías. Los demás se agrupan en incendios: dos focos son del mismo incendio si sus píxeles están a menos de dos kilómetros y se vieron con menos de tres días de diferencia, y basta una cadena de focos para unir un frente que avanza. Son reglas fijas: no interviene ningún modelo entrenado ni ninguna inteligencia artificial.</p>
    <p>De cada incendio se calcula la extensión de sus píxeles, qué cubierta tenía el suelo según CORINE Land Cover 2018, los espacios de la Red Natura 2000 que toca y el municipio. Cuando EFFIS, el servicio europeo de incendios de Copernicus, publica el perímetro quemado, se enlaza y su superficie pasa a ser la de referencia.</p>
    <h3>Lo que hay que saber antes de citarlo</h3>
    <p class="aviso">La extensión de los píxeles con focos no es la superficie quemada. En incendios pequeños la exagera, porque un fuego de una hectárea enciende un píxel de catorce. En los grandes puede quedarse corta si el humo o las nubes tapan el frente. La superficie que se puede citar es la del perímetro EFFIS o la oficial.</p>
    <p>«Activo» quiere decir que el satélite vio calor en las últimas 24 horas, no que el incendio siga sin controlar. Al revés, un incendio puede seguir ardiendo sin focos si el humo o las nubes lo tapan o si arde bajo arbolado. Los focos aislados, uno o dos sin más señales, son a menudo quemas agrícolas o de rastrojos. Por eso no se muestran salvo que se pida.</p>
    <h3>Contraste con 2023 y 2024</h3>
    <p>Las mismas reglas, aplicadas al archivo de FIRMS de esos años, se compararon con los incendios que cartografió EFFIS en España. Un incendio de EFFIS cuenta como visto si su perímetro toca la huella de focos de un incendio del vigía en sus mismas fechas.</p>
    __VALIDACION__
    <p class="nota">Los que se escapan son sobre todo incendios cortos que arden entre dos pasadas o bajo nubes. Detalle en <a href="https://github.com/Asensio94/vigia-incendios/blob/main/docs/validacion.md">docs/validacion.md</a>.</p>
  </div>
  <div>
    <h2>Parámetros</h2>
    __METODO__
    <h3>Datos de censos de especies</h3>
    <p>El vigía no incorpora datos de censos de especies (colonias, nidos, dormideros ni territorios). Esa información es interna de las entidades que la producen: no se publica aquí, no se guarda en el repositorio y no se usa en ningún cálculo. Una ubicación precisa de una colonia junto a un incendio puede poner en riesgo a la especie.</p>
    <h3>Datos abiertos</h3>
    <p><a href="incendios.geojson">incendios.geojson</a> con todos los incendios y sus cruces · <a href="feed.xml">fuente Atom</a> de los incendios de la última semana · focos por año en CSV en el <a href="https://github.com/Asensio94/vigia-incendios/tree/main/data/focos">repositorio</a> · <a href="https://github.com/Asensio94/vigia-incendios">código</a>.</p>
  </div>
</section>

<footer>
  Focos activos: NASA FIRMS (LANCE), parte del Earth Science Data and Information System de la NASA · Áreas quemadas: EFFIS, Copernicus Emergency Management Service, © Unión Europea · Red Natura 2000 y CORINE Land Cover 2018: Agencia Europea de Medio Ambiente · Municipios: Nominatim, © colaboradores de OpenStreetMap (ODbL) · Ortofoto PNOA: CC BY 4.0 scne.es.
</footer>

<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>
<script>
const D = __DATOS__;
const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const esc = s => String(s??"").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const num = (x,d=0) => x==null ? "—" : x.toLocaleString("es-ES",{minimumFractionDigits:d,maximumFractionDigits:d});
const ms = t => Date.parse(t.replace("Z",":00Z"));
const AHORA = ms(D.ahora);
const fmt = new Intl.DateTimeFormat("es-ES",{timeZone:"Europe/Madrid",day:"numeric",month:"short",hour:"2-digit",minute:"2-digit"});
const hora = t => fmt.format(new Date(ms(t)));
const hace = t => { const h = (AHORA-ms(t))/36e5; return h < 1 ? "hace menos de una hora" : h < 48 ? `hace ${Math.round(h)} h` : `hace ${Math.round(h/24)} días`; };

document.getElementById("pasada").textContent = D.ultima_pasada ? hora(D.ultima_pasada) : "—";
document.getElementById("actualizado").textContent = hora(D.ahora).split(", ").pop();

const todas = D.incendios.features;
const tipos = {}; for (const f of todas) tipos[f.properties.tipo] = (tipos[f.properties.tipo]||0)+1;
for (const t of ["vegetación natural","mixto","cultivos","suelo urbano o industrial","sin datos"]) if (tipos[t])
  document.getElementById("f-tipo").insertAdjacentHTML("beforeend",`<option value="${t}">${esc(t[0].toUpperCase()+t.slice(1))}</option>`);

// ── Mapa ──
const mapa = L.map("mapa",{zoomControl:true}).setView([40.2,-3.7],6);
const osm = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",{maxZoom:19,attribution:"© OpenStreetMap"}).addTo(mapa);
const pnoa = L.tileLayer("https://www.ign.es/wmts/pnoa-ma?service=WMTS&request=GetTile&version=1.0.0&format=image/jpeg&layer=OI.OrthoimageCoverage&style=default&tilematrixset=GoogleMapsCompatible&tilematrix={z}&tilerow={y}&tilecol={x}",{maxZoom:20,attribution:"PNOA © scne.es"});
const capaNatura = L.geoJSON(null,{style:()=>({color:css("--natura"),weight:1,fillColor:css("--natura"),fillOpacity:.10}),
  onEachFeature:(f,l)=>l.bindTooltip(`${esc(f.properties.tipo)} · ${esc(f.properties.nombre)}`,{sticky:true})});
let naturaCargada = false;
mapa.on("overlayadd", e => { if (e.layer===capaNatura && !naturaCargada){ naturaCargada = true;
  fetch("natura.geojson").then(r=>r.json()).then(g=>{capaNatura.addData(g); capaNatura.bringToBack();}); }});
const capaEffis = L.geoJSON(D.effis,{style:()=>({color:css("--effis"),weight:1.5,dashArray:"4 3",fill:false})}).addTo(mapa);
const capaFocos = L.layerGroup().addTo(mapa);
const capaHuellas = L.layerGroup().addTo(mapa);
L.control.layers({"Mapa":osm,"Ortofoto PNOA":pnoa},{"Focos (7 días)":capaFocos,"Incendios":capaHuellas,"Perímetros EFFIS":capaEffis,"Red Natura 2000":capaNatura},{collapsed:true}).addTo(mapa);

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
const titulo = p => { const l=p.lugar||{}; let s=l.municipio||l.provincia||"lugar sin nombre";
  if (l.provincia && l.provincia!==s) s+=` (${l.provincia})`; return (p.relevante?"Incendio en ":"Foco aislado en ")+s; };
const COLG = {bosque:"#3f7a3a",matorral:"#8a9a3c",agroforestal:"#b59b45",desnudo:"#9b8c7e",agricola:"#d8b55b",artificial:"#7b6f86",agua:"#3f7fb0"};
function ficha(p){
  const reparto = p.cobertura && Object.keys(p.cobertura).length ? `<div class="reparto">
    <div class="barra" role="img" aria-label="Cubierta del suelo">${Object.entries(p.cobertura).map(([k,v])=>`<span style="width:${v*100}%;background:${COLG[k]||"#999"}" title="${esc(D.grupos[k])}"></span>`).join("")}</div>
    <p>Arde sobre ${Object.entries(p.cobertura).map(([k,v])=>`${esc(D.grupos[k])} ${Math.round(v*100)} %`).join(", ")} <span class="dato">(CORINE 2018)</span></p></div>` : "";
  const nat = (p.natura||[]).length ? `<ul class="espacios">${p.natura.slice(0,4).map(e=>`<li>${esc(e.tipo)} <strong>${esc(e.nombre)}</strong> <span class="dato">${esc(e.codigo)} · ${num(e.ha)} ha de píxeles con focos</span></li>`).join("")}</ul>${p.natura.length>4?`<p class="nota">Y ${p.natura.length-4} espacios más.</p>`:""}` : "";
  const ef = p.effis_ha!=null ? `<p class="nota">Perímetro EFFIS: <strong>${num(p.effis_ha)} ha</strong> quemadas${p.effis.length>1?` en ${p.effis.length} áreas`:""}, actualizado el ${esc(p.effis.map(e=>e.actualizado).sort().pop())}.</p>`
    : p.relevante ? `<p class="nota">EFFIS aún no ha publicado su perímetro.</p>` : "";
  const un = (p.unidos||[]).length ? `<p class="nota">Reúne ${p.unidos.length+1} incendios que se vieron por separado y luego se juntaron (${p.unidos.map(esc).join(", ")}).</p>` : "";
  const d0 = p.primera.slice(0,10), d1 = p.ultima.slice(0,10);
  const firms = `https://firms.modaps.eosdis.nasa.gov/map/#d:${d0}..${d1};@${p.centro[0]},${p.centro[1]},12.0z`;
  return `<article class="ficha" id="${esc(p.id)}">
    <header>
      <h2>${esc(titulo(p))}</h2>
      <span class="sello ${p.estado}">${esc(D.estados[p.estado])}</span>
      ${(p.natura||[]).length ? `<span class="sello natura">Red Natura</span>` : ""}
      ${p.effis_ha!=null ? `<span class="sello effis">Perímetro EFFIS</span>` : ""}
      <span class="id dato">${esc(p.id)}</span>
    </header>
    <p class="cuando">Primer foco <strong>${hora(p.primera)}</strong> · último <strong>${hora(p.ultima)}</strong>, ${hace(p.ultima)}</p>
    <dl class="medidas">
      <div><dt>Focos</dt><dd>${num(p.n_focos)}</dd></div>
      <div><dt>Pasadas</dt><dd>${num(p.pasadas)}</dd></div>
      <div><dt>Píxeles con focos</dt><dd>${num(p.ha_focos)} ha</dd></div>
      <div><dt>Potencia máxima</dt><dd>${num(p.frp_max)} MW</dd></div>
    </dl>
    ${reparto}${nat}${ef}${un}
    <div class="acciones"><button type="button" data-zoom="${esc(p.id)}">Ver en el mapa</button>
      <a href="${firms}">Focos en FIRMS</a><a href="#${esc(p.id)}">Enlace</a></div>
  </article>`;
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
    : `<p class="vacio">Ningún incendio cumple los filtros. ${per==="activo"?"Puede que no haya focos en las últimas 24 horas: prueba con los últimos 7 días.":""}</p>`;
  document.getElementById("cuenta").textContent = ok.length===1 ? "1 incendio" : `${ok.length} incendios`;
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
  b && b.isValid() ? mapa.fitBounds(b,{padding:[30,30],maxZoom:9,animate:false}) : mapa.setView([40.2,-3.7],6,{animate:false});
};
for (const ev of ["mousedown","touchstart","wheel","keydown"]) document.getElementById("mapa").addEventListener(ev,()=>{tocado=true},{passive:true});
encuadrar();
if (capas[h]) document.getElementById(h)?.scrollIntoView({block:"start"});
new ResizeObserver(()=>{ mapa.invalidateSize(); if(!tocado) encuadrar(); }).observe(document.getElementById("mapa"));
</script>
</body>
</html>
"""
