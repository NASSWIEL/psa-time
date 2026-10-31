"""Vérifie que le poste peut lancer la saisie PSA Time et explique quoi faire sinon.

Crée aussi config.toml s'il manque (depuis le modèle du plugin). Les identifiants PSA sont dans le coffre
d'identifiants Windows (identifiants.py), jamais dans un fichier.

Usage :
    python verifier.py                 # rapport lisible
    python verifier.py --json          # rapport pour les skills
    python verifier.py --rapide        # sans le test de téléchargement du MCP Playwright
    python verifier.py --profil DIR    # vérifie aussi que ce profil Edge n'est pas déjà ouvert
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from chemins import CODE, CONFIG, DONNEES, ENV, console_utf8  # noqa: E402

VERSION_MCP = "0.0.75"
CHEMINS_EDGE = [
    Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")) / "Microsoft/Edge/Application/msedge.exe",
    Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")) / "Microsoft/Edge/Application/msedge.exe",
    Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/Edge/Application/msedge.exe",
]


@dataclass
class Controle:
    nom: str
    ok: bool
    detail: str
    consigne: str = ""
    bloquant: bool = True


def _version(texte: str) -> tuple[int, ...]:
    m = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", texte or "")
    return tuple(int(x or 0) for x in m.groups()) if m else (0,)


def _executer(commande: list[str], delai: int = 30) -> tuple[int, str]:
    try:
        r = subprocess.run(commande, capture_output=True, text=True, timeout=delai, encoding="utf-8", errors="replace")
        return r.returncode, (r.stdout + r.stderr).strip()
    except FileNotFoundError:
        return 127, "introuvable"
    except subprocess.TimeoutExpired:
        return 124, f"délai de {delai} s dépassé"


def controle_systeme() -> Controle:
    ok = sys.platform == "win32"
    return Controle(
        "Windows",
        ok,
        sys.platform,
        "" if ok else "L'outil est prévu pour Windows avec Microsoft Edge (poste CGI).",
        bloquant=False,
    )


def controle_python() -> Controle:
    v = sys.version_info
    ok = v >= (3, 11)
    return Controle(
        "Python 3.11+",
        ok,
        f"{v.major}.{v.minor}.{v.micro}",
        "" if ok else "Installe Python 3.12 depuis le Microsoft Store (sans droits admin) ou python.org "
        "en cochant « Add python.exe to PATH » et « Install for current user ».",
    )


def controle_node() -> Controle:
    node = shutil.which("node")
    if not node:
        return Controle(
            "Node.js 18+",
            False,
            "node introuvable dans le PATH",
            "Installe Node.js LTS sans droits admin : `winget install OpenJS.NodeJS.LTS --scope user`, "
            "ou télécharge le .zip Windows sur nodejs.org, dézippe-le dans ton dossier utilisateur et ajoute "
            "ce dossier au PATH utilisateur. Ferme et rouvre Claude Code ensuite.",
        )
    code, sortie = _executer([node, "--version"])
    ok = code == 0 and _version(sortie) >= (18,)
    return Controle("Node.js 18+", ok, sortie, "" if ok else "Mets Node.js à jour en version LTS (18 ou plus).")


def controle_npx() -> Controle:
    ok = bool(shutil.which("npx"))
    return Controle("npx", ok, "présent" if ok else "introuvable", "" if ok else "npx est livré avec Node.js : réinstalle Node.js LTS.")


def controle_edge() -> Controle:
    trouve = next((p for p in CHEMINS_EDGE if p.exists()), None)
    return Controle(
        "Microsoft Edge",
        bool(trouve),
        str(trouve) if trouve else "msedge.exe introuvable",
        "" if trouve else "Installe Microsoft Edge (Centre logiciel CGI) : le plugin pilote Edge.",
    )


def controle_mcp() -> Controle:
    npx = shutil.which("npx")
    if not npx:
        return Controle(f"MCP Playwright {VERSION_MCP}", False, "npx absent", "Installe d'abord Node.js.")
    code, sortie = _executer([npx, "-y", f"@playwright/mcp@{VERSION_MCP}", "--version"], delai=240)
    if code == 0:
        versions = re.findall(r"\b\d+\.\d+\.\d+\b", sortie)
        return Controle(f"MCP Playwright {VERSION_MCP}", True, f"version {versions[-1]}" if versions else "téléchargé")
    consigne = "Le téléchargement npm a échoué."
    if re.search(r"ETIMEDOUT|ECONNREFUSED|ENOTFOUND|proxy|SELF_SIGNED|certificate", sortie, re.I):
        consigne += (
            " Réseau/proxy d'entreprise probable : `npm config set proxy http://<proxy>:<port>` et "
            "`npm config set https-proxy http://<proxy>:<port>` (demande l'adresse au support), "
            "ou réessaie hors VPN."
        )
    return Controle(f"MCP Playwright {VERSION_MCP}", False, sortie[-300:], consigne)


def creer_depuis_modele(cible: Path, modele: str) -> bool:
    if cible.exists():
        return False
    cible.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(CODE / modele, cible)
    return True


def controle_identifiants() -> Controle:
    import identifiants
    from servir_env import verifier_env

    outil = (CODE / "outils" / "identifiants.py").as_posix()
    if identifiants.present():
        return Controle("Identifiants PSA", True, "dans le coffre d'identifiants Windows")
    if ENV.exists() and not verifier_env(ENV):
        return Controle(
            "Identifiants PSA",
            True,
            f"ancien fichier {ENV.as_posix()} (encore accepté)",
            f"Conseillé : `python \"{outil}\" migrer` pour les ranger dans le coffre Windows et supprimer le fichier.",
            bloquant=False,
        )
    return Controle(
        "Identifiants PSA",
        False,
        "aucun identifiant enregistré : il faudra se connecter à la main dans la fenêtre Edge",
        f"Lance `python \"{outil}\" enregistrer` : une fenêtre s'ouvre, tape ton identifiant et ton mot de passe "
        "une seule fois (gardés chiffrés par Windows, jamais dans un fichier).",
        bloquant=False,
    )


def controle_config() -> Controle:
    from semaine import ErreurConfig, charger

    cree = creer_depuis_modele(CONFIG, "config.example.toml")
    try:
        cfg = charger(CONFIG)
    except ErreurConfig as e:
        return Controle(
            "config.toml",
            False,
            f"{CONFIG.as_posix()} " + ("créé depuis le modèle" if cree else f": {e}"),
            f"Ouvre {CONFIG} (ex. `notepad \"{CONFIG}\"`) : code projet, activité, heures et jours.",
        )
    codes = ", ".join(p["code"] for p in cfg["projets"])
    return Controle("config.toml", True, f"{len(cfg['projets'])} projet(s) : {codes}")


def controle_profil(profil: Path) -> Controle:
    # Chromium garde ce fichier verrouillé tant qu'un navigateur utilise le profil.
    verrou = profil / "lockfile"
    occupe = False
    if verrou.exists():
        try:
            verrou.unlink()
        except OSError:
            occupe = True
    return Controle(
        "Profil Edge du plugin",
        not occupe,
        profil.as_posix() + (" (déjà utilisé par une fenêtre Edge)" if occupe else ""),
        "" if not occupe else "Ferme la fenêtre Edge ouverte par une saisie précédente, puis relance.",
        bloquant=False,
    )


def verifier(rapide: bool = False, profil: Path | None = None) -> list[Controle]:
    controles = [controle_systeme(), controle_python(), controle_node(), controle_npx(), controle_edge()]
    if not rapide:
        controles.append(controle_mcp())
    controles += [controle_identifiants(), controle_config()]
    if profil:
        controles.append(controle_profil(profil))
    return controles


def main(argv=None) -> int:
    console_utf8()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--rapide", action="store_true")
    parser.add_argument("--profil", type=Path, help="profil Edge du plugin")
    args = parser.parse_args(argv)

    controles = verifier(args.rapide, args.profil)
    pret = all(c.ok for c in controles if c.bloquant)

    if args.json:
        print(json.dumps({"pret": pret, "donnees": DONNEES.as_posix(), "controles": [asdict(c) for c in controles]}, ensure_ascii=False, indent=2))
    else:
        for c in controles:
            etat = "OK " if c.ok else ("KO " if c.bloquant else "ATTENTION")
            print(f"[{etat}] {c.nom} : {c.detail}")
            if c.consigne:
                print(f"       -> {c.consigne}")
        print()
        print("Tout est prêt : lance /psa-time:saisir." if pret else "Corrige les points KO ci-dessus puis relance la vérification.")
    return 0 if pret else 1


if __name__ == "__main__":
    sys.exit(main())
