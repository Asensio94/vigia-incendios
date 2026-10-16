"""Órdenes: `python -m vigia zonas | vigilar | web | validar`."""
from __future__ import annotations

import logging
import os

import typer
from rich import print

from . import config, effis, focos as F, incendios as I, web, zonas
from .config import Country

app = typer.Typer(add_completion=False, no_args_is_help=True)
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


def _paises(pais: str) -> list[Country]:
    return list(config.COUNTRIES.values()) if not pais else [config.COUNTRIES[pais.upper()]]


@app.command("zonas")
def cmd_zonas(pais: str = typer.Option("", help="ES o FR; por defecto, todos")) -> None:
    """Descarga las capas fijas de cada país: contorno, Red Natura 2000 y fuentes fijas de calor."""
    for c in _paises(pais):
        zonas.descargar_contorno(c)
        print(f"{c.code} · Red Natura 2000: {zonas.descargar_natura(c)} espacios")
        print(f"{c.code} · Fuentes fijas: {zonas.descargar_fijas(c)} celdas")


def _focos_en_juego(ahora: str, c: Country) -> list[dict]:
    """Todos los focos de un país de los años que toca la ventana de agrupado (años completos,
    porque F.guardar reescribe cada año entero)."""
    desde = F.hace(config.VENTANA_DIAS * 24, F._dt(ahora))
    return F.leer(c, desde[:4] + "-01-01")


@app.command("vigilar")
def cmd_vigilar(periodo: str = typer.Option("", help="24h, 48h o 7d; por defecto, según la última pasada")) -> None:
    """Una vuelta completa: focos nuevos, incendios, EFFIS, perímetros de Sentinel-2 y web."""
    from . import perimetro          # carga GDAL y compañía: solo cuando hace falta
    paises = config.COUNTRIES
    reg = {code: I.cargar(c) for code, c in paises.items()}
    ahora = F.iso(F.ahora())
    if not periodo:
        # Si la última vuelta fue hace más de 40 h (o no hubo), se pide la semana entera.
        ultimas = [r["actualizado"] for r in reg.values()]
        periodo = "7d" if not all(ultimas) or F.horas_entre(min(ultimas), ahora) > 40 else "48h"
    nuevos = F.descargar(periodo)
    todos, areas, resumen = {}, {}, {}
    for code, c in paises.items():
        n = F.anadir(nuevos[code], c)
        todos[code] = _focos_en_juego(ahora, c)
        res = I.actualizar(reg[code], todos[code], ahora, c)
        F.guardar(todos[code], c)
        areas[code] = effis.actualizar(c)
        con = effis.enlazar(reg[code]["incendios"], areas[code])
        resumen[code] = (n, res, con)
    # Un solo presupuesto de Sentinel-2 para todos: los incendios más grandes van primero.
    per = perimetro.actualizar({code: r["incendios"] for code, r in reg.items()}, ahora)
    if os.environ.get("GITHUB_OUTPUT"):        # el workflow guarda data/ si hay perímetros nuevos
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as fh:
            fh.write(f"perimetros={per['calculados']}\n")
    for code, c in paises.items():
        I.guardar(reg[code], c)
    I.guardar_cache()
    vivos = {code: web.construir(reg[code], todos[code], areas[code], c) for code, c in paises.items()}
    web.escribir_signals(vivos, ahora)
    for code, (n, res, con) in resumen.items():
        activos = [i for i in reg[code]["incendios"] if i.get("estado") == "activo"]
        print(f"{code} · FIRMS {periodo}: {len(nuevos[code])} focos, {n} nuevos · {res['incendios_nuevos']} "
              f"incendios nuevos, {res['unidos']} unidos · {len(activos)} activos "
              f"({sum(web.relevante(i) for i in activos)} no aislados) · {con} con perímetro EFFIS")
    print(f"Sentinel-2: {per['calculados']} calculados de {per['revisados']} revisados "
          f"({per['pendientes']} pendientes, {per['segundos']} s)")


@app.command("web")
def cmd_web() -> None:
    """Rehace la web con los datos guardados, sin descargar nada."""
    vivos, ahora = {}, None
    for code, c in config.COUNTRIES.items():
        reg = I.cargar(c)
        if not reg["actualizado"]:
            print(f"{code}: aún no hay incendios (ejecuta primero `vigilar`)")
            continue
        vivos[code] = web.construir(reg, _focos_en_juego(reg["actualizado"], c), effis.leer(c), c)
        ahora = max(ahora or "", reg["actualizado"])
        print(f"Web de {code} en {c.site}")
    if not vivos:
        raise typer.Exit(1)
    web.escribir_signals(vivos, ahora)


@app.command("validar")
def cmd_validar() -> None:
    """Contrasta las reglas con los incendios EFFIS de 2023 y 2024 (descarga el archivo de FIRMS)."""
    from . import validacion
    res = validacion.main()
    for a, r in res.items():
        print(a, [f"{c['detectados']}/{c['effis']}" for c in r["clases"]])
