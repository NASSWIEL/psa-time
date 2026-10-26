"""Emplacements partagés par les scripts du plugin."""

import os
import sys
from pathlib import Path

# Code du plugin (change à chaque mise à jour : on n'y écrit jamais).
CODE = Path(__file__).resolve().parent.parent

# Fichiers personnels de l'utilisateur, conservés entre mises à jour et désinstallations.
DONNEES = Path(os.environ.get("PSA_TIME_DONNEES") or Path.home() / ".psa-time")
ENV = DONNEES / ".env"
CONFIG = DONNEES / "config.toml"

# Dossier des scripts générés : la skill passe --run avec le dossier de sortie du MCP Playwright,
# seul endroit où browser_run_code_unsafe accepte de lire un fichier.
RUN_DEFAUT = DONNEES / "run"


def console_utf8():
    # La console Windows est souvent en cp1252 : sans ça, les accents deviennent illisibles.
    for flux in (sys.stdout, sys.stderr):
        if hasattr(flux, "reconfigure"):
            flux.reconfigure(encoding="utf-8", errors="replace")
