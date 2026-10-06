"""Órdenes: `python -m vigia zonas | vigilar | web | validar`."""
from __future__ import annotations

import json
import logging

import typer
from rich import print

from . import config, effis, focos as F, incendios as I, web, zonas

app = typer.Typer(add_completion=False, no_args_is_help=True)
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


@app.command("zonas")
def cmd_zonas() -> None:
    """Descarga las capas fijas: contorno de España, Red Natura 2000 y fuentes fijas de calor."""
    zonas.descargar_espana()
    print(f"Red Natura 2000: {zonas.descargar_natura()} espacios")
    print(f"Fuentes fijas: {zonas.descargar_fijas()} celdas")


def _focos_en_juego(ahora: str) -> list[dict]:
    """Todos los focos de los años que toca la ventana de agrupado (años completos, porque
    F.guardar reescribe cada año entero)."""
    desde = F.hace(config.VENTANA_DIAS * 24, F._dt(ahora))
    return F.leer(desde[:4] + "-01-01")


@app.command("vigilar")
def cmd_vigilar(periodo: str = typer.Option("", help="24h, 48h o 7d; por defecto, según la última pasada")) -> None:
    """Una vuelta completa: focos nuevos, incendios, EFFIS y web."""
    reg = I.cargar()
    ahora = F.iso(F.ahora())
    if not periodo:
        # Si la última vuelta fue hace más de 40 h (o no hubo), se pide la semana entera.
        periodo = "7d" if not reg["actualizado"] or F.horas_entre(reg["actualizado"], ahora) > 40 else "48h"
    nuevos = F.descargar(periodo)
    n = F.anadir(nuevos)
    todos = _focos_en_juego(ahora)
    res = I.actualizar(reg, todos, ahora)
    F.guardar(todos)
    areas = effis.actualizar()
    con = effis.enlazar(reg["incendios"], areas)
    I.guardar(reg)
    I.guardar_cache()
    web.construir(reg, todos, areas)
    activos = [i for i in reg["incendios"] if i.get("estado") == "activo"]
    print(f"FIRMS {periodo}: {len(nuevos)} focos, {n} nuevos · {res['incendios_nuevos']} incendios nuevos, "
          f"{res['unidos']} unidos · {len(activos)} activos ({sum(web.relevante(i) for i in activos)} no aislados) · "
          f"{con} con perímetro EFFIS")


@app.command("web")
def cmd_web() -> None:
    """Rehace la web con los datos guardados, sin descargar nada."""
    reg = I.cargar()
    if not reg["actualizado"]:
        raise typer.Exit("Aún no hay incendios: ejecuta primero `vigilar`.")
    areas = (json.loads(config.EFFIS_JSON.read_text(encoding="utf-8"))["areas"]
             if config.EFFIS_JSON.exists() else [])
    web.construir(reg, _focos_en_juego(reg["actualizado"]), areas)
    print(f"Web en {config.SITE}")


@app.command("validar")
def cmd_validar() -> None:
    """Contrasta las reglas con los incendios EFFIS de 2023 y 2024 (descarga el archivo de FIRMS)."""
    from . import validacion
    res = validacion.main()
    for a, r in res.items():
        print(a, [f"{c['detectados']}/{c['effis']}" for c in r["clases"]])
