"""BDIFF, la base de datos de incendios forestales de Francia, para validar en Francia.

La lleva el Ministerio de Agricultura (bdiff.agriculture.gouv.fr) con licencia Licence
Ouverte 2.0. Cada incendio trae su commune (código INSEE), la fecha y hora de la primera
alerta y la superficie recorrida, pero no su contorno: se cruza con el vigía por la commune.
Recoge también los del arco mediterráneo que antes publicaba Prométhée. Se completa una vez al
año: la última temporada entra la primavera siguiente.

La exportación va en dos pasos con la misma sesión: la búsqueda fija los años y el zip
descarga lo último que se buscó.
"""
from __future__ import annotations

import csv
import io
import ssl
import tempfile
import zipfile
from datetime import datetime
from functools import lru_cache
from zoneinfo import ZoneInfo

import certifi
import requests

from . import config

URL = "https://bdiff.agriculture.gouv.fr"
# El servidor envía un certificado intermedio que no es el que firma el suyo. El bueno está en
# la dirección AIA de su certificado; se añade a las autoridades de certifi y la cadena se
# sigue comprobando hasta una raíz de confianza, como hacen los navegadores.
INTERMEDIO = "http://crt.harica.gr/HARICA-GEANT-TLS-R1.cer"
PARIS = ZoneInfo("Europe/Paris")


@lru_cache(1)
def _autoridades() -> str:
    r = requests.get(INTERMEDIO, timeout=60, headers=config.UA)
    r.raise_for_status()
    pem = ssl.DER_cert_to_PEM_cert(r.content) if not r.content.startswith(b"-----") else r.text
    f = tempfile.NamedTemporaryFile("w", suffix=".pem", delete=False, encoding="ascii")
    f.write(open(certifi.where(), encoding="ascii").read() + "\n" + pem)
    f.close()
    return f.name


def descargar(anio: int) -> list[dict]:
    """Los incendios de un año, con la alerta en UTC y la superficie en hectáreas."""
    s = requests.Session()
    s.headers.update(config.UA)
    s.verify = _autoridades()
    s.get(f"{URL}/incendies", timeout=300, params={
        "if[periodeAnnees][anneeDeb]": anio, "if[periodeAnnees][anneeFin]": anio}).raise_for_status()
    r = s.get(f"{URL}/incendies/zip", timeout=600)
    r.raise_for_status()
    z = zipfile.ZipFile(io.BytesIO(r.content))
    crudo = z.read(next(n for n in z.namelist() if n.lower().endswith(".csv")))
    try:
        texto = crudo.decode("utf-8-sig")
    except UnicodeDecodeError:         # exportaciones antiguas
        texto = crudo.decode("latin-1")
    return leer(texto, anio)


def leer(texto: str, anio: int) -> list[dict]:
    lineas = texto.splitlines()
    cab = next(k for k, l in enumerate(lineas) if l.startswith("Ann"))
    out = []
    for f in csv.DictReader(io.StringIO("\n".join(lineas[cab:])), delimiter=";"):
        if str(f.get("Année", "")).strip() != str(anio):
            continue
        m2 = (f.get("Surface parcourue (m2)") or "").replace(" ", "").replace(",", ".")
        alerta = (f.get("Date de première alerte") or "").strip()
        try:
            t = datetime.strptime(alerta[:16], "%Y-%m-%d %H:%M").replace(tzinfo=PARIS)
        except ValueError:
            continue
        # Solo lo que hace falta para casar y citar el lugar: ni personas ni causas.
        out.append({"numero": f.get("Numéro", "").strip(), "insee": f.get("Code INSEE", "").strip(),
                    "commune": f.get("Nom de la commune", "").strip(),
                    "departement": f.get("Département", "").strip(),
                    "alerta": t.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%MZ"),
                    "ha": float(m2) / 10_000 if m2 else 0.0,
                    "precision": (f.get("Précision de la donnée") or f.get("Précision des surfaces") or "").strip()})
    return out
