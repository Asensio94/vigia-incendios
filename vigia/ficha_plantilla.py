"""Page template and shared script of the per-fire analysis page (see ficha.py).

__MARKERS__ are filled by ficha.html, @@markers@@ by i18n.ficha_page in the page language.
"""

MAPLIBRE = "https://cdnjs.cloudflare.com/ajax/libs/maplibre-gl/5.6.0/maplibre-gl.min"

PLANTILLA = r"""<!doctype html>
<html lang="__LANG__">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
__FAVICON__
<title>__TITULO__ · @@sitio@@</title>
<meta name="description" content="__DESCRIPCION__">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;600;700&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<link rel="stylesheet" href="__MAPLIBRE__.css">
<style>
__COMMON_CSS__
:root{--accent:#c2410c;--accent-dark:#fb7b3e}
:root{
  --suelo:var(--ground); --papel:var(--paper); --tinta:var(--ink); --gris:var(--muted); --linea:var(--line);
  --brasa:var(--accent);
  --encendido:#ff3b1f; --ceniza:#4a3b34; --iso0:#f6c453; --iso1:#7a1c0c; --actual:#d0310f;
  --natura-l:#2f7a55; --s2:#3a2a8c;
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){ --encendido:#ff6b45; --ceniza:#b9a79c; --iso0:#f5d27a; --iso1:#c2410c; --actual:#ff6b45; --natura-l:#62b88a; --s2:#b8a6ff; }
}
:root[data-theme="dark"]{ --encendido:#ff6b45; --ceniza:#b9a79c; --iso0:#f5d27a; --iso1:#c2410c; --actual:#ff6b45; --natura-l:#62b88a; --s2:#b8a6ff; }
html{-webkit-text-size-adjust:100%}
.rotulo{font-family:var(--font-title);text-transform:uppercase;letter-spacing:.08em;font-weight:600;color:var(--gris);font-size:14px}
.marca{display:flex;align-items:baseline;gap:14px;flex-wrap:wrap}
.marca h1{text-wrap:balance}
.site-header .lede{text-wrap:pretty}
.site-header .lede a{white-space:nowrap}
.aviso{border-left:3px solid var(--brasa);padding:2px 0 2px 12px}
main.ficha-main{max-width:1440px;margin:0 auto;padding:0 16px;display:grid;grid-template-columns:minmax(0,1.6fr) minmax(300px,1fr);gap:18px;align-items:start}
.visor{display:grid;gap:8px;min-width:0}
#mapa{height:min(64vh,640px);min-height:340px;border:1px solid var(--linea);background:var(--papel);position:relative}
#mapa .sin-mapa{position:absolute;inset:0;display:grid;place-items:center;padding:16px;text-align:center;color:var(--gris)}
.reproductor{display:flex;flex-wrap:wrap;gap:8px 10px;align-items:center}
.reproductor button{font:600 15px/1 var(--font-title);letter-spacing:.06em;text-transform:uppercase;background:var(--papel);color:var(--tinta);border:1.5px solid var(--linea);padding:7px 11px;cursor:pointer;min-width:40px}
.reproductor button#play{border-color:var(--brasa);color:var(--brasa);min-width:96px}
.reproductor input[type=range]{flex:1 1 180px;accent-color:var(--brasa);min-width:120px}
.cuando{font:500 14px var(--font-data);font-variant-numeric:tabular-nums;flex:1 1 100%}
.estado{margin:0;font-size:14.5px;min-height:2.6em}
.estado b{font-family:var(--font-data);font-weight:500}
.estado .hueco{color:var(--brasa)}
.curva{margin:0}
.curva svg{width:100%;height:auto;display:block;cursor:pointer;touch-action:manipulation}
.curva figcaption{font-size:12.5px;color:var(--gris)}
.curva .eje{font:11px var(--font-data);fill:var(--gris)}
.leyenda{display:flex;flex-wrap:wrap;gap:4px 14px;font-size:12.5px;color:var(--gris);align-items:center}
.leyenda i{display:inline-block;width:11px;height:11px;margin-right:5px;vertical-align:-1px}
.capas{display:flex;flex-wrap:wrap;gap:4px 16px;font-size:13px;color:var(--gris)}
.capas label{display:flex;gap:6px;align-items:center}
.capas input{accent-color:var(--brasa)}
.momentos-caja{position:sticky;top:12px;max-height:calc(100vh - 24px);overflow:auto;padding-bottom:12px}
.momentos-caja h2{margin:0 0 4px;font:600 22px/1.15 var(--font-title)}
.momentos-caja > p{margin:0 0 10px;font-size:13px;color:var(--gris)}
ol.momentos{list-style:none;margin:0;padding:0;display:grid;gap:6px}
ol.momentos button{all:unset;box-sizing:border-box;display:grid;gap:2px;width:100%;padding:8px 10px;background:var(--papel);border:1px solid var(--linea);border-left:3px solid var(--linea);cursor:pointer;font-size:14.5px;line-height:1.35}
ol.momentos button:focus-visible{outline:2px solid var(--brasa);outline-offset:2px}
ol.momentos time{font:500 12.5px var(--font-data);color:var(--gris)}
ol.momentos li.pasado button{border-left-color:var(--iso1)}
ol.momentos li.actual button{border-color:var(--brasa);border-left-color:var(--brasa);box-shadow:0 0 0 1px var(--brasa)}
ol.momentos li.m-hueco button,ol.momentos li.m-reactivacion button{background:color-mix(in srgb,var(--brasa) 6%,var(--papel))}
.method{max-width:1440px;margin:24px auto 0;padding:0 16px 40px;border-top:1.5px solid var(--tinta);display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:28px}
.method p{margin:0 0 10px}
.method ol{margin:0 0 10px;padding-left:1.4em}
.method ol li{margin-bottom:8px}
.method > div > h2:first-child,.method > div > h3:first-child{margin-top:18px}
.nota{font-size:13.5px;color:var(--gris);margin:0}
.site-footer p{margin:0}
.maplibregl-ctrl-attrib{font-size:11px}
@media (max-width: 900px){
  main.ficha-main{grid-template-columns:1fr}
  .momentos-caja{position:static;max-height:none}
  #mapa{height:58vh}
  .method{grid-template-columns:1fr}
}
@media (max-width: 560px){
  .figures{display:grid;grid-template-columns:1fr 1fr;column-gap:12px}
  .reproductor input[type=range]{order:-1;flex-basis:100%}
  .reproductor button#play{flex:1}
}
</style>
</head>
<body>
<header class="site-header">
  <div class="marca">
    <h1>__LOGO__ __TITULO__</h1>
    <span class="rotulo">@@rotulo@@</span>
  </div>
  <p class="lede">@@lede@@ <a href="../">@@volver@@</a></p>
  <div class="figures">__CIFRAS__</div>
  __NOTA__
</header>

<main class="ficha-main">
  <section class="visor" aria-label="@@aria_visor@@">
    <div id="mapa" role="region" aria-label="@@aria_mapa@@"><noscript><p class="sin-mapa">@@sin_js@@</p></noscript></div>
    <div class="reproductor">
      <button type="button" id="play" aria-pressed="false">@@play@@</button>
      <button type="button" id="prev" aria-label="@@anterior@@">‹</button>
      <input type="range" id="paso" min="0" max="0" value="0" aria-label="@@aria_paso@@">
      <button type="button" id="next" aria-label="@@siguiente@@">›</button>
      <output class="cuando" id="cuando" for="paso"></output>
    </div>
    <p class="estado" id="estado" aria-live="polite"></p>
    <figure class="curva">
      <svg id="curva" viewBox="0 0 640 170" role="img" aria-label="@@aria_curva@@"></svg>
      <figcaption>@@curva_cap@@</figcaption>
    </figure>
    <div class="leyenda">
      <span><i style="background:var(--encendido)"></i>@@ley_actual@@</span>
      <span><i style="background:var(--ceniza);opacity:.5"></i>@@ley_ceniza@@</span>
      <span><i style="background:linear-gradient(90deg,var(--iso0),var(--iso1))"></i>@@ley_iso@@</span>
      <span><i style="border:2px solid var(--natura-l)"></i>@@ley_natura@@</span>
      <span><i style="border:2px dashed var(--s2)"></i>@@ley_s2@@</span>
    </div>
    <div class="capas">
      <label><input type="checkbox" id="c-3d" checked> @@capa_3d@@</label>
      <label><input type="checkbox" id="c-orto"> @@capa_orto@@</label>
      <label><input type="checkbox" id="c-natura" checked> @@capa_natura@@</label>
      <label><input type="checkbox" id="c-s2"> @@capa_s2@@</label>
    </div>
  </section>
  <aside class="momentos-caja" aria-labelledby="momentos-h">
    <h2 id="momentos-h">@@momentos_h@@</h2>
    <p>@@momentos_nota@@</p>
    <ol class="momentos" id="momentos">__MOMENTOS__</ol>
  </aside>
</main>

<section class="method" id="metodo">
  <div>
    <h2>@@como_h@@</h2>
    <ol>@@como_pasos@@</ol>
  </div>
  <div>
    <h3>@@limites_h@@</h3>
    @@limites@@
    <h3>@@datos_h@@</h3>
    <p>@@datos_p@@</p>
  </div>
</section>

__PIE__

<script src="__MAPLIBRE__.js"></script>
<script>const CFG = __CONFIG__;</script>
<script src="ficha.js"></script>
</body>
</html>
""".replace("__MAPLIBRE__", MAPLIBRE)


FICHA_JS = r"""// Ficha de un incendio: mapa 3D, línea de tiempo por pasada, curva de superficie y momentos.
(async function () {
  const T = CFG.t;
  const $ = id => document.getElementById(id);
  const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
  const ms = t => Date.parse(t.replace("Z", ":00Z"));
  const fmt = new Intl.DateTimeFormat(CFG.locale, {timeZone: CFG.tz, day: "numeric", month: "short",
                                                   hour: "2-digit", minute: "2-digit"});
  const fdia = new Intl.DateTimeFormat(CFG.locale, {timeZone: CFG.tz, day: "numeric", month: "short"});
  const hora = t => fmt.format(new Date(ms(t)));
  // Same as i18n.n / i18n.d: thousands always grouped (es-ES leaves 4-digit numbers alone).
  const num = (x, d = 0) => x.toLocaleString("en-US", {minimumFractionDigits: d, maximumFractionDigits: d})
    .replace(/[,.]/g, c => c === "," ? (CFG.locale.startsWith("fr") ? " " : ".") : ",");
  const fill = (s, o) => s.replace(/\{(\w+)\}/g, (_, k) => o[k]);
  const quieto = matchMedia("(prefers-reduced-motion: reduce)").matches;

  const D = await fetch(CFG.datos).then(r => r.json());
  const P = D.pasadas, N = P.length;
  const ISO = D.isocronas.features;
  const haIso = j => j >= 0 ? ISO[j].properties.ha : 0;

  // Píxeles con su tamaño real (scan × track, en km): el fuego está dentro, no en todo él.
  const pixeles = {type: "FeatureCollection", features: D.focos.map(([lo, la, k, frp, sc, tr]) => {
    const dx = sc / 2 / (111.32 * Math.cos(la * Math.PI / 180)), dy = tr / 2 / 110.57;
    return {type: "Feature", properties: {k, frp},
            geometry: {type: "Polygon", coordinates: [[[lo - dx, la - dy], [lo + dx, la - dy], [lo + dx, la + dy],
                                                      [lo - dx, la + dy], [lo - dx, la - dy]]]}};
  })};

  // ── Línea de tiempo ──
  let k = 0, timer = null;
  const paso = $("paso");
  paso.max = N - 1;

  // ── Curva de superficie (escalera: solo cambia cuando pasa VIIRS) ──
  const W = 640, H = 170, ML = 70, MR = 10, MT = 10, MB = 34;
  const t0 = ms(P[0].t), t1 = Math.max(ms(P[N - 1].t), t0 + 36e5);
  const hmax = Math.max(1, ...ISO.map(f => f.properties.ha));
  const X = t => ML + (W - ML - MR) * (ms(t) - t0) / (t1 - t0), Y = h => MT + (H - MT - MB) * (1 - h / hmax);
  const svg = $("curva");
  const ns = "http://www.w3.org/2000/svg";
  const el = (tag, at, padre = svg) => { const e = document.createElementNS(ns, tag);
    for (const a in at) e.setAttribute(a, at[a]); padre.appendChild(e); return e; };
  function dibujarCurva() {
    svg.textContent = "";
    const linea = css("--linea"), gris = css("--gris"), iso1 = css("--iso1"), brasa = css("--brasa");
    for (const f of [0, .5, 1]) {
      el("line", {x1: ML, x2: W - MR, y1: Y(hmax * f), y2: Y(hmax * f), stroke: linea, "stroke-width": 1});
      el("text", {x: ML - 6, y: Y(hmax * f) + 4, "text-anchor": "end", class: "eje"}).textContent = num(hmax * f) + " ha";
    }
    // días
    const dias = Math.ceil((t1 - t0) / 864e5);
    const cada = Math.max(1, Math.ceil(dias / 8));
    for (let i = 0; i <= dias; i += cada) {
      const t = t0 + i * 864e5, x = ML + (W - ML - MR) * (t - t0) / (t1 - t0);
      if (x > W - MR) break;
      el("text", {x, y: H - 6, "text-anchor": i ? "middle" : "start", class: "eje"}).textContent = fdia.format(new Date(t));
    }
    // pasadas: rayas abajo (VIIRS más altas)
    P.forEach((p, i) => el("line", {x1: X(p.t), x2: X(p.t), y1: H - MB, y2: H - MB + (p.viirs ? 9 : 5),
                                     stroke: p.viirs ? iso1 : gris, "stroke-width": 1, opacity: .8}));
    let d = "";
    ISO.forEach((f, j) => { const x = X(f.properties.t).toFixed(1), y = Y(f.properties.ha).toFixed(1);
      d += j ? `H${x}V${y}` : `M${x},${Y(0).toFixed(1)}V${y}`; });
    d += `H${(W - MR).toFixed(1)}`;
    el("path", {d: d + `V${Y(0).toFixed(1)}Z`, fill: iso1, opacity: .12});
    el("path", {d, fill: "none", stroke: iso1, "stroke-width": 2});
    for (const li of document.querySelectorAll("#momentos li")) {
      const p = P[+li.dataset.k], j = p.iso;
      el("circle", {cx: X(p.t), cy: Y(haIso(j)), r: 3.5, fill: brasa});
    }
    el("line", {id: "cursor", x1: 0, x2: 0, y1: MT, y2: H - MB, stroke: brasa, "stroke-width": 1.5});
    el("circle", {id: "cursor-p", r: 5, fill: brasa, stroke: css("--papel"), "stroke-width": 2});
  }
  dibujarCurva();
  svg.addEventListener("click", e => {
    const r = svg.getBoundingClientRect(), x = (e.clientX - r.left) * W / r.width;
    let mejor = 0;
    P.forEach((p, i) => { if (Math.abs(X(p.t) - x) < Math.abs(X(P[mejor].t) - x)) mejor = i; });
    parar(); ir(mejor);
  });

  // ── Mapa ──
  let mapa = null, listo = false;
  try {
    mapa = new maplibregl.Map({
      container: "mapa",
      style: {version: 8, sources: {
        osm: {type: "raster", tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"], tileSize: 256, maxzoom: 19,
              attribution: "© OpenStreetMap"},
        orto: {type: "raster", tiles: [CFG.orto[0]], tileSize: 256, maxzoom: 19, attribution: CFG.orto[1]},
        dem: {type: "raster-dem", tiles: ["https://tiles.mapterhorn.com/{z}/{x}/{y}.webp"], tileSize: 512,
              maxzoom: 12, encoding: "terrarium", attribution: "<a href=\"https://mapterhorn.com/attribution\">© Mapterhorn</a>"},
        demh: {type: "raster-dem", tiles: ["https://tiles.mapterhorn.com/{z}/{x}/{y}.webp"], tileSize: 512,
               maxzoom: 12, encoding: "terrarium"},
      }, layers: [
        {id: "osm", type: "raster", source: "osm", paint: {"raster-saturation": -0.6, "raster-opacity": .9}},
        {id: "orto", type: "raster", source: "orto", layout: {visibility: "none"}},
        {id: "sombra", type: "hillshade", source: "demh", paint: {"hillshade-exaggeration": .35}},
      ]},
      center: D.centro, zoom: 10, maxPitch: 75, attributionControl: {compact: true},
    });
  } catch (err) {
    $("mapa").innerHTML = `<p class="sin-mapa">${T.js_sin_webgl}</p>`;
  }
  if (mapa) {
    mapa.addControl(new maplibregl.NavigationControl({visualizePitch: true}), "top-right");
    mapa.on("load", () => {
      // Frame the fire flat, then tilt: fitting with pitch leaves it small in the distance.
      mapa.fitBounds([[D.bbox[0], D.bbox[1]], [D.bbox[2], D.bbox[3]]], {padding: 30, duration: 0, pitch: 0});
      mapa.jumpTo({pitch: 52, bearing: -12, zoom: mapa.getZoom() - 0.6});
      mapa.setTerrain({source: "dem", exaggeration: 1.4});
      const nIso = Math.max(1, ISO.length - 1);
      mapa.addSource("natura", {type: "geojson", data: D.natura});
      mapa.addSource("iso", {type: "geojson", data: D.isocronas});
      mapa.addSource("px", {type: "geojson", data: pixeles});
      mapa.addSource("s2", {type: "geojson", data: D.quemado_s2 ? {type: "Feature", properties: {}, geometry: D.quemado_s2}
                                                              : {type: "FeatureCollection", features: []}});
      mapa.addLayer({id: "natura-f", type: "fill", source: "natura", paint: {"fill-color": css("--natura-l"), "fill-opacity": .08}});
      mapa.addLayer({id: "natura-l", type: "line", source: "natura", paint: {"line-color": css("--natura-l"), "line-width": 1.5}});
      const color = ["interpolate", ["linear"], ["/", ["get", "k"], nIso], 0, css("--iso0"), 1, css("--iso1")];
      mapa.addLayer({id: "iso-f", type: "fill", source: "iso", filter: ["<=", ["get", "k"], -1],
                     paint: {"fill-color": color, "fill-opacity": .32}});
      mapa.addLayer({id: "iso-l", type: "line", source: "iso", filter: ["<=", ["get", "k"], -1],
                     paint: {"line-color": color, "line-width": 1, "line-opacity": .9}});
      mapa.addLayer({id: "px", type: "fill", source: "px", filter: ["<=", ["get", "k"], -1],
                     paint: {"fill-color": css("--ceniza"), "fill-opacity": .28}});
      mapa.addLayer({id: "iso-actual", type: "line", source: "iso", filter: ["==", ["get", "k"], -1],
                     paint: {"line-color": css("--actual"), "line-width": 2.5}});
      mapa.addLayer({id: "px-on", type: "fill", source: "px", filter: ["==", ["get", "k"], -1],
                     paint: {"fill-color": css("--encendido"),
                             "fill-opacity": ["interpolate", ["linear"], ["get", "frp"], 0, .55, 60, .95]}});
      mapa.addLayer({id: "s2", type: "line", source: "s2", layout: {visibility: "none"},
                     paint: {"line-color": css("--s2"), "line-width": 2, "line-dasharray": [2, 1.5]}});
      listo = true;
      ir(k, false);
    });
    $("c-3d").addEventListener("change", e => {
      mapa.setTerrain(e.target.checked ? {source: "dem", exaggeration: 1.4} : null);
      mapa.easeTo({pitch: e.target.checked ? 52 : 0, duration: quieto ? 0 : 600});
    });
    $("c-orto").addEventListener("change", e => {
      mapa.setLayoutProperty("orto", "visibility", e.target.checked ? "visible" : "none");
      mapa.setLayoutProperty("osm", "visibility", e.target.checked ? "none" : "visible");
    });
    $("c-natura").addEventListener("change", e => {
      for (const id of ["natura-f", "natura-l"]) if (listo) mapa.setLayoutProperty(id, "visibility", e.target.checked ? "visible" : "none");
    });
    $("c-s2").addEventListener("change", e => {
      if (listo) mapa.setLayoutProperty("s2", "visibility", e.target.checked ? "visible" : "none");
    });
    if (!D.quemado_s2) $("c-s2").closest("label").hidden = true;
    if (!D.natura.features.length) $("c-natura").closest("label").hidden = true;
  }

  function ir(i, hash = true) {
    k = Math.max(0, Math.min(N - 1, i));
    const p = P[k], j = p.iso;
    paso.value = k;
    $("cuando").textContent = `${fill(T.js_pasada, {k: k + 1, n: N})} · ${hora(p.t)} · ${p.sats.join(", ")}`;
    let txt = `${fill(p.n === 1 ? T.js_pixel : T.js_pixeles, {n: num(p.n)})}, ${num(p.frp)} MW. `;
    if (!p.viirs) txt += T.js_solo_modis + " ";
    if (j >= 0) {
      const crece = j > 0 && P[k - 1] && P[k - 1].iso !== j ? haIso(j) - haIso(j - 1) : 0;
      txt += fill(T.js_perimetro, {ha: `<b>${num(haIso(j))} ha</b>`});
      if (crece > 0) txt += " " + fill(T.js_crece, {ha: num(crece)});
    } else txt += T.js_sin_perimetro;
    if (p.h >= 18) txt = `<span class="hueco">${fill(T.js_hueco, {h: num(p.h)})}</span> ` + txt;
    $("estado").innerHTML = txt;
    const cx = X(p.t), cur = svg.querySelector("#cursor"), cp = svg.querySelector("#cursor-p");
    cur.setAttribute("x1", cx); cur.setAttribute("x2", cx);
    cp.setAttribute("cx", cx); cp.setAttribute("cy", Y(haIso(j)));
    for (const li of document.querySelectorAll("#momentos li")) {
      li.classList.toggle("actual", +li.dataset.k === k);
      li.classList.toggle("pasado", +li.dataset.k < k);
    }
    if (listo) {
      mapa.setFilter("iso-f", ["<=", ["get", "k"], j]);
      mapa.setFilter("iso-l", ["<=", ["get", "k"], j]);
      mapa.setFilter("iso-actual", ["==", ["get", "k"], j]);
      mapa.setFilter("px", ["<", ["get", "k"], k]);
      mapa.setFilter("px-on", ["==", ["get", "k"], k]);
    }
    if (hash) history.replaceState(null, "", `#p${k + 1}`);
  }

  function parar() {
    clearInterval(timer); timer = null;
    $("play").textContent = T.js_play; $("play").setAttribute("aria-pressed", "false");
  }
  $("play").addEventListener("click", () => {
    if (timer) return parar();
    if (k >= N - 1) ir(0);
    $("play").textContent = T.js_pausa; $("play").setAttribute("aria-pressed", "true");
    timer = setInterval(() => { if (k >= N - 1) return parar(); ir(k + 1); }, quieto ? 1600 : 900);
  });
  $("prev").addEventListener("click", () => { parar(); ir(k - 1); });
  $("next").addEventListener("click", () => { parar(); ir(k + 1); });
  paso.addEventListener("input", () => { parar(); ir(+paso.value); });
  $("momentos").addEventListener("click", e => {
    const li = e.target.closest("li[data-k]"); if (!li) return;
    parar(); ir(+li.dataset.k);
    if (innerWidth <= 900) $("mapa").scrollIntoView({behavior: quieto ? "auto" : "smooth", block: "start"});
  });
  document.addEventListener("keydown", e => {
    if (e.target.closest("input,select,textarea")) return;
    if (e.key === "ArrowRight") { parar(); ir(k + 1); }
    if (e.key === "ArrowLeft") { parar(); ir(k - 1); }
  });
  matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => { dibujarCurva(); ir(k, false); });

  const m = location.hash.match(/^#p(\d+)$/);
  ir(m ? +m[1] - 1 : N - 1, false);
})();
"""
