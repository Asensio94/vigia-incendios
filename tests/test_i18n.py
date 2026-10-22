"""Each country's page in its language; the Spanish one exactly as it was."""
import re

from vigia import bdiff, i18n, web

NNBSP = " "


def test_french_numbers_use_a_narrow_space_for_thousands_and_before_percent():
    assert i18n.n(12552, "fr") == f"12{NNBSP}552"
    assert i18n.n(12552, "es") == "12.552"
    assert i18n.d(1234.5, "fr") == f"1{NNBSP}234,5"
    assert i18n.d(-0.25, "es", 2) == "-0,25"
    assert i18n.p(0.91, "fr") == f"91{NNBSP}%"
    assert i18n.p(0.91, "es") == "91 %"


def test_every_marker_of_the_page_has_a_text_in_both_languages():
    markers = set(re.findall(r"@@(\w+)@@", web.PLANTILLA))
    assert markers == set(i18n.UI["es"]) == set(i18n.UI["fr"])
    for lang in ("es", "fr"):
        assert "@@" not in i18n.page(web.PLANTILLA, lang)


def test_the_french_page_is_in_french():
    html = i18n.page(web.PLANTILLA, "fr")
    assert '<html lang="fr">' in html and "Vigie des incendies" in html
    assert '"fr-FR"' in html and '"es-ES"' not in html and "Europe/Paris" in html
    for es in ("Cómo se calcula", "Red Natura</span>", "Incendio en ", "Últimos 7 días"):
        assert es not in html


def test_french_fire_title_and_feed():
    i = {"id": "FR-IN-20250805-001", "n_focos": 40, "pasadas": 9, "ha_focos": 1234.5, "primera": "2025-08-05T13:30Z",
         "ultima": "2025-08-07T02:10Z", "lugar": {"municipio": "Fabrezan", "provincia": "Aude"},
         "cobertura": {"matorral": 0.8, "agricola": 0.2}, "estado": "inactivo"}
    assert web._titulo(i, "fr") == "Incendie à Fabrezan (Aude)"
    assert web._titulo(i) == "Incendio en Fabrezan (Aude)"
    r = web._resumen_fr(i)
    assert r.startswith("40 foyers en 9 passages") and f"1{NNBSP}234,5 ha" in r
    assert "végétation naturelle" in r


def test_bdiff_export_reads_commune_alert_in_utc_and_hectares_only():
    texto = ('"Nombre d\'incendies suivant les critères de sélection : 2"\n'
             'Année;Numéro;Département;"Code INSEE";"Nom de la commune";"Date de première alerte";'
             '"Surface parcourue (m2)";"Précision de la donnée"\n'
             '2022;11421;"33";"33225";"Landiras";"2022-07-12 16:31:00";125520000;"Mesurées"\n'
             '2021;1;"2A";"2A004";"Ajaccio";"2021-07-01 10:00:00";5000;""\n')
    [f] = bdiff.leer(texto, 2022)
    assert f == {"numero": "11421", "insee": "33225", "commune": "Landiras", "departement": "33",
                 "alerta": "2022-07-12T14:31Z", "ha": 12552.0, "precision": "Mesurées"}


def test_header_figures_agree_with_their_number():
    assert i18n.singular(1, "es") and not i18n.singular(0, "es") and not i18n.singular(2, "es")
    assert i18n.singular(1, "fr") and i18n.singular(0, "fr") and not i18n.singular(2, "fr")
    assert set(i18n.SINGULAR["es"]) == set(i18n.SINGULAR["fr"])
    for k in i18n.SINGULAR["fr"]:
        assert f"@@{k}@@" in web.PLANTILLA


def test_language_switch_names_the_other_country_in_the_page_language():
    assert ">Espagne</a>" in i18n.page(web.PLANTILLA, "fr") and "España</a>" not in i18n.page(web.PLANTILLA, "fr")
    assert ">Francia</a>" in i18n.page(web.PLANTILLA, "es")


def test_every_page_explains_its_acronyms():
    for lang in ("es", "fr"):
        assert 'class="glosario"' in i18n.page(web.PLANTILLA, lang)
        assert "dNBR" in i18n.GLOSARIO[lang] and "FEDS" in i18n.GLOSARIO[lang]
        assert i18n.FICHA[lang]["glosario"] == i18n.GLOSARIO[lang]
