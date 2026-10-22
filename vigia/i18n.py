"""Interface strings and number formats, one dictionary per language.

Each country's page is written in that country's language: the Spanish one in Spanish, the
French one in French. Data files (incendios.json, signals.json, GeoJSON) keep canonical,
language-independent values; only what a reader sees goes through here. Same pattern as
humedales/i18n.py in vigilancia-humedales.
"""
from __future__ import annotations

LANG_BY_COUNTRY = {"ES": "es", "FR": "fr"}


def lang_of(pais: str) -> str:
    return LANG_BY_COUNTRY.get(pais, "es")

# French typography: a narrow no-break space as thousands separator and before «%».
_NNBSP = " "


def n(v: float, lang: str) -> str:
    """Integer with the thousands separator of the language: 46.709 / 46 709."""
    s = f"{v:,.0f}"
    return s.replace(",", "." if lang == "es" else _NNBSP)


def d(v: float, lang: str, nd: int = 1) -> str:
    """Decimal with comma, in both languages and with thousands: 1.234,5 / 1 234,5."""
    ent, _, dec = f"{abs(v):.{nd}f}".partition(".")
    return ("-" if v < 0 else "") + n(int(ent), lang) + ("," + dec if dec else "")


def p(x: float, lang: str) -> str:
    """A fraction as a percentage without decimals: 15 % / 15 %."""
    return f"{100 * x:.0f}{' ' if lang == 'es' else _NNBSP}%"


def pct(v: float, lang: str) -> str:
    """Spacing before «%» for a number already in percent."""
    return f"{v}{' ' if lang == 'es' else _NNBSP}%"


# French display labels of canonical values. The data keep the Spanish keys and values
# (incendios.ESTADOS, incendios.GRUPOS_CLC, incendios.tipo), so a fire reads the same in both.
ESTADOS_FR = {"activo": "Foyers ces dernières 24 h", "reciente": "Sans foyers depuis 1 à 7 jours",
              "inactivo": "Sans foyers depuis plus de 7 jours", "unido": "Rattaché à un autre incendie"}
GRUPOS_FR = {"bosque": "forêt", "matorral": "landes, maquis et pelouses", "agroforestal": "mosaïque agroforestière",
             "desnudo": "roches ou sol nu", "agricola": "cultures", "artificial": "sol urbain ou industriel",
             "agua": "zone humide ou eau"}
TIPOS_FR = {"vegetación natural": "végétation naturelle", "mixto": "mixte", "cultivos": "cultures",
            "suelo urbano o industrial": "sol urbain ou industriel", "sin datos": "sans données"}
ESTADO_SEV_FR = {"alta": "élevée", "moderada": "modérée", "baja": "faible"}


# Acronyms and technical terms, explained once per page (main page, list and fire pages).
GLOSARIO = {
    "es": (
        '<h3>Siglas y términos</h3>\n'
        '    <ul class="glosario">\n'
        '      <li><strong>FIRMS</strong> (Fire Information for Resource Management System): el servicio de '
        'la NASA que publica en abierto los focos de calor que ven los satélites, unas horas después de cada '
        'pasada.</li>\n'
        '      <li><strong>VIIRS</strong> y <strong>MODIS</strong>: los dos sensores que detectan esos focos.'
        ' VIIRS va en los satélites S-NPP, NOAA-20 y NOAA-21, con píxeles de 375 m; MODIS, en Terra y Aqua, '
        'con píxeles de 1 km.</li>\n'
        '      <li><strong>FRP</strong> (potencia radiativa del fuego): el calor que emite un píxel, en '
        'megavatios. Sirve para comparar la intensidad de una pasada con otra.</li>\n'
        '      <li><strong>EFFIS</strong>: el Sistema Europeo de Información sobre Incendios Forestales, de '
        'Copernicus. Dibuja los perímetros quemados a partir de unas 30 ha.</li>\n'
        '      <li><strong>NBR</strong> y <strong>dNBR</strong>: el NBR (índice normalizado de área quemada) '
        'compara en una imagen el infrarrojo cercano con el de onda corta; el dNBR es cuánto baja entre la '
        'imagen de antes y la de después del fuego. Cuanto más baja, más quemado.</li>\n'
        '      <li><strong>FEDS</strong> (Fire Event Data Suite): el método de la NASA que sigue cada '
        'incendio pasada a pasada con los focos VIIRS. El perímetro estimado del vigía sigue la misma '
        'idea.</li>\n'
        '      <li><strong>CORINE Land Cover</strong>: el mapa europeo de cubiertas del suelo (bosque, '
        'matorral, cultivos, ciudad…), en su edición de 2018.</li>\n'
        '      <li><strong>Red Natura 2000</strong>: la red europea de espacios protegidos. '
        '<strong>ZEC</strong> es Zona Especial de Conservación (Directiva Hábitats) y <strong>ZEPA</strong>, '
        'Zona de Especial Protección para las Aves (Directiva Aves).</li>\n'
        '      <li><strong>Sentinel-2</strong>: los satélites europeos de Copernicus que fotografían el suelo'
        ' cada dos o tres días con píxeles de 10 a 20 m. <strong>PNOA</strong>: la ortofoto del Plan Nacional'
        ' de Ortofotografía Aérea.</li>\n'
        '    </ul>'
    ),
    "fr": (
        '<h3>Sigles et termes</h3>\n'
        '    <ul class="glosario">\n'
        '      <li><strong>FIRMS</strong> (Fire Information for Resource Management System) : le service de '
        'la NASA qui publie en accès libre les foyers de chaleur vus par satellite, quelques heures après '
        'chaque passage.</li>\n'
        '      <li><strong>VIIRS</strong> et <strong>MODIS</strong> : les deux capteurs qui détectent ces '
        'foyers. VIIRS est à bord des satellites S-NPP, NOAA-20 et NOAA-21, avec des pixels de 375 m ; MODIS,'
        ' à bord de Terra et Aqua, avec des pixels de 1 km.</li>\n'
        '      <li><strong>FRP</strong> (puissance radiative du feu) : la chaleur émise par un pixel, en '
        'mégawatts. Elle sert à comparer l’intensité d’un passage à l’autre.</li>\n'
        '      <li><strong>EFFIS</strong> : le Système européen d’information sur les feux de forêt, de '
        'Copernicus. Il cartographie les surfaces brûlées à partir d’environ 30 ha.</li>\n'
        '      <li><strong>NBR</strong> et <strong>dNBR</strong> : le NBR (indice normalisé de surface '
        'brûlée) compare sur une image le proche infrarouge et l’infrarouge à ondes courtes ; le dNBR est sa '
        'baisse entre l’image d’avant et celle d’après le feu. Plus il baisse, plus c’est brûlé.</li>\n'
        '      <li><strong>FEDS</strong> (Fire Event Data Suite) : la méthode de la NASA qui suit chaque '
        'incendie passage après passage avec les foyers VIIRS. Le périmètre estimé de la vigie suit la même '
        'idée.</li>\n'
        '      <li><strong>CORINE Land Cover</strong> : la carte européenne d’occupation du sol (forêt, '
        'landes, cultures, ville…), dans son édition 2018.</li>\n'
        '      <li><strong>Natura 2000</strong> : le réseau européen d’espaces protégés. <strong>ZSC</strong>'
        ' : zone spéciale de conservation (directive Habitats) ; <strong>ZPS</strong> : zone de protection '
        'spéciale (directive Oiseaux).</li>\n'
        '      <li><strong>BDIFF</strong> : la Base de données sur les incendies de forêts en France, la '
        'statistique officielle. <strong>Code INSEE</strong> : le code officiel de chaque commune.</li>\n'
        '      <li><strong>Sentinel-2</strong> : les satellites européens de Copernicus qui photographient le'
        ' sol tous les deux ou trois jours avec des pixels de 10 à 20 m.</li>\n'
        '    </ul>'
    ),
}

# Header figures with one item (and zero, in French) take the singular.
SINGULAR = {
    "es": {"fig_active": "<span>incendio con focos en las últimas 24 h</span>",
           "fig_isolated": "<span>foco aislado aparte</span>",
           "fig_focos24": "<span>foco en las últimas 24 h</span>"},
    "fr": {"fig_active": "<span>incendie avec des foyers ces dernières 24 h</span>",
           "fig_isolated": "<span>foyer isolé en plus</span>",
           "fig_focos24": "<span>foyer ces dernières 24 h</span>"},
}


def singular(v: int, lang: str) -> bool:
    """Spanish takes the singular only for one; French also for zero."""
    return v == 1 or (lang == "fr" and v == 0)


# Page fragments by marker: web.PLANTILLA carries @@key@@ where the text depends on the
# language. The Spanish values are the page as it always was, so it renders byte for byte.
UI: dict[str, dict[str, str]] = {
    "es": {
        'lang': '<html lang="es">',
        'meta_description': ('Incendios con focos activos en España, vistos por satélite cada hora y cruzados con la Red Natura '
                             '2000 y las áreas quemadas de EFFIS.'),
        'project_title': '<title>Vigía de incendios</title>',
        'project_feed': 'title="Vigía de incendios"',
        'h1': 'Vigía de <span>incendios</span>',
        'tagline': '<span class="rotulo">España · focos por satélite · cada hora</span>',
        'lede': ('Incendios con focos activos vistos desde satélite, agrupados por reglas fijas y cruzados con '
                 'la Red Natura 2000 y con las áreas quemadas que cartografía EFFIS. Sin esperar a la estadística '
                 'oficial, y sin sustituirla: un foco es un píxel caliente, no un parte de extinción.'),
        'fig_active': '<span>incendios con focos en las últimas 24 h</span>',
        'fig_natura': '<span>de ellos, en la Red Natura 2000</span>',
        'fig_isolated': '<span>focos aislados aparte</span>',
        'fig_focos24': '<span>focos en las últimas 24 h</span>',
        'fig_last': '<span>último foco visto · revisado a las ',
        'map_aria': 'aria-label="Mapa de incendios"',
        'legend_aria': 'aria-label="Leyenda"',
        'legend': ('      <span><i style="background:var(--f6)"></i>foco de hace menos de 6 h</span>\n'
                   '      <span><i style="background:var(--f24)"></i>6–24 h</span>\n'
                   '      <span><i style="background:var(--f72)"></i>1–3 días</span>\n'
                   '      <span><i style="background:var(--fviejo)"></i>3–7 días</span>\n'
                   '      <span><i class="cuadro relleno"></i>quemado según Sentinel-2</span>\n'
                   '      <span><i class="cuadro" style="border-color:var(--effis)"></i>perímetro EFFIS</span>'),
        'filters': ('      <label>Periodo <select id="f-periodo">\n'
                    '        <option value="activo">Últimas 24 h</option><option value="semana" selected>Últimos '
                    '7 días</option>\n'
                    '        <option value="temporada">Últimos __TEMPORADA__ días</option></select></label>\n'
                    '      <label>Arde sobre <select id="f-tipo"><option value="">Cualquier cosa</option></select></label>\n'
                    '      <label><input type="checkbox" id="f-natura"> Solo Red Natura</label>\n'
                    '      <label><input type="checkbox" id="f-aislados"> Con focos aislados</label>'),
        'method_title': '<h2>Cómo se calcula</h2>',
        'steps': ('      <li>Cada hora se descargan los focos activos que publica NASA FIRMS para la península, '
                  'Baleares, Canarias, Ceuta y Melilla. Un foco es un píxel de 375 metros (VIIRS) o de un kilómetro '
                  '(MODIS) donde el satélite ha medido más calor del normal en una pasada. Hay unas diez pasadas '
                  'útiles al día entre los cinco satélites, y FIRMS publica cada una unas tres horas después.</li>\n'
                  '      <li>Se quitan los focos de confianza baja, que suelen ser reflejos del sol en tejados '
                  'e invernaderos, y los que caen junto a fuentes fijas de calor como cementeras, acerías o refinerías.</li>\n'
                  '      <li>Los demás se agrupan en incendios: dos focos son del mismo incendio si sus píxeles '
                  'están a menos de dos kilómetros y se vieron con menos de tres días de diferencia, y basta una '
                  'cadena de focos para unir un frente que avanza. Son reglas fijas: no interviene ningún modelo '
                  'entrenado ni ninguna inteligencia artificial.</li>\n'
                  '      <li>De cada incendio se calcula la extensión de sus píxeles, qué cubierta tenía el suelo '
                  'según CORINE Land Cover 2018, los espacios de la Red Natura 2000 que toca y el municipio. Cuando '
                  'EFFIS, el servicio europeo de incendios de Copernicus, publica el perímetro quemado, se enlaza '
                  'y su superficie pasa a ser la de referencia.</li>'),
        'params_title': '<h3>Parámetros</h3>',
        'glossary': GLOSARIO['es'],
        's2_section': ('<h3>Superficie quemada con Sentinel-2</h3>\n'
                       '    <p>EFFIS tarda días en cartografiar y apenas dibuja nada por debajo de 30 hectáreas. Para '
                       'no esperar, el vigía mide lo quemado con las imágenes de Sentinel-2, que pasan cada dos o tres '
                       'días con píxeles de 20 metros. Compara el índice de área quemada (NBR) de antes y de después '
                       'del fuego: la vegetación quemada pierde reflectancia en el infrarrojo cercano y la gana en el '
                       'de onda corta. Solo cuenta lo que cambia junto a los focos y unido a ellos, para que no entren '
                       'cosechas ni labrados de las mismas semanas. Para que una sombra de nube o una bruma de una sola '
                       'imagen no pase por ceniza, un píxel solo cuenta como quemado si lo ven al menos dos imágenes. '
                       'El cálculo se rehace al llegar imágenes nuevas, hasta veinte días después del último foco. Si '
                       'las nubes tapan más de la mitad de la zona, la cifra se da como mínimo («al menos») o no se '
                       'da. Si lo quemado solo lo ha visto una imagen, ese filtro no puede actuar: la ficha lo avisa '
                       'y la cifra no se da por definitiva hasta que llegue otra. Cada ficha enlaza la imagen de antes '
                       'y la de después en Copernicus Browser, para que cualquiera pueda comprobar a ojo lo que dice '
                       'el índice.</p>'),
        'val_title': '<h3>Contraste con 2023 y 2024</h3>',
        'val_intro': ('<p>Las mismas reglas, aplicadas al archivo de FIRMS de esos años, se compararon con los incendios '
                      'que cartografió EFFIS en España. Un incendio de EFFIS cuenta como visto si su perímetro toca '
                      'la huella de focos de un incendio del vigía en sus mismas fechas.</p>'),
        'val_note': ('<p class="nota">Los que se escapan son sobre todo incendios cortos que arden entre dos pasadas '
                     'o bajo nubes. Detalle en <a href="https://github.com/Asensio94/vigia-incendios/blob/main/docs/validacion.md">docs/validacion.md</a>.</p>'),
        'caveats': ('<h3>Lo que hay que saber antes de citarlo</h3>\n'
                    '    <p class="aviso">La extensión de los píxeles con focos no es la superficie quemada. En incendios '
                    'pequeños la exagera, porque un fuego de una hectárea enciende un píxel de catorce; en los grandes '
                    'puede quedarse corta. La superficie de Sentinel-2 es una estimación propia, contrastada con '
                    'EFFIS más abajo. Como cifra oficial, la de EFFIS o la de la comunidad autónoma.</p>\n'
                    '    <p>«Activo» quiere decir que el satélite vio calor en las últimas 24 horas, no que el incendio '
                    'siga sin controlar. Al revés, un incendio puede seguir ardiendo sin focos si el humo o las nubes '
                    'lo tapan o si arde bajo arbolado. Los focos aislados, uno o dos sin más señales, son a menudo '
                    'quemas agrícolas o de rastrojos. Por eso no se muestran salvo que se pida.</p>'),
        'species': ('<h3>Datos de censos de especies</h3>\n'
                    '    <p>El vigía no incorpora datos de censos de especies (colonias, nidos, dormideros ni territorios). '
                    'Esa información es interna de las entidades que la producen: no se publica aquí, no se guarda '
                    'en el repositorio y no se usa en ningún cálculo. Una ubicación precisa de una colonia junto '
                    'a un incendio puede poner en riesgo a la especie.</p>'),
        'open_data': ('<h3>Datos abiertos</h3>\n'
                      '    <p><a href="incendios.geojson">incendios.geojson</a> con todos los incendios y sus cruces '
                      '· <a href="quemado.geojson">quemado.geojson</a> con lo quemado según Sentinel-2 · <a href="feed.xml">fuente '
                      'Atom</a> de los incendios de la última semana · focos por año en CSV en el <a href="https://github.com/Asensio94/vigia-incendios/tree/main/data/focos">repositorio</a> '
                      '· <a href="https://github.com/Asensio94/vigia-incendios">código</a>.</p>'),
        'principle': ('Datos públicos, reglas a la vista y cada cifra enlazada a su fuente. Indicios, no veredictos.'),
        'credits': ('<p>Focos activos: NASA FIRMS (LANCE), parte del Earth Science Data and Information System de '
                    'la NASA · Áreas quemadas: EFFIS, Copernicus Emergency Management Service, © Unión Europea · '
                    'Imágenes Sentinel-2: Copernicus, © Unión Europea, vía Earth Search (Element 84) · Red Natura '
                    '2000 y CORINE Land Cover 2018: Agencia Europea de Medio Ambiente · Municipios: Nominatim, © '
                    'colaboradores de OpenStreetMap (ODbL) · Ortofoto PNOA: CC BY 4.0 scne.es.</p>'),
        'locale': '"es-ES"',
        'tz': '"Europe/Madrid"',
        'js_ago': ('h < 1 ? "hace menos de una hora" : h < 48 ? `hace ${Math.round(h)} h` : `hace ${Math.round(h/24)} '
                   'días`'),
        'js_tipo_label': 'esc(t[0].toUpperCase()+t.slice(1))',
        'js_ortho': ('const pnoa = L.tileLayer("https://www.ign.es/wmts/pnoa-ma?service=WMTS&request=GetTile&version=1.0.0&format=image/jpeg&layer=OI.OrthoimageCoverage&style=default&tilematrixset=GoogleMapsCompatible&tilematrix={z}&tilerow={y}&tilecol={x}",{maxZoom:20,attribution:"PNOA '
                     '© scne.es"});'),
        'js_s2_tip': ('Quemado según Sentinel-2: ${f.properties.nublado?"al menos ":""}${num(f.properties.ha)} ha${f.properties.definitivo?"":" '
                      '(provisional)"}'),
        'js_front_tip': 'Frente activo en la pasada de ',
        'js_layers': ('{"Mapa":osm,"Ortofoto PNOA":pnoa},{"Focos (7 días)":capaFocos,"Incendios":capaHuellas,"Frentes '
                      'activos":capaFrentes,"Quemado (Sentinel-2)":capaS2,"Perímetros EFFIS":capaEffis,"Red Natura '
                      '2000":capaNatura}'),
        'js_title': ('let s=l.municipio||l.provincia||"lugar sin nombre";\n'
                     '  if (l.provincia && l.provincia!==s) s+=` (${l.provincia})`; return (p.relevante?"Incendio '
                     'en ":"Foco aislado en ")+s;'),
        'js_prog_aria': 'aria-label="Superficie del perímetro tras cada pasada"',
        'js_prog_caption': ('Perímetro tras cada una de las ${r.length} pasadas: de ${num(r[0][1])} a ${num(r[r.length-1][1])} '
                            'ha.'),
        'js_cover_aria': 'aria-label="Cubierta del suelo"',
        'js_burns_on': '<p>Arde sobre ',
        'js_in_natura': ('q ? (q[e.codigo] ? `${nub?"al menos ":""}${num(q[e.codigo].ha)} ha quemadas`\n'
                         '                                     : nub ? `${num(e.ha)} ha de píxeles con focos` : "sin superficie '
                         'quemada dentro")\n'
                         '                       : `${num(e.ha)} ha de píxeles con focos`'),
        'js_more_sites': 'Y ${espacios.length-4} espacios más.',
        'js_effis': ('`<p class="nota">Perímetro EFFIS: <strong>${num(p.effis_ha)} ha</strong> quemadas${p.effis.length>1?` '
                     'en ${p.effis.length} áreas`:""}, actualizado el ${esc(p.effis.map(e=>e.actualizado).sort().pop())}.</p>`\n'
                     '    : p.relevante ? `<p class="nota">EFFIS aún no ha publicado su perímetro.</p>`'),
        'js_merged': ('Reúne ${p.unidos.length+1} incendios que se vieron por separado y luego se juntaron'),
        'js_seal_natura': '<span class="sello natura">Red Natura</span>',
        'js_seal_effis': '<span class="sello effis">Perímetro EFFIS</span>',
        'js_when': 'Primer foco <strong>${hora(p.primera)}</strong> · último <strong>',
        'js_dt_focos': '<dt>Focos</dt>',
        'js_dt_passes': '<dt>Pasadas</dt>',
        'js_dt_pixels': '<dt>Píxeles con focos</dt>',
        'js_dt_perimeter': '<dt>Perímetro estimado</dt>',
        'js_dt_front': '<dt>Frente activo</dt>',
        'js_dt_growth': '<dt>Crecimiento máximo</dt>',
        'js_dt_s2': '<dt>Quemado (Sentinel-2)</dt>',
        'js_dt_frp': '<dt>Potencia máxima</dt>',
        'js_actions': ('>Ver en el mapa</button>\n'
                       '      ${p.ficha?`<a href="${p.ficha}">Por pasadas</a>`:""}'
                       '<a href="${firms}">Focos en FIRMS</a><a href="#${esc(p.id)}">Enlace</a>'),
        'js_check': ('Compruébalo con las imágenes:\n'
                     '  <a href="${urlCB(s.fecha_antes,p)}" target="_blank" rel="noopener">antes (${dia(s.fecha_antes)})</a> '
                     '·\n'
                     '  <a href="${urlCB(s.fecha_despues,p)}" target="_blank" rel="noopener">después (${dia(s.fecha_despues)})</a>\n'
                     '  en Copernicus Browser. Lo quemado sale granate; la vegetación, verde.'),
        'js_s2_none': 'Aún no hay una imagen despejada de Sentinel-2 para medir lo quemado.',
        'js_s2_images': '${s.imagenes.length===1?"imagen":"imágenes"}, la última del ',
        'js_s2_cloudy': ('Las nubes tapan la zona de los focos en las imágenes de Sentinel-2 (${ult}): aún no se puede '
                         'medir lo quemado.'),
        'js_s2_nothing': ('Sentinel-2 no ve superficie quemada apreciable junto a los focos (${ult}). Suele pasar con quemas '
                          'agrícolas, con fuego bajo arbolado o si las nubes taparon la zona.'),
        'js_sev': '[["alta","--sev-alta"],["moderada","--sev-mod"],["baja","--sev-baja"]]',
        'js_s2_area': ('Superficie quemada estimada con Sentinel-2: <span class="cifra-q">${s.nublado?"al menos ":""}${num(s.ha)} '
                       'ha</span>${s.definitivo?"":" · <strong>provisional</strong>"}'),
        'js_sev_aria': 'aria-label="Severidad"',
        'js_sev_label': 'severidad ${k} ${num(s.severidad[k])} ha',
        'js_s2_notes': ('${ult}.${s.nublado?" Las nubes tapan buena parte de la zona: es un mínimo, no la superficie '
                        'total.":s.cobertura<0.8?" Las nubes taparon parte de la zona: la cifra puede quedarse corta.":""}${s.una_imagen>0.5?" '
                        'Medido con una sola imagen despejada: una bruma o la sombra de una nube junto al fuego pueden '
                        'pasar por quemado, así que la cifra puede sobrar. Se confirmará con la siguiente.":""}${s.definitivo||s.una_imagen>0.5?"":" '
                        'Se rehará cuando lleguen imágenes nuevas."}'),
        'js_empty': ('Ningún incendio cumple los filtros. ${per==="activo"?"Puede que no haya focos en las últimas '
                     '24 horas: prueba con los últimos 7 días.":""}'),
        'js_count': 'ok.length===1 ? "1 incendio" : `${ok.length} incendios`',
        'switch': '\n    <a class="pais" href="fr/" hreflang="fr">Francia</a>',
        'extra': '',
        'js_updated': 'hora(D.ahora).split(", ").pop()',
    },
    "fr": {
        "lang": '<html lang="fr">',
        "meta_description": ("Incendies avec des foyers actifs en France métropolitaine, vus par satellite toutes les "
                             "heures et croisés avec le réseau Natura 2000 et les surfaces brûlées d’EFFIS."),
        "project_title": "<title>Vigie des incendies</title>",
        "project_feed": 'title="Vigie des incendies"',
        "h1": "Vigie des <span>incendies</span>",
        "tagline": '<span class="rotulo">France métropolitaine · foyers vus par satellite · toutes les heures</span>',
        "switch": '\n    <a class="pais" href="../" hreflang="es">Espagne</a>',
        "lede": ("Les incendies avec des foyers actifs vus depuis l’espace, regroupés selon des règles fixes et "
                 "croisés avec le réseau Natura 2000 et avec les surfaces brûlées que cartographie EFFIS. Sans "
                 "attendre la statistique officielle, et sans la remplacer : un foyer est un pixel chaud, pas un "
                 "rapport d’intervention."),
        "fig_active": "<span>incendies avec des foyers ces dernières 24 h</span>",
        "fig_natura": "<span>d’entre eux dans le réseau Natura 2000</span>",
        "fig_isolated": "<span>foyers isolés en plus</span>",
        "fig_focos24": "<span>foyers ces dernières 24 h</span>",
        "fig_last": "<span>dernier foyer vu · vérifié à ",
        "map_aria": 'aria-label="Carte des incendies"',
        "legend_aria": 'aria-label="Légende"',
        "legend": ('      <span><i style="background:var(--f6)"></i>foyer de moins de 6 h</span>\n'
                   '      <span><i style="background:var(--f24)"></i>6–24 h</span>\n'
                   '      <span><i style="background:var(--f72)"></i>1–3 jours</span>\n'
                   '      <span><i style="background:var(--fviejo)"></i>3–7 jours</span>\n'
                   '      <span><i class="cuadro relleno"></i>brûlé selon Sentinel-2</span>\n'
                   '      <span><i class="cuadro" style="border-color:var(--effis)"></i>contour EFFIS</span>'),
        "filters": ('      <label>Période <select id="f-periodo">\n'
                    '        <option value="activo">Dernières 24 h</option><option value="semana" selected>7 derniers jours</option>\n'
                    '        <option value="temporada">__TEMPORADA__ derniers jours</option></select></label>\n'
                    '      <label>Brûle sur <select id="f-tipo"><option value="">Tout</option></select></label>\n'
                    '      <label><input type="checkbox" id="f-natura"> Natura 2000 seulement</label>\n'
                    '      <label><input type="checkbox" id="f-aislados"> Avec les foyers isolés</label>'),
        "method_title": "<h2>Comment c’est calculé</h2>",
        "steps": ("      <li>Toutes les heures, la vigie télécharge les foyers actifs que publie NASA FIRMS pour la "
                  "France métropolitaine, Corse comprise. Un foyer est un pixel de 375 mètres (VIIRS) ou d’un "
                  "kilomètre (MODIS) où le satellite a mesuré plus de chaleur que la normale lors d’un passage. "
                  "Il y a une dizaine de passages utiles par jour entre les cinq satellites, et FIRMS publie "
                  "chacun environ trois heures plus tard.</li>\n"
                  "      <li>Les foyers de faible confiance, souvent des reflets du soleil sur des toits ou des "
                  "serres, sont écartés, ainsi que ceux situés près de sources fixes de chaleur comme les "
                  "cimenteries, les aciéries ou les raffineries.</li>\n"
                  "      <li>Les autres sont regroupés en incendies : deux foyers appartiennent au même incendie si "
                  "leurs pixels sont à moins de deux kilomètres et ont été vus à moins de trois jours "
                  "d’intervalle, et une chaîne de foyers suffit à relier un front qui avance. Ce sont des règles "
                  "fixes : aucun modèle entraîné ni aucune intelligence artificielle n’intervient.</li>\n"
                  "      <li>Pour chaque incendie, la vigie calcule l’étendue de ses pixels, l’occupation du sol "
                  "d’après CORINE Land Cover 2018, les sites Natura 2000 qu’il touche et la commune, avec son "
                  "code INSEE. Quand EFFIS, le service européen des feux de forêt de Copernicus, publie le "
                  "contour brûlé, il est relié à l’incendie et sa surface devient la référence.</li>"),
        "params_title": "<h3>Paramètres</h3>",
        "glossary": GLOSARIO["fr"],
        "s2_section": ("<h3>Surface brûlée avec Sentinel-2</h3>\n"
                       "    <p>EFFIS met plusieurs jours à cartographier et ne dessine presque rien en dessous de "
                       "30 hectares. Pour ne pas attendre, la vigie mesure le brûlé avec les images de "
                       "Sentinel-2, qui passent tous les deux ou trois jours avec des pixels de 20 mètres. Elle "
                       "compare l’indice de surface brûlée (NBR) avant et après le feu : la végétation brûlée perd "
                       "de la réflectance dans le proche infrarouge et en gagne dans l’infrarouge à ondes courtes. "
                       "Seul compte ce qui change près des foyers et en contact avec eux, pour écarter les moissons "
                       "et les labours des mêmes semaines. Pour qu’une ombre de nuage ou une brume sur une seule "
                       "image ne passe pas pour de la cendre, un pixel n’est compté comme brûlé que si au moins deux "
                       "images le voient. Le calcul est refait à chaque nouvelle image, jusqu’à vingt jours après le "
                       "dernier foyer. Si les nuages couvrent plus de la moitié de la zone, le chiffre est donné "
                       "comme un minimum (« au moins ») ou n’est pas donné. Si le brûlé n’a été vu que sur une "
                       "image, ce filtre ne peut pas jouer : la fiche le signale et le chiffre n’est pas définitif "
                       "avant la suivante. Chaque fiche renvoie aux images d’avant et d’après dans Copernicus "
                       "Browser, pour que chacun puisse vérifier à l’œil ce que dit l’indice.</p>"),
        "val_title": "<h3>Validation sur 2022 et 2025</h3>",
        "val_intro": ("<p>Les mêmes règles, appliquées à l’archive de FIRMS de ces deux saisons — celle des "
                      "grands feux de Gironde et des Landes, puis celle de l’Aude —, ont été comparées à deux "
                      "références. Les surfaces brûlées d’EFFIS, comme en Espagne : un feu EFFIS compte comme vu "
                      "si son contour touche l’empreinte des foyers d’un incendie de la vigie aux mêmes dates. Et "
                      "BDIFF, la base officielle des incendies de forêt en France : elle ne donne pas de contour, "
                      "donc un feu BDIFF compte comme vu si l’empreinte d’un incendie de la vigie touche sa commune "
                      "et si la première alerte tombe dans ses dates. Le retard se mesure depuis l’heure de cette "
                      "première alerte.</p>"),
        "val_note": ('<p class="nota">Ceux qui échappent sont surtout des feux courts qui brûlent entre deux '
                     "passages ou sous les nuages ; face à BDIFF s’y ajoutent les feux dont la surface n’est "
                     'qu’estimée. Détail en <a href="https://github.com/Asensio94/vigia-incendios/blob/main/docs/'
                     'validation_fr.md">docs/validation_fr.md</a>.</p>'),
        "caveats": ("<h3>À savoir avant de le citer</h3>\n"
                    '    <p class="aviso">L’étendue des pixels avec des foyers n’est pas la surface brûlée. Pour '
                    "les petits feux elle l’exagère, car un feu d’un hectare allume un pixel de quatorze ; pour "
                    "les grands, elle peut rester en deçà. La surface Sentinel-2 est une estimation propre, "
                    "comparée à EFFIS plus bas. Comme chiffre officiel, celui d’EFFIS ou celui de BDIFF.</p>\n"
                    "    <p>« Actif » veut dire que le satellite a vu de la chaleur ces dernières 24 heures, pas que "
                    "le feu n’est pas maîtrisé. À l’inverse, un incendie peut continuer de brûler sans foyers si "
                    "la fumée ou les nuages le cachent, ou s’il brûle sous les arbres. Les foyers isolés, un ou "
                    "deux sans autre signe, sont souvent des brûlages agricoles ou d’écobuage. C’est pourquoi ils "
                    "ne sont montrés que sur demande.</p>"),
        "extra": ("\n    <h3>Sources françaises</h3>\n"
                  "    <p>Les foyers, Sentinel-2, CORINE Land Cover, Natura 2000 et EFFIS sont les mêmes sources "
                  "européennes et américaines qu’en Espagne. La France y ajoute trois sources nationales :</p>\n"
                  "    <ul>\n"
                  "      <li><strong>Communes</strong> : l’API Découpage administratif "
                  "(geo.api.gouv.fr, Etalab) donne pour chaque incendie la commune, son code INSEE, le "
                  "département et la région. Les communes de Corse gardent leur code en 2A et 2B.</li>\n"
                  "      <li><strong>BDIFF</strong>, la Base de données sur les incendies de forêts en France "
                  "(ministère de l’Agriculture, Licence Ouverte 2.0), sert à valider : elle recense chaque feu "
                  "avec sa commune, l’heure de la première alerte et la surface parcourue. Elle reprend aussi "
                  "les feux de l’arc méditerranéen que publiait Prométhée.</li>\n"
                  "      <li><strong>Orthophotographie</strong> de l’IGN (Géoplateforme), comme fond de carte.</li>\n"
                  "    </ul>\n"
                  "    <h3>Ce qui reste en dehors</h3>\n"
                  "    <p>Les départements et régions d’outre-mer (Guadeloupe, Martinique, Guyane, La Réunion, "
                  "Mayotte) et les autres territoires ne sont pas couverts : la vigie suit l’Europe, où Natura "
                  "2000, CORINE et EFFIS sont homogènes. BDIFF ne sert pas en temps réel : elle se complète une "
                  "fois par an, et la saison passée n’y entre qu’au printemps suivant. Une partie de ses surfaces "
                  "sont estimées et non mesurées, et elle situe chaque feu par sa commune, pas par un contour : "
                  "c’est une référence pour valider, pas pour mesurer.</p>"),
        "species": ("<h3>Données de suivi des espèces</h3>\n"
                    "    <p>La vigie n’intègre aucune donnée de suivi d’espèces (colonies, nids, dortoirs ou "
                    "territoires). Ces informations appartiennent aux organismes qui les produisent : elles ne sont "
                    "pas publiées ici, pas conservées dans le dépôt et pas utilisées dans les calculs. La position "
                    "précise d’une colonie près d’un incendie peut mettre l’espèce en danger.</p>"),
        "open_data": ("<h3>Données ouvertes</h3>\n"
                      '    <p><a href="incendios.geojson">incendios.geojson</a> avec tous les incendies et leurs '
                      'croisements · <a href="quemado.geojson">quemado.geojson</a> avec le brûlé selon '
                      'Sentinel-2 · <a href="feed.xml">flux Atom</a> des incendies de la dernière semaine · '
                      'foyers par an en CSV dans le <a href="https://github.com/Asensio94/vigia-incendios/tree/'
                      'main/data/fr/focos">dépôt</a> · <a href="https://github.com/Asensio94/vigia-incendios">'
                      "code</a>. Les champs des fichiers gardent leurs noms en espagnol, communs aux deux "
                      "pays.</p>"),
        "principle": ("Données publiques, règles visibles et chaque chiffre relié à sa source. Des indices, pas des "
                      "verdicts."),
        "credits": ("<p>Foyers actifs : NASA FIRMS (LANCE), partie de l’Earth Science Data and Information System "
                    "de la NASA · Surfaces brûlées : EFFIS, Copernicus Emergency Management Service, © Union "
                    "européenne · Images Sentinel-2 : Copernicus, © Union européenne, via Earth Search (Element "
                    "84) · Natura 2000 et CORINE Land Cover 2018 : Agence européenne pour l’environnement · "
                    "Communes : API Découpage administratif, geo.api.gouv.fr (Licence Ouverte 2.0) · Validation : "
                    "BDIFF, ministère de l’Agriculture et de la Souveraineté alimentaire (Licence Ouverte 2.0) · "
                    "Orthophotographie : © IGN, Géoplateforme.</p>"),
        # ── JS ──
        "locale": '"fr-FR"',
        "tz": '"Europe/Paris"',
        "js_updated": ('new Intl.DateTimeFormat("fr-FR",{timeZone:"Europe/Paris",hour:"2-digit",minute:"2-digit"})'
                       ".format(new Date(ms(D.ahora)))"),
        "js_ago": ('h < 1 ? "il y a moins d’une heure" : h < 48 ? `il y a ${Math.round(h)} h` : '
                   "`il y a ${Math.round(h/24)} jours`"),
        "js_tipo_label": ('esc({"vegetación natural":"Végétation naturelle","mixto":"Mixte","cultivos":"Cultures",'
                          '"suelo urbano o industrial":"Sol urbain ou industriel","sin datos":"Sans données"}[t]||t)'),
        "js_ortho": ('const pnoa = L.tileLayer("https://data.geopf.fr/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0'
                     '&LAYER=ORTHOIMAGERY.ORTHOPHOTOS&STYLE=normal&TILEMATRIXSET=PM&FORMAT=image/jpeg&TILEMATRIX={z}'
                     '&TILEROW={y}&TILECOL={x}",{maxZoom:19,attribution:"© IGN"});'),
        "js_s2_tip": ('Brûlé selon Sentinel-2 : ${f.properties.nublado?"au moins ":""}${num(f.properties.ha)} ha'
                      '${f.properties.definitivo?"":" (provisoire)"}'),
        "js_front_tip": "Front actif au passage de ",
        "js_layers": ('{"Carte":osm,"Orthophoto IGN":pnoa},{"Foyers (7 jours)":capaFocos,"Incendies":capaHuellas,'
                      '"Fronts actifs":capaFrentes,"Brûlé (Sentinel-2)":capaS2,"Contours EFFIS":capaEffis,'
                      '"Natura 2000":capaNatura}'),
        "js_title": ('let s=l.municipio||l.provincia||"lieu sans nom";\n'
                     '  if (l.provincia && l.provincia!==s) s+=` (${l.provincia})`; '
                     'return (p.relevante?"Incendie à ":"Foyer isolé à ")+s;'),
        "js_prog_aria": 'aria-label="Surface du périmètre après chaque passage"',
        "js_prog_caption": ("Périmètre après chacun des ${r.length} passages : de ${num(r[0][1])} à "
                            "${num(r[r.length-1][1])} ha."),
        "js_cover_aria": 'aria-label="Occupation du sol"',
        "js_burns_on": "<p>Brûle sur ",
        "js_in_natura": ('q ? (q[e.codigo] ? `${nub?"au moins ":""}${num(q[e.codigo].ha)} ha brûlés`\n'
                         '                                     : nub ? `${num(e.ha)} ha de pixels avec foyers` '
                         ': "aucune surface brûlée à l’intérieur")\n'
                         "                       : `${num(e.ha)} ha de pixels avec foyers`"),
        "js_more_sites": "Et ${espacios.length-4} sites de plus.",
        "js_effis": ('`<p class="nota">Contour EFFIS : <strong>${num(p.effis_ha)} ha</strong> brûlés'
                     '${p.effis.length>1?` en ${p.effis.length} zones`:""}, mis à jour le '
                     '${esc(p.effis.map(e=>e.actualizado).sort().pop())}.</p>`\n'
                     '    : p.relevante ? `<p class="nota">EFFIS n’a pas encore publié son contour.</p>`'),
        "js_merged": "Réunit ${p.unidos.length+1} incendies vus séparément qui se sont ensuite rejoints",
        "js_seal_natura": '<span class="sello natura">Natura 2000</span>',
        "js_seal_effis": '<span class="sello effis">Contour EFFIS</span>',
        "js_when": "Premier foyer <strong>${hora(p.primera)}</strong> · dernier <strong>",
        "js_dt_focos": "<dt>Foyers</dt>",
        "js_dt_passes": "<dt>Passages</dt>",
        "js_dt_pixels": "<dt>Pixels avec foyers</dt>",
        "js_dt_perimeter": "<dt>Périmètre estimé</dt>",
        "js_dt_front": "<dt>Front actif</dt>",
        "js_dt_growth": "<dt>Croissance maximale</dt>",
        "js_dt_s2": "<dt>Brûlé (Sentinel-2)</dt>",
        "js_dt_frp": "<dt>Puissance maximale</dt>",
        "js_actions": ('>Voir sur la carte</button>\n'
                       '      ${p.ficha?`<a href="${p.ficha}">Par passages</a>`:""}'
                       '<a href="${firms}">Foyers dans FIRMS</a><a href="#${esc(p.id)}">Lien</a>'),
        "js_check": ("Vérifiez avec les images :\n"
                     '  <a href="${urlCB(s.fecha_antes,p)}" target="_blank" rel="noopener">avant (${dia(s.fecha_antes)})</a> ·\n'
                     '  <a href="${urlCB(s.fecha_despues,p)}" target="_blank" rel="noopener">après (${dia(s.fecha_despues)})</a>\n'
                     "  dans Copernicus Browser. Le brûlé apparaît bordeaux ; la végétation, verte."),
        "js_s2_none": "Il n’y a pas encore d’image Sentinel-2 dégagée pour mesurer le brûlé.",
        "js_s2_images": '${s.imagenes.length===1?"image":"images"}, la dernière du ',
        "js_s2_cloudy": ("Les nuages couvrent la zone des foyers sur les images Sentinel-2 (${ult}) : le brûlé ne "
                         "peut pas encore être mesuré."),
        "js_s2_nothing": ("Sentinel-2 ne voit pas de surface brûlée notable près des foyers (${ult}). C’est courant "
                          "pour les brûlages agricoles, les feux sous couvert forestier ou si les nuages ont caché "
                          "la zone."),
        "js_sev": '[["alta","--sev-alta"],["moderada","--sev-mod"],["baja","--sev-baja"]]',
        "js_s2_area": ('Surface brûlée estimée avec Sentinel-2 : <span class="cifra-q">${s.nublado?"au moins ":""}'
                       '${num(s.ha)} ha</span>${s.definitivo?"":" · <strong>provisoire</strong>"}'),
        "js_sev_aria": 'aria-label="Sévérité"',
        "js_sev_label": 'sévérité ${{alta:"élevée",moderada:"modérée",baja:"faible"}[k]} ${num(s.severidad[k])} ha',
        "js_s2_notes": ('${ult}.${s.nublado?" Les nuages couvrent une bonne partie de la zone : c’est un minimum, '
                        'pas la surface totale.":s.cobertura<0.8?" Les nuages ont couvert une partie de la zone : '
                        'le chiffre peut être sous-estimé.":""}${s.una_imagen>0.5?" Mesuré avec une seule image '
                        'dégagée : une brume ou l’ombre d’un nuage près du feu peut passer pour du brûlé, le '
                        'chiffre peut donc être surestimé. Il sera confirmé avec la suivante.":""}'
                        '${s.definitivo||s.una_imagen>0.5?"":" Il sera recalculé à l’arrivée de nouvelles images."}'),
        "js_empty": ('Aucun incendie ne correspond aux filtres. ${per==="activo"?"Il n’y a peut-être pas eu de '
                     'foyers ces dernières 24 heures : essayez les 7 derniers jours.":""}'),
        "js_count": 'ok.length===1 ? "1 incendie" : `${ok.length} incendies`',
    },
}


# The common footer of the Terra Aperta projects, in the hub's menu order. This project is the
# second one and appears as plain text. French pages link each project's French page when it has one.
_HUB = {"es": ("https://asensio94.github.io/terra-aperta/", "← Terra Aperta: todos los proyectos", "Proyectos hermanos"),
        "fr": ("https://asensio94.github.io/terra-aperta/fr/", "← Terra Aperta : tous les projets", "Projets frères")}
_SIBLINGS = [  # (slug, Spanish name, French name, French page)
    ("sub-nocte", "Sub Nocte", "Sub Nocte", ""),
    ("vigia-incendios", "Vigía de incendios", "Vigie des incendies", "fr/"),
    ("centinela-natura", "Centinela Natura", "Centinela Natura", "fr/"),
    ("estado-iba", "Estado de las IBA", "État des IBA", "fr/"),
    ("riesgo-tendidos-aves", "Riesgo de tendidos para aves", "Risque des lignes pour les oiseaux", "regions.fr.html"),
    ("observatorio-alegaciones", "Observatorio de alegaciones", "Observatoire des consultations", ""),
    ("grafo-promotores", "Grafo de promotores", "Graphe des porteurs de projet", ""),
    ("vigilancia-humedales", "Vigilancia de humedales", "Veille des zones humides", "france.html"),
    ("caudal-ecologico", "Caudal ecológico", "Débit écologique", ""),
    ("acuiferos-francia", "Acuíferos de Francia", "Nappes de France", "fr/"),
    ("depuracion-y-bano", "Depuración y baño", "Épuration et baignade", "fr/"),
    ("zona-inundable", "Construir en zona inundable", "Construire en zone inondable", ""),
]


def siblings(lang: str) -> str:
    """The hub link and the list of sibling projects for the footer."""
    hub, back, label = _HUB[lang]
    items = []
    for slug, es, fr, fr_page in _SIBLINGS:
        name = fr if lang == "fr" else es
        if slug == "vigia-incendios":
            items.append(f'    <li aria-current="page">{name}</li>')
        else:
            href = f"https://asensio94.github.io/{slug}/" + (fr_page if lang == "fr" else "")
            items.append(f'    <li><a href="{href}">{name}</a></li>')
    return (f'<p><a href="{hub}">{back}</a></p>\n  <nav aria-label="{label}"><ul class="siblings">\n'
            + "\n".join(items) + "\n  </ul></nav>")


for _lang in UI:
    UI[_lang]["siblings"] = siblings(_lang)


def page(html: str, lang: str) -> str:
    """Fill every @@key@@ marker of the page template in `lang`."""
    for k, v in UI[lang].items():
        html = html.replace(f"@@{k}@@", v)
    return html


# Per-fire analysis page (ficha.py). Template markers @@key@@ are filled by ficha_page; the
# js_* entries go to the page script; the rest are used from Python.
_COMO_ES = [
    "Cada vez que un satélite pasa sobre el fuego, FIRMS (NASA) publica los píxeles con calor anómalo. Esta página "
    "agrupa en una <strong>pasada</strong> los píxeles de satélites que pasaron con menos de una hora de diferencia.",
    "Cada píxel VIIRS se dibuja con su tamaño real (unos 375 m en la vertical del satélite, más hacia los bordes de "
    "la pasada). El fuego está dentro de ese recuadro, no en todo él.",
    "El <strong>perímetro estimado</strong> se construye pasada a pasada con los píxeles VIIRS: un disco por píxel, un "
    "cierre morfológico de 0,75 km y nunca encoge. Cada pasada VIIRS deja una <strong>isocrona</strong>, del amarillo "
    "(primeras) al granate (últimas).",
    "Las pasadas solo de MODIS (píxeles de 1 km) encienden focos en el mapa pero no mueven el perímetro: lo inflarían.",
    "Los <strong>momentos clave</strong> salen de reglas fijas sobre esas cifras: el mayor salto del perímetro, la "
    "pasada de más potencia radiativa (FRP), el frente activo más largo, cuándo llega al 50 % y al 90 % de su tamaño "
    "final, la entrada en cada espacio Red Natura 2000 y los huecos de más de 18 horas sin observación.",
]
_COMO_FR = [
    "À chaque passage d’un satellite au-dessus du feu, FIRMS (NASA) publie les pixels présentant une chaleur anormale. "
    "Cette page regroupe en un <strong>passage</strong> les pixels de satellites passés à moins d’une heure d’écart.",
    "Chaque pixel VIIRS est dessiné à sa taille réelle (environ 375 m à la verticale du satellite, davantage vers les "
    "bords de la fauchée). Le feu se trouve dans ce rectangle, pas sur toute sa surface.",
    "Le <strong>périmètre estimé</strong> se construit passage après passage avec les pixels VIIRS : un disque par "
    "pixel, une fermeture morphologique de 0,75 km, et il ne rétrécit jamais. Chaque passage VIIRS laisse une "
    "<strong>isochrone</strong>, du jaune (premières) au grenat (dernières).",
    "Les passages MODIS seuls (pixels de 1 km) allument des foyers sur la carte mais ne font pas avancer le "
    "périmètre : ils le gonfleraient.",
    "Les <strong>moments clés</strong> découlent de règles fixes appliquées à ces chiffres : le plus grand bond du "
    "périmètre, le passage de plus forte puissance radiative (FRP), le front actif le plus long, l’atteinte de 50 % "
    "et de 90 % de la taille finale, l’entrée dans chaque site Natura 2000 et les trous de plus de 18 heures sans "
    "observation.",
]

FICHA: dict[str, dict] = {
    "es": {
        "locale": "es-ES",
        "meses": ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"],
        "sitio": "Vigía de incendios",
        "titulo": "Incendio de {sitio}",
        "sin_nombre": "lugar sin nombre",
        "meses_largos": ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
                         "octubre", "noviembre", "diciembre"],
        "titulo_hist": "{sitio}, {mes} de {anio}",
        "titulo_hist_dia": "{sitio}, {dia} de {mes} de {anio}",
        "descripcion": "{titulo}, pasada a pasada: focos VIIRS y MODIS, perímetro estimado y momentos clave.",
        "rotulo": "Análisis por pasadas",
        "lede": ("El incendio tal como lo vieron los satélites, pasada a pasada: los píxeles con calor, el perímetro "
                 "que van dibujando y los momentos en que cambió. No es una película continua: entre dos pasadas el "
                 "fuego avanza sin que nadie lo mida."),
        "volver": "← Grandes incendios",
        "tab_aria": "Secciones",
        "tab_mapa": "Mapa en directo",
        "tab_lista": "Grandes incendios",
        "l_titulo": "Grandes incendios",
        "l_rotulo": "España · desde 2022 · por pasadas de satélite",
        "l_descripcion": ("Los diez mayores incendios de cada temporada en España desde 2022 y los de este año de más de 100 ha, cada uno reconstruido pasada a pasada con los focos de FIRMS."),
        "l_lede": ("Los diez mayores incendios de cada temporada desde 2022 y los de este año que pasan de 100 ha, "
                   "con su superficie estimada a partir de los píxeles de satélite. Elige uno para verlo crecer pasada "
                   "a pasada."),
        "l_fig_n": "incendios",
        "l_fig_n_1": "incendio",
        "l_fig_ha": "estimadas en total",
        "l_fig_anios": "temporadas",
        "l_fig_natura": "tocan Red Natura 2000",
        "l_fig_natura_1": "toca Red Natura 2000",
        "l_buscar": "Buscar",
        "l_buscar_ph": "municipio, provincia, año…",
        "l_anio": "Año",
        "l_region": "Comunidad",
        "l_todos": "Todos",
        "l_todas": "Todas",
        "l_caption": "Incendios con ficha por pasadas, ordenados por superficie estimada",
        "l_c_incendio": "Incendio",
        "l_c_inicio": "Inicio",
        "l_c_dias": "Días",
        "l_c_ha": "Hectáreas",
        "l_c_pasadas": "Pasadas",
        "l_c_natura": "Espacios Natura",
        "l_en_curso": "activo",
        "l_vacio": "Ningún incendio cumple esos filtros.",
        "l_como_h": "Cómo se elige",
        "l_como_pasos": (
            "<li>Para cada temporada desde 2022 se descargan todos los focos del archivo estándar de FIRMS (VIIRS de "
            "Suomi NPP y NOAA-20, y MODIS) dentro de España, sin las fuentes fijas de calor.</li>"
            "<li>Se agrupan en incendios con las mismas reglas que el mapa en directo: focos a menos de 2 km y 72 h "
            "pertenecen al mismo incendio.</li>"
            "<li>De cada incendio se estima el perímetro con los píxeles VIIRS y se guardan los diez mayores de cada "
            "temporada que superan las 1.000 ha.</li>"
            "<li>Se nombran por el municipio de los primeros píxeles, que suele ser el del inicio del fuego. Los "
            "incendios de este año entran solos en cuanto superan 100 ha y su perímetro ha cambiado al menos una "
            "vez.</li>"),
        "l_limites": ("La superficie es una estimación desde el espacio: píxeles de 375 m, unidos y cerrados. Suele "
                      "acercarse a la cartografía oficial en incendios grandes y exagerar en los pequeños o con muchas "
                      "islas sin quemar. Dos incendios que se tocan pueden aparecer como uno. Las cifras oficiales son "
                      "las de EFFIS y las comunidades autónomas."),
        "fig_perimetro": "perímetro estimado con VIIRS",
        "fig_pasadas": "pasadas con focos ({viirs} de VIIRS)",
        "fig_dias": "días entre el primer y el último foco",
        "fig_hueco": "mediana entre pasadas",
        "fig_s2": "quemado según Sentinel-2",
        "fig_effis": "superficie según EFFIS",
        "aria_visor": "Reproducción del incendio",
        "aria_mapa": "Mapa en relieve del incendio",
        "sin_js": "El mapa y la línea de tiempo necesitan JavaScript. Los momentos clave están en la lista.",
        "play": "Reproducir",
        "anterior": "Pasada anterior",
        "siguiente": "Pasada siguiente",
        "aria_paso": "Pasada",
        "aria_curva": "Superficie del perímetro estimado a lo largo del tiempo",
        "curva_cap": ("Hectáreas del perímetro estimado. Es una escalera: solo cambia cuando pasa un satélite VIIRS "
                      "(rayas granates abajo; las grises son pasadas MODIS). Toca la curva para ir a una pasada."),
        "ley_actual": "píxeles de esta pasada",
        "ley_ceniza": "píxeles anteriores",
        "ley_iso": "isocronas, de la primera a la última",
        "ley_natura": "Red Natura 2000",
        "ley_s2": "quemado según Sentinel-2",
        "capa_3d": "Relieve 3D",
        "capa_orto": "Ortofoto",
        "capa_natura": "Red Natura",
        "capa_s2": "Quemado Sentinel-2",
        "momentos_h": "Momentos clave",
        "momentos_nota": "Toca uno para ver esa pasada en el mapa. Horas locales.",
        "como_h": "Cómo se calcula",
        "como_pasos": "".join(f"<li>{p}</li>" for p in _COMO_ES),
        "limites_h": "Lo que no puede decir",
        "limites": (
            "<p><strong>La resolución temporal la marcan los satélites.</strong> VIIRS va a bordo de tres satélites "
            "en la misma órbita, que pasan sobre España de madrugada (hacia la 1–3 h UTC) y a mediodía (12–14 h "
            "UTC): unas dos ventanas al día. MODIS añade pasadas por la mañana y la tarde, con píxeles de 1 km. "
            "Entre una pasada y otra no hay datos: un salto de 2.000 ha en una pasada nocturna puede haber ocurrido "
            "en cualquier momento de las horas anteriores.</p>"
            "<p><strong>La resolución espacial también.</strong> Un píxel VIIRS mide unos 375 m de lado (14 ha), pero "
            "un píxel encendido no significa 14 ha ardiendo: basta un frente de unos metros si está muy caliente. El "
            "perímetro estimado es una aproximación; la superficie real la da Sentinel-2 o EFFIS cuando el humo y las "
            "nubes lo permiten.</p>"
            "<p><strong>Nubes y humo esconden el fuego.</strong> Una pasada sin focos no quiere decir que el incendio "
            "se apagara. Los huecos de más de 18 horas aparecen marcados.</p>"
            "<p>En los incendios históricos se usa el archivo estándar de FIRMS, que no incluye el satélite "
            "NOAA-21: tienen algo menos de pasadas que los actuales.</p>"),
        "datos_h": "Datos",
        "glosario": GLOSARIO["es"],
        "datos_p": ("Focos: NASA FIRMS (VIIRS S-NPP, NOAA-20, NOAA-21 y MODIS). Relieve: Mapterhorn, con los MDT del IGN "
                    "(CC BY 4.0, scne.es). Red Natura 2000: MITECO / AEE. Los datos de esta página están en el JSON "
                    "que la acompaña, con el mismo nombre."),
        "creditos": ("Relieve © Mapterhorn (MDT del IGN, CC BY 4.0 scne.es; Copernicus GLO-30). Mapa base © "
                     "OpenStreetMap. Ortofoto PNOA © scne.es."),
        "al_menos": "al menos ",
        "m_inicio": "Primeros píxeles con calor.",
        "m_salto": "Mayor salto del perímetro: +{ha} ha en {horas} h{ritmo}.",
        "m_ritmo": " (unas {v} ha/h)",
        "m_potencia": "Pasada de más potencia: {frp} MW de energía radiativa.",
        "m_frente": "Frente activo más largo: {km} km.",
        "m_mitad": "Alcanza la mitad de su tamaño final ({ha} ha).",
        "m_noventa": "Llega al 90 % de su tamaño final ({ha} ha).",
        "m_natura": "El perímetro entra en {tipo} «{nombre}» ({codigo}).",
        "m_hueco": "{horas} h sin focos: nubes, humo o sin pasada. Pudo crecer sin verse.",
        "m_reactivacion": "Se reactiva tras {horas} h sin focos.",
        "m_ultimo": "Últimos píxeles con calor.",
        "m_s2": "Sentinel-2 mide {ha} ha quemadas.",
        "js_play": "Reproducir",
        "js_pausa": "Pausa",
        "js_pasada": "Pasada {k} de {n}",
        "js_pixel": "{n} píxel",
        "js_pixeles": "{n} píxeles",
        "js_solo_modis": "Solo MODIS (1 km): no mueve el perímetro.",
        "js_perimetro": "Perímetro estimado: {ha}.",
        "js_crece": "+{ha} ha desde la pasada VIIRS anterior.",
        "js_sin_perimetro": "Aún sin perímetro VIIRS.",
        "js_hueco": "Tras {h} h sin observación.",
        "ejemplos": ("Para ver el método en incendios que duraron días, los mayores desde 2022 están reproducidos pasada "
                     "a pasada en <a href=\"incendio/\">Grandes incendios</a>; por ejemplo {enlaces}."),
        "js_sin_webgl": "Este navegador no puede dibujar el mapa en 3D (WebGL). La curva y los momentos siguen funcionando.",
    },
    "fr": {
        "locale": "fr-FR",
        "meses": ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."],
        "sitio": "Vigie des incendies",
        "titulo": "Incendie de {sitio}",
        "sin_nombre": "lieu sans nom",
        "meses_largos": ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre",
                         "octobre", "novembre", "décembre"],
        "titulo_hist": "{sitio}, {mes} {anio}",
        "titulo_hist_dia": "{sitio}, {dia} {mes} {anio}",
        "descripcion": "{titulo}, passage par passage : foyers VIIRS et MODIS, périmètre estimé et moments clés.",
        "rotulo": "Analyse par passages",
        "lede": ("L’incendie tel que les satellites l’ont vu, passage après passage : les pixels chauds, le périmètre "
                 "qu’ils dessinent et les moments où il a changé. Ce n’est pas un film continu : entre deux passages, "
                 "le feu avance sans que personne ne le mesure."),
        "volver": "← Grands incendies",
        "tab_aria": "Sections",
        "tab_mapa": "Carte en direct",
        "tab_lista": "Grands incendies",
        "l_titulo": "Grands incendies",
        "l_rotulo": "France métropolitaine · depuis 2022 · par passages satellite",
        "l_descripcion": ("Les dix plus grands incendies de chaque saison en France métropolitaine depuis 2022 et ceux de cette année de plus de 100 ha, chacun reconstitué passage après passage avec les foyers FIRMS."),
        "l_lede": ("Les dix plus grands incendies de chaque saison depuis 2022 et ceux de cette année qui dépassent 100 ha, "
                   "avec leur surface estimée à partir des pixels satellite. Choisissez-en un pour le voir grandir "
                   "passage après passage."),
        "l_fig_n": "incendies",
        "l_fig_n_1": "incendie",
        "l_fig_ha": "estimés au total",
        "l_fig_anios": "saisons",
        "l_fig_natura": "touchent Natura 2000",
        "l_fig_natura_1": "touche Natura 2000",
        "l_buscar": "Rechercher",
        "l_buscar_ph": "commune, département, année…",
        "l_anio": "Année",
        "l_region": "Région",
        "l_todos": "Toutes",
        "l_todas": "Toutes",
        "l_caption": "Incendies avec une fiche par passages, classés par surface estimée",
        "l_c_incendio": "Incendie",
        "l_c_inicio": "Début",
        "l_c_dias": "Jours",
        "l_c_ha": "Hectares",
        "l_c_pasadas": "Passages",
        "l_c_natura": "Sites Natura",
        "l_en_curso": "actif",
        "l_vacio": "Aucun incendie ne correspond à ces filtres.",
        "l_como_h": "Comment ils sont choisis",
        "l_como_pasos": (
            "<li>Pour chaque saison depuis 2022, on télécharge tous les foyers de l’archive standard de FIRMS (VIIRS "
            "de Suomi NPP et NOAA-20, et MODIS) en France métropolitaine, sans les sources fixes de chaleur.</li>"
            "<li>Ils sont regroupés en incendies avec les mêmes règles que la carte en direct : des foyers à moins de "
            "2 km et 72 h appartiennent au même incendie.</li>"
            "<li>Pour chaque incendie, le périmètre est estimé avec les pixels VIIRS ; on garde les dix plus grands "
            "de chaque saison qui dépassent 1 000 ha.</li>"
            "<li>Ils portent le nom de la commune des premiers pixels, en général celle du départ du feu. Les "
            "incendies de l’année entrent d’eux-mêmes dès qu’ils dépassent 100 ha et que leur périmètre a changé au "
            "moins une fois.</li>"),
        "l_limites": ("La surface est une estimation depuis l’espace : pixels de 375 m, réunis et refermés. Elle "
                      "s’approche souvent de la cartographie officielle pour les grands feux et exagère les petits ou "
                      "ceux qui laissent beaucoup d’îlots intacts. Deux feux qui se touchent peuvent apparaître comme "
                      "un seul. Les chiffres officiels sont ceux d’EFFIS et de la BDIFF."),
        "fig_perimetro": "périmètre estimé avec VIIRS",
        "fig_pasadas": "passages avec foyers ({viirs} VIIRS)",
        "fig_dias": "jours entre le premier et le dernier foyer",
        "fig_hueco": "médiane entre passages",
        "fig_s2": "brûlé selon Sentinel-2",
        "fig_effis": "surface selon EFFIS",
        "aria_visor": "Reconstitution de l’incendie",
        "aria_mapa": "Carte en relief de l’incendie",
        "sin_js": "La carte et la frise chronologique nécessitent JavaScript. Les moments clés sont dans la liste.",
        "play": "Lecture",
        "anterior": "Passage précédent",
        "siguiente": "Passage suivant",
        "aria_paso": "Passage",
        "aria_curva": "Surface du périmètre estimé au fil du temps",
        "curva_cap": ("Hectares du périmètre estimé. C’est un escalier : il ne change qu’au passage d’un satellite "
                      "VIIRS (traits grenat en bas ; les gris sont des passages MODIS). Touchez la courbe pour aller "
                      "à un passage."),
        "ley_actual": "pixels de ce passage",
        "ley_ceniza": "pixels précédents",
        "ley_iso": "isochrones, de la première à la dernière",
        "ley_natura": "Natura 2000",
        "ley_s2": "brûlé selon Sentinel-2",
        "capa_3d": "Relief 3D",
        "capa_orto": "Orthophoto",
        "capa_natura": "Natura 2000",
        "capa_s2": "Brûlé Sentinel-2",
        "momentos_h": "Moments clés",
        "momentos_nota": "Touchez-en un pour voir ce passage sur la carte. Heures locales.",
        "como_h": "Méthode",
        "como_pasos": "".join(f"<li>{p}</li>" for p in _COMO_FR),
        "limites_h": "Ce qu’elle ne peut pas dire",
        "limites": (
            "<p><strong>La résolution temporelle dépend des satellites.</strong> VIIRS est embarqué sur trois "
            "satellites de la même orbite, qui passent au-dessus de la France la nuit (vers 1–3 h UTC) et à la "
            "mi-journée (12–14 h UTC) : environ deux fenêtres par jour. MODIS ajoute des passages le matin et "
            "l’après-midi, avec des pixels de 1 km. Entre deux passages il n’y a pas de données : un bond de "
            "2 000 ha lors d’un passage nocturne peut s’être produit à n’importe quel moment des heures "
            "précédentes.</p>"
            "<p><strong>La résolution spatiale aussi.</strong> Un pixel VIIRS mesure environ 375 m de côté (14 ha), "
            "mais un pixel allumé ne signifie pas 14 ha en feu : un front de quelques mètres suffit s’il est très "
            "chaud. Le périmètre estimé est une approximation ; la surface réelle vient de Sentinel-2 ou d’EFFIS "
            "quand la fumée et les nuages le permettent.</p>"
            "<p><strong>Nuages et fumée cachent le feu.</strong> Un passage sans foyers ne veut pas dire que "
            "l’incendie s’est éteint. Les trous de plus de 18 heures sont signalés.</p>"
            "<p>Pour les incendies historiques, on utilise l’archive standard de FIRMS, qui n’inclut pas le "
            "satellite NOAA-21 : ils comptent un peu moins de passages que les incendies actuels.</p>"),
        "datos_h": "Données",
        "glosario": GLOSARIO["fr"],
        "datos_p": ("Foyers : NASA FIRMS (VIIRS S-NPP, NOAA-20, NOAA-21 et MODIS). Relief : Mapterhorn, avec le RGE "
                    "ALTI et le LiDAR HD de l’IGN (Licence Ouverte 2.0). Natura 2000 : AEE. Les données de cette page "
                    "sont dans le JSON qui l’accompagne, du même nom."),
        "creditos": ("Relief © Mapterhorn (IGN RGE ALTI et LiDAR HD, Licence Ouverte 2.0 ; Copernicus GLO-30). "
                     "Fond de carte © OpenStreetMap. Orthophoto © IGN."),
        "al_menos": "au moins ",
        "m_inicio": "Premiers pixels chauds.",
        "m_salto": "Plus grand bond du périmètre : +{ha} ha en {horas} h{ritmo}.",
        "m_ritmo": " (environ {v} ha/h)",
        "m_potencia": "Passage le plus puissant : {frp} MW d’énergie radiative.",
        "m_frente": "Front actif le plus long : {km} km.",
        "m_mitad": "Atteint la moitié de sa taille finale ({ha} ha).",
        "m_noventa": "Atteint 90 % de sa taille finale ({ha} ha).",
        "m_natura": "Le périmètre entre dans la {tipo} « {nombre} » ({codigo}).",
        "m_hueco": "{horas} h sans foyers : nuages, fumée ou pas de passage. Il a pu grandir sans être vu.",
        "m_reactivacion": "Reprise après {horas} h sans foyers.",
        "m_ultimo": "Derniers pixels chauds.",
        "m_s2": "Sentinel-2 mesure {ha} ha brûlés.",
        "js_play": "Lecture",
        "js_pausa": "Pause",
        "js_pasada": "Passage {k} sur {n}",
        "js_pixel": "{n} pixel",
        "js_pixeles": "{n} pixels",
        "js_solo_modis": "MODIS seul (1 km) : ne fait pas avancer le périmètre.",
        "js_perimetro": "Périmètre estimé : {ha}.",
        "js_crece": "+{ha} ha depuis le passage VIIRS précédent.",
        "js_sin_perimetro": "Pas encore de périmètre VIIRS.",
        "js_hueco": "Après {h} h sans observation.",
        "ejemplos": ("Pour voir la méthode sur des incendies qui ont duré plusieurs jours, les plus grands depuis 2022 "
                     "sont reconstitués passage par passage dans <a href=\"incendio/\">Grands incendies</a> ; par "
                     "exemple {enlaces}."),
        "js_sin_webgl": "Ce navigateur ne peut pas afficher la carte en 3D (WebGL). La courbe et les moments fonctionnent.",
    },
}


def ficha_page(html: str, lang: str) -> str:
    """Fill the @@key@@ markers of the per-fire page template in `lang`."""
    for k, v in FICHA[lang].items():
        if isinstance(v, str):
            html = html.replace(f"@@{k}@@", v)
    return html
