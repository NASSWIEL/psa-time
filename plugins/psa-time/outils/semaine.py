"""Lit config.toml, calcule la semaine cible et prépare le plan de saisie PSA Time.

Usage :
    python semaine.py                        # affiche le plan (JSON)
    python semaine.py -1                     # semaine précédente
    python semaine.py --preparer --run DIR   # écrit aussi DIR/plan.json et les scripts Playwright
"""

import argparse
import json
import sys
import tomllib
from datetime import date, timedelta
from pathlib import Path

from chemins import CONFIG, RUN_DEFAUT, console_utf8

DOSSIER_JS = Path(__file__).resolve().parent / "js"

# Colonnes PSA : TIME1 = dimanche ... TIME7 = samedi.
COLONNES = {"dimanche": 1, "lundi": 2, "mardi": 3, "mercredi": 4, "jeudi": 5, "vendredi": 6, "samedi": 7}
SEMAINE_OUVREE = ["lundi", "mardi", "mercredi", "jeudi", "vendredi"]
REPONSES = {"oui": "Y", "non": "N", "n/a": "NA", "na": "NA"}
LOCALISATIONS = {
    "cgi": "O",
    "regulier tlt": "T",
    "ponctuel tlt": "P",
    "exceptionel tlt": "E",
    "exceptionnel tlt": "E",
    "site client": "C",
    "grand déplacement": "GD",
    "grand deplacement": "GD",
    "n/a": "NA",
    "navette airbus": "NAV",
    "vélo site cgi": "VCGI",
    "velo site cgi": "VCGI",
    "vélo site client": "VCLI",
    "velo site client": "VCLI",
}


class ErreurConfig(ValueError):
    pass


def vendredi_cible(aujourdhui: date, decalage: int = 0) -> date:
    # Le week-end, la semaine à déclarer est celle qui vient de se terminer (écart négatif).
    return aujourdhui + timedelta(days=4 - aujourdhui.weekday() + 7 * decalage)


def format_psa(valeur: float) -> str:
    texte = f"{valeur:.2f}".rstrip("0").rstrip(".")
    return texte.replace(".", ",")


def _nombre(valeur, nom: str, mini: float, maxi: float) -> float:
    if isinstance(valeur, bool) or not isinstance(valeur, (int, float)):
        raise ErreurConfig(f"{nom} doit être un nombre (reçu : {valeur!r}). Utilise un point : 7.4")
    if not mini <= valeur <= maxi:
        raise ErreurConfig(f"{nom} doit être entre {mini} et {maxi} (reçu : {valeur}).")
    return float(valeur)


def _reponse(valeur, nom: str) -> str:
    code = REPONSES.get(str(valeur).strip().lower())
    if not code:
        raise ErreurConfig(f"{nom} doit valoir \"Oui\", \"Non\" ou \"N/A\" (reçu : {valeur!r}).")
    return code


def _localisation(valeur, nom: str) -> str:
    texte = str(valeur).strip().lower()
    if texte == "auto":
        return "auto"
    code = LOCALISATIONS.get(texte)
    if not code:
        choix = ", ".join(sorted({k.title() for k in LOCALISATIONS if "é" not in k}))
        raise ErreurConfig(f"{nom} : valeur inconnue {valeur!r}. Mets \"auto\" ou une de : {choix}.")
    return code


def charger(chemin: Path = CONFIG) -> dict:
    if not chemin.exists():
        raise ErreurConfig(
            f"Fichier {chemin} introuvable. Lance /psa-time:prise-en-main (ou outils/verifier.py) "
            "pour le créer depuis le modèle."
        )
    try:
        brut = tomllib.loads(chemin.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as e:
        raise ErreurConfig(f"{chemin.name} mal formé : {e}") from None

    projets = brut.get("projets")
    if not isinstance(projets, list) or not projets:
        raise ErreurConfig("Ajoute au moins un bloc [[projets]] dans config.toml.")

    lignes = []
    for i, p in enumerate(projets, start=1):
        nom = f"projet n°{i}"
        code = str(p.get("code", "")).strip()
        if not code or code.upper() == "A_REMPLIR":
            raise ErreurConfig(f"{nom} : renseigne ton vrai code projet PSA dans 'code' (modèle non modifié ?).")
        activite = str(p.get("activite", "")).strip().upper()
        if not activite:
            raise ErreurConfig(f"{nom} : renseigne 'activite' (ex. \"PROJET\").")
        heures = _nombre(p.get("heures_par_jour"), f"{nom} heures_par_jour", 0.25, 24)
        jours = p.get("jours", SEMAINE_OUVREE)
        if isinstance(jours, str):
            jours = [jours]
        jours = [str(j).strip().lower() for j in jours]
        inconnus = [j for j in jours if j not in COLONNES]
        if inconnus:
            raise ErreurConfig(f"{nom} : jours inconnus {inconnus}. Valeurs possibles : {', '.join(COLONNES)}.")
        if not jours:
            raise ErreurConfig(f"{nom} : 'jours' est vide.")
        lignes.append({"code": code, "activite": activite, "heures_par_jour": heures, "jours": sorted(set(jours), key=COLONNES.get)})

    cgi = brut.get("cgi_information", {})
    execution = brut.get("execution", {})
    enregistrer = execution.get("enregistrer", True)
    soumettre = execution.get("soumettre", False)
    if not isinstance(enregistrer, bool) or not isinstance(soumettre, bool):
        raise ErreurConfig("enregistrer et soumettre doivent valoir true ou false (sans guillemets).")
    if soumettre and not enregistrer:
        raise ErreurConfig("soumettre = true demande aussi enregistrer = true.")
    decalage = execution.get("decalage_semaines", 0)
    if isinstance(decalage, bool) or not isinstance(decalage, int):
        raise ErreurConfig("decalage_semaines doit être un entier (0, -1, ...).")

    return {
        "projets": lignes,
        "repos": [
            _reponse(cgi.get("repos_11h", "Oui"), "repos_11h"),
            _reponse(cgi.get("plage_8h_10h_16h30_19h", "Oui"), "plage_8h_10h_16h30_19h"),
            _reponse(cgi.get("plus_demi_journee", "Oui"), "plus_demi_journee"),
        ],
        "pause": _nombre(cgi.get("duree_pause", 1.0), "duree_pause", 0, 4),
        "localisation_matin": _localisation(cgi.get("localisation_matin", "auto"), "localisation_matin"),
        "localisation_apres_midi": _localisation(cgi.get("localisation_apres_midi", "auto"), "localisation_apres_midi"),
        "decalage_semaines": decalage,
        "enregistrer": enregistrer,
        "soumettre": soumettre,
    }


def plan(config: dict, aujourdhui: date, decalage: int | None = None) -> dict:
    decalage = config["decalage_semaines"] if decalage is None else decalage
    vendredi = vendredi_cible(aujourdhui, decalage)
    dimanche = vendredi - timedelta(days=5)

    totaux = {j: 0.0 for j in COLONNES}
    lignes = []
    for index, p in enumerate(config["projets"]):
        heures = {}
        for jour in p["jours"]:
            heures[str(COLONNES[jour])] = format_psa(p["heures_par_jour"])
            totaux[jour] += p["heures_par_jour"]
        lignes.append({"index": index, "code": p["code"], "activite": p["activite"], "heures": heures})

    avertissements = []
    for jour, total in totaux.items():
        if total > 24:
            raise ErreurConfig(f"{jour} : {total} h au total sur tous les projets, plus de 24 h.")
        if total > 10:
            avertissements.append(f"{jour} : {format_psa(total)} h au total, vérifie que c'est voulu.")

    # Le bloc CGI se remplit lundi à vendredi même sans heures, plus les jours de week-end travaillés.
    jours_cgi = sorted({COLONNES[j] for j in SEMAINE_OUVREE} | {COLONNES[j] for j, t in totaux.items() if t > 0})

    return {
        "date_fin": vendredi.strftime("%d/%m/%Y"),
        "semaine": f"du {dimanche.strftime('%d/%m/%Y')} au {(dimanche + timedelta(days=6)).strftime('%d/%m/%Y')}",
        "lignes": lignes,
        "total_semaine": format_psa(sum(totaux.values())),
        "cgi": {
            "jours": jours_cgi,
            "repos": config["repos"],
            "pause": format_psa(config["pause"]),
            "localisation_matin": config["localisation_matin"],
            "localisation_apres_midi": config["localisation_apres_midi"],
        },
        "enregistrer": config["enregistrer"],
        "soumettre": config["soumettre"],
        "avertissements": avertissements,
    }


def preparer(donnees: dict, dossier: Path = RUN_DEFAUT) -> list[Path]:
    """Écrit plan.json et les scripts Playwright avec le plan intégré, lus ensuite par browser_run_code_unsafe."""
    dossier.mkdir(parents=True, exist_ok=True)
    (dossier / "plan.json").write_text(json.dumps(donnees, ensure_ascii=False, indent=2), encoding="utf-8")
    ecrits = []
    plan_js = json.dumps(donnees, ensure_ascii=False)
    for modele in sorted(DOSSIER_JS.glob("*.js")):
        cible = dossier / modele.name
        cible.write_text(modele.read_text(encoding="utf-8").replace("/*PLAN*/null", plan_js), encoding="utf-8")
        ecrits.append(cible)
    return ecrits


def main(argv=None) -> int:
    console_utf8()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("decalage", nargs="?", type=int, help="semaines de décalage (0 = semaine en cours, -1 = précédente)")
    parser.add_argument("--config", type=Path, default=CONFIG)
    parser.add_argument("--preparer", action="store_true", help="écrit le plan et les scripts dans --run")
    parser.add_argument("--run", type=Path, default=RUN_DEFAUT, help="dossier des scripts générés")
    args = parser.parse_args(argv)

    try:
        donnees = plan(charger(args.config), date.today(), args.decalage)
    except ErreurConfig as e:
        print(f"ERREUR config : {e}", file=sys.stderr)
        return 1

    if args.preparer:
        preparer(donnees, args.run)
    print(json.dumps(donnees, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
