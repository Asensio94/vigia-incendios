// Ficha de un incendio: mapa 3D, línea de tiempo por pasada, curva de superficie y momentos.
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
