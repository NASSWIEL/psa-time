import json
from datetime import date
from pathlib import Path

import pytest

import semaine
from semaine import ErreurConfig, charger, format_psa, plan, preparer, vendredi_cible

RACINE = Path(__file__).resolve().parent.parent

CONFIG = """
[[projets]]
code = "300000000011111"
activite = "projet"
heures_par_jour = 7.4

[[projets]]
code = "300000000022222"
activite = "PROJET"
heures_par_jour = 3.5
jours = ["jeudi", "Vendredi", "samedi"]

[cgi_information]
repos_11h = "Oui"
plage_8h_10h_16h30_19h = "Non"
plus_demi_journee = "N/A"
duree_pause = 1
localisation_matin = "auto"
localisation_apres_midi = "Regulier TLT"

[execution]
decalage_semaines = 0
"""

UN_PROJET = """
[[projets]]
code = "300000000011111"
activite = "PROJET"
heures_par_jour = 7.4
jours = ["lundi"]
"""


def ecrire(tmp_path, texte):
    chemin = tmp_path / "config.toml"
    chemin.write_text(texte, encoding="utf-8")
    return chemin


@pytest.mark.parametrize(
    "jour, attendu",
    [
        (date(2026, 10, 26), date(2026, 10, 30)),  # lundi
        (date(2026, 10, 30), date(2026, 10, 30)),  # vendredi
        (date(2026, 10, 31), date(2026, 10, 30)),  # samedi : semaine écoulée
        (date(2026, 11, 1), date(2026, 10, 30)),  # dimanche : semaine écoulée
        (date(2026, 12, 28), date(2027, 1, 1)),  # changement d'année
    ],
)
def test_vendredi_cible(jour, attendu):
    assert vendredi_cible(jour) == attendu


def test_vendredi_cible_decalage():
    assert vendredi_cible(date(2026, 10, 26), -1) == date(2026, 10, 23)
    assert vendredi_cible(date(2026, 10, 26), 1) == date(2026, 11, 6)


@pytest.mark.parametrize("valeur, attendu", [(7.4, "7,4"), (8, "8"), (7.25, "7,25"), (1.0, "1"), (0.5, "0,5")])
def test_format_psa(valeur, attendu):
    assert format_psa(valeur) == attendu


def test_plan_multi_projets(tmp_path):
    p = plan(charger(ecrire(tmp_path, CONFIG)), date(2026, 10, 26))
    assert p["date_fin"] == "30/10/2026"
    assert p["semaine"] == "du 25/10/2026 au 31/10/2026"
    assert [ligne["index"] for ligne in p["lignes"]] == [0, 1]
    assert p["lignes"][0]["activite"] == "PROJET"
    assert p["lignes"][0]["heures"] == {str(c): "7,4" for c in range(2, 7)}
    assert p["lignes"][1]["heures"] == {"5": "3,5", "6": "3,5", "7": "3,5"}
    assert p["total_semaine"] == "47,5"
    assert p["cgi"]["jours"] == [2, 3, 4, 5, 6, 7]  # samedi travaillé ajouté
    assert p["cgi"]["repos"] == ["Y", "N", "NA"]
    assert p["cgi"]["pause"] == "1"
    assert p["cgi"]["localisation_matin"] == "auto"
    assert p["cgi"]["localisation_apres_midi"] == "T"
    assert any("jeudi" in a for a in p["avertissements"])  # 10,9 h
    assert p["enregistrer"] is True
    assert p["soumettre"] is False  # brouillon par défaut


def test_option_soumettre(tmp_path):
    texte = CONFIG.replace("decalage_semaines = 0", "decalage_semaines = 0\nsoumettre = true")
    assert plan(charger(ecrire(tmp_path, texte)), date(2026, 10, 26))["soumettre"] is True


@pytest.mark.parametrize(
    "ajout, message",
    [
        ("soumettre = true\nenregistrer = false", "demande aussi enregistrer"),
        ('soumettre = "oui"', "true ou false"),
        ('enregistrer = "non"', "true ou false"),
    ],
)
def test_option_soumettre_invalide(tmp_path, ajout, message):
    texte = CONFIG.replace("decalage_semaines = 0", "decalage_semaines = 0\n" + ajout)
    with pytest.raises(ErreurConfig, match=message):
        charger(ecrire(tmp_path, texte))


def test_plan_bloc_cgi_meme_sans_heures(tmp_path):
    p = plan(charger(ecrire(tmp_path, UN_PROJET)), date(2026, 10, 26))
    assert p["lignes"][0]["heures"] == {"2": "7,4"}
    assert p["cgi"]["jours"] == [2, 3, 4, 5, 6]
    assert p["cgi"]["repos"] == ["Y", "Y", "Y"]
    assert p["cgi"]["localisation_matin"] == "auto"


def test_decalage_argument_prioritaire(tmp_path):
    p = plan(charger(ecrire(tmp_path, CONFIG)), date(2026, 10, 26), -1)
    assert p["date_fin"] == "23/10/2026"


@pytest.mark.parametrize(
    "remplacement, message",
    [
        (('code = "300000000011111"', 'code = "A_REMPLIR"'), "code projet"),
        (("heures_par_jour = 7.4", 'heures_par_jour = "7,4"'), "nombre"),
        (("heures_par_jour = 7.4", "heures_par_jour = 30"), "entre"),
        (('jours = ["jeudi", "Vendredi", "samedi"]', 'jours = ["jeudy"]'), "jours inconnus"),
        (('repos_11h = "Oui"', 'repos_11h = "Peut-être"'), "repos_11h"),
        (('localisation_apres_midi = "Regulier TLT"', 'localisation_apres_midi = "Plage"'), "valeur inconnue"),
        (("decalage_semaines = 0", 'decalage_semaines = "x"'), "entier"),
        (('activite = "projet"', 'activite = ""'), "activite"),
    ],
)
def test_erreurs_config(tmp_path, remplacement, message):
    with pytest.raises(ErreurConfig, match=message):
        charger(ecrire(tmp_path, CONFIG.replace(*remplacement, 1)))


def test_plus_de_24h(tmp_path):
    texte = CONFIG.replace("heures_par_jour = 3.5", "heures_par_jour = 20")
    with pytest.raises(ErreurConfig, match="24"):
        plan(charger(ecrire(tmp_path, texte)), date(2026, 10, 26))


def test_config_absente_ou_cassee(tmp_path):
    with pytest.raises(ErreurConfig, match="introuvable"):
        charger(tmp_path / "absent.toml")
    with pytest.raises(ErreurConfig, match="mal formé"):
        charger(ecrire(tmp_path, "[[projets]\ncode="))
    with pytest.raises(ErreurConfig, match="projets"):
        charger(ecrire(tmp_path, "[execution]\n"))


def test_modele_refuse_tant_que_non_rempli():
    with pytest.raises(ErreurConfig, match="code projet"):
        charger(RACINE / "config.example.toml")


def test_modele_valide_une_fois_rempli(tmp_path):
    texte = (RACINE / "config.example.toml").read_text(encoding="utf-8").replace('"A_REMPLIR"', '"300000000099999"')
    p = plan(charger(ecrire(tmp_path, texte)), date(2026, 10, 26))
    assert p["total_semaine"] == "37"


def test_preparer_injecte_le_plan(tmp_path):
    p = plan(charger(ecrire(tmp_path, CONFIG)), date(2026, 10, 26))
    ecrits = preparer(p, tmp_path / "run")
    noms = {f.name for f in ecrits}
    assert {"ouvrir_feuille.js", "saisir_projets.js", "remplir_cgi.js", "enregistrer.js", "soumettre.js"} <= noms
    for f in ecrits:
        contenu = f.read_text(encoding="utf-8")
        assert "/*PLAN*/null" not in contenu
        assert contenu.lstrip().startswith("async (page) =>")
    assert json.loads((tmp_path / "run" / "plan.json").read_text(encoding="utf-8")) == p


def test_modeles_js_contiennent_le_marqueur():
    modeles = list(semaine.DOSSIER_JS.glob("*.js"))
    assert modeles
    for f in modeles:
        assert "/*PLAN*/null" in f.read_text(encoding="utf-8"), f.name


def test_seul_soumettre_js_peut_soumettre():
    for f in semaine.DOSSIER_JS.iterdir():
        if f.name == "soumettre.js":
            continue
        for ligne in f.read_text(encoding="utf-8").splitlines():
            if "PB_SUBMIT" in ligne or "Soumettre" in ligne:
                assert ligne.strip().startswith("//"), f"{f.name} : {ligne.strip()}"


def test_soumettre_js_protege_par_l_option():
    texte = (semaine.DOSSIER_JS / "soumettre.js").read_text(encoding="utf-8")
    garde = texte.index("if (!PLAN.soumettre) return")
    assert garde < texte.index("PB_SUBMIT")
    assert garde < texte.index(".click(")


def test_cli_erreur(tmp_path, capsys):
    assert semaine.main(["--config", str(tmp_path / "absent.toml")]) == 1
    assert "ERREUR config" in capsys.readouterr().err
