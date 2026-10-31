"""Transmet les identifiants PSA au navigateur Playwright sans qu'ils passent dans la conversation.

Source, dans l'ordre : coffre d'identifiants Windows (identifiants.py), sinon ancien fichier .env, sinon mode
manuel (la personne se connecte elle-même dans la fenêtre Edge, rien n'est transmis).

Le bac à sable de browser_run_code_unsafe n'a pas accès au disque : ce script sert les identifiants une seule
fois sur 127.0.0.1, à une adresse contenant un jeton aléatoire, et écrit <run>/connexion.js avec cette
adresse. La skill exécute ensuite ce fichier, qui ne lit les identifiants que si PSA affiche la page de login.

Usage (en arrière-plan) : python servir_env.py --run DIR
"""

import argparse
import http.server
import json
import secrets
import sys
import time
from pathlib import Path

from chemins import ENV, RUN_DEFAUT, console_utf8

MODELE = Path(__file__).resolve().parent / "js" / "connexion.js.modele"
CLES = ("utilisateur", "mdp")


def lire_env(chemin: Path) -> dict:
    valeurs = {}
    for ligne in chemin.read_text(encoding="utf-8-sig").splitlines():
        ligne = ligne.strip()
        if not ligne or ligne.startswith("#") or "=" not in ligne:
            continue
        cle, valeur = ligne.split("=", 1)
        valeurs[cle.strip().lower()] = valeur.strip().strip('"').strip("'")
    return valeurs


def verifier_env(chemin: Path) -> list[str]:
    """Liste des problèmes de .env, sans jamais renvoyer les valeurs."""
    if not chemin.exists():
        return [f"{chemin} introuvable : lance /psa-time:prise-en-main pour le créer."]
    valeurs = lire_env(chemin)
    problemes = []
    for cle in CLES:
        v = valeurs.get(cle, "")
        if not v or v.upper() == "A_REMPLIR":
            problemes.append(f"{cle} est vide dans .env")
    return problemes


def identifiants_a_servir(env: Path) -> tuple[bytes, str]:
    """Contenu à servir au navigateur et sa source : « coffre », « env » ou « manuel »."""
    import identifiants

    try:
        trouve = identifiants.lire()
    except identifiants.ErreurCoffre:
        trouve = None
    if trouve and trouve[0] and trouve[1]:
        return json.dumps({"utilisateur": trouve[0], "mdp": trouve[1]}).encode("utf-8"), "coffre"
    if env.exists() and not verifier_env(env):
        return env.read_bytes(), "env"
    return json.dumps({"manuel": True}).encode("utf-8"), "manuel"


def creer_serveur(contenu: bytes, jeton: str) -> http.server.HTTPServer:
    class Gestionnaire(http.server.BaseHTTPRequestHandler):
        servi = False

        def do_GET(self):
            if self.path != f"/{jeton}":
                self.send_response(404)
                self.end_headers()
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(contenu)
            type(self).servi = True

        def log_message(self, *args):
            pass

    serveur = http.server.HTTPServer(("127.0.0.1", 0), Gestionnaire)
    serveur.gestionnaire = Gestionnaire
    return serveur


def servir(serveur: http.server.HTTPServer, delai: float) -> bool:
    fin = time.monotonic() + delai
    serveur.timeout = 1
    while time.monotonic() < fin:
        serveur.handle_request()
        if serveur.gestionnaire.servi:
            return True
    return False


def main(argv=None) -> int:
    console_utf8()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--env", type=Path, default=ENV)
    parser.add_argument("--run", type=Path, default=RUN_DEFAUT, help="dossier où écrire connexion.js")
    parser.add_argument("--delai", type=float, default=90, help="secondes d'attente maximum")
    args = parser.parse_args(argv)

    contenu, source = identifiants_a_servir(args.env)
    print(f"SOURCE : {source}", flush=True)

    jeton = secrets.token_urlsafe(24)
    serveur = creer_serveur(contenu, jeton)
    url = f"http://127.0.0.1:{serveur.server_address[1]}/{jeton}"

    args.run.mkdir(parents=True, exist_ok=True)
    script = args.run / "connexion.js"
    script.write_text(MODELE.read_text(encoding="utf-8").replace("__URL_ENV__", url), encoding="utf-8")
    print(f"PRET : {script.as_posix()}", flush=True)

    try:
        ok = servir(serveur, args.delai)
    finally:
        serveur.server_close()
        script.unlink(missing_ok=True)
    print("Identifiants transmis." if ok else "Rien transmis (normal si la session PSA était encore ouverte).", flush=True)
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
