"""Identifiants PSA dans le Gestionnaire d'identifiants Windows (chiffré par Windows, lié à la session).

Le mot de passe est tapé une seule fois dans une petite fenêtre, jamais dans la conversation ni dans un fichier.
Aucun paquet à installer : appel direct à l'API Windows (advapi32).

Usage :
    python identifiants.py enregistrer      # fenêtre de saisie (à refaire si le mot de passe CGI change)
    python identifiants.py etat             # PRESENT / ABSENT, sans jamais afficher les valeurs
    python identifiants.py migrer           # copie un ancien .env dans le coffre puis supprime le .env
    python identifiants.py supprimer        # retire les identifiants du coffre
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from chemins import ENV, console_utf8  # noqa: E402

CIBLE = os.environ.get("PSA_TIME_COFFRE") or "psa-time/PSA Finance"
CRED_TYPE_GENERIC = 1
CRED_PERSIST_LOCAL_MACHINE = 2
ERREUR_INTROUVABLE = 1168


class ErreurCoffre(RuntimeError):
    pass


def _api():
    if sys.platform != "win32":
        raise ErreurCoffre("le coffre d'identifiants n'existe que sous Windows")
    import ctypes
    from ctypes import wintypes

    class CREDENTIAL(ctypes.Structure):
        _fields_ = [
            ("Flags", wintypes.DWORD),
            ("Type", wintypes.DWORD),
            ("TargetName", wintypes.LPWSTR),
            ("Comment", wintypes.LPWSTR),
            ("LastWritten", wintypes.FILETIME),
            ("CredentialBlobSize", wintypes.DWORD),
            ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
            ("Persist", wintypes.DWORD),
            ("AttributeCount", wintypes.DWORD),
            ("Attributes", ctypes.c_void_p),
            ("TargetAlias", wintypes.LPWSTR),
            ("UserName", wintypes.LPWSTR),
        ]

    advapi = ctypes.WinDLL("advapi32", use_last_error=True)
    advapi.CredReadW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                 ctypes.POINTER(ctypes.POINTER(CREDENTIAL))]
    advapi.CredReadW.restype = wintypes.BOOL
    advapi.CredWriteW.argtypes = [ctypes.POINTER(CREDENTIAL), wintypes.DWORD]
    advapi.CredWriteW.restype = wintypes.BOOL
    advapi.CredDeleteW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD]
    advapi.CredDeleteW.restype = wintypes.BOOL
    advapi.CredFree.argtypes = [ctypes.c_void_p]
    return ctypes, CREDENTIAL, advapi


def lire() -> tuple[str, str] | None:
    """(utilisateur, mot de passe) depuis le coffre, ou None s'il n'y a rien."""
    ctypes, CREDENTIAL, advapi = _api()
    pointeur = ctypes.POINTER(CREDENTIAL)()
    if not advapi.CredReadW(CIBLE, CRED_TYPE_GENERIC, 0, ctypes.byref(pointeur)):
        code = ctypes.get_last_error()
        if code == ERREUR_INTROUVABLE:
            return None
        raise ErreurCoffre(f"lecture du coffre impossible (code Windows {code})")
    try:
        cred = pointeur.contents
        brut = ctypes.string_at(cred.CredentialBlob, cred.CredentialBlobSize)
        return (cred.UserName or "", brut.decode("utf-16-le"))
    finally:
        advapi.CredFree(pointeur)


def nettoyer_utilisateur(utilisateur: str) -> str:
    u = (utilisateur or "").strip()
    return u[: -len("@cgi.com")] if u.lower().endswith("@cgi.com") else u


def enregistrer(utilisateur: str, mdp: str):
    utilisateur = nettoyer_utilisateur(utilisateur)
    if not utilisateur or not mdp:
        raise ErreurCoffre("utilisateur et mot de passe sont obligatoires")
    ctypes, CREDENTIAL, advapi = _api()
    blob = mdp.encode("utf-16-le")
    tampon = (ctypes.c_ubyte * len(blob)).from_buffer_copy(blob)
    cred = CREDENTIAL()
    cred.Type = CRED_TYPE_GENERIC
    cred.TargetName = CIBLE
    cred.Comment = "Connexion PSA Time (plugin psa-time)"
    cred.CredentialBlobSize = len(blob)
    cred.CredentialBlob = ctypes.cast(tampon, ctypes.POINTER(ctypes.c_ubyte))
    cred.Persist = CRED_PERSIST_LOCAL_MACHINE
    cred.UserName = utilisateur
    if not advapi.CredWriteW(ctypes.byref(cred), 0):
        raise ErreurCoffre(f"écriture dans le coffre impossible (code Windows {ctypes.get_last_error()})")


def supprimer() -> bool:
    ctypes, _, advapi = _api()
    if advapi.CredDeleteW(CIBLE, CRED_TYPE_GENERIC, 0):
        return True
    code = ctypes.get_last_error()
    if code == ERREUR_INTROUVABLE:
        return False
    raise ErreurCoffre(f"suppression impossible (code Windows {code})")


def present() -> bool:
    try:
        return lire() is not None
    except ErreurCoffre:
        return False


def fenetre_saisie(utilisateur_defaut: str = "") -> tuple[str, str] | None:
    """Petite fenêtre Windows avec champ mot de passe masqué. None si la personne annule."""
    import tkinter as tk

    resultat: dict = {}
    racine = tk.Tk()
    racine.title("PSA Time : connexion")
    racine.attributes("-topmost", True)
    racine.resizable(False, False)
    tk.Label(racine, text="Identifiants PSA Finance, gardés dans le coffre Windows.\nTu ne les tapes qu'une fois.",
             justify="left").grid(row=0, column=0, columnspan=2, padx=12, pady=(12, 8), sticky="w")
    tk.Label(racine, text="Utilisateur (sans @cgi.com)").grid(row=1, column=0, padx=12, sticky="w")
    champ_u = tk.Entry(racine, width=30)
    champ_u.insert(0, utilisateur_defaut)
    champ_u.grid(row=1, column=1, padx=12, pady=4)
    tk.Label(racine, text="Mot de passe").grid(row=2, column=0, padx=12, sticky="w")
    champ_m = tk.Entry(racine, width=30, show="•")
    champ_m.grid(row=2, column=1, padx=12, pady=4)

    def valider(_=None):
        if champ_u.get().strip() and champ_m.get():
            resultat["u"], resultat["m"] = champ_u.get(), champ_m.get()
            racine.destroy()

    boutons = tk.Frame(racine)
    boutons.grid(row=3, column=0, columnspan=2, pady=12)
    tk.Button(boutons, text="Enregistrer", width=12, command=valider).pack(side="left", padx=6)
    tk.Button(boutons, text="Annuler", width=12, command=racine.destroy).pack(side="left", padx=6)
    racine.bind("<Return>", valider)
    racine.bind("<Escape>", lambda _: racine.destroy())
    (champ_m if utilisateur_defaut else champ_u).focus_force()
    racine.mainloop()
    return (resultat["u"], resultat["m"]) if resultat else None


def migrer_env(env: Path = ENV) -> str:
    """Copie utilisateur/mdp d'un ancien .env dans le coffre puis supprime le .env."""
    from servir_env import lire_env, verifier_env

    if not env.exists():
        return "Pas de .env à migrer."
    if verifier_env(env):
        return f"{env.name} incomplet : rien migré. Utilise plutôt « enregistrer »."
    valeurs = lire_env(env)
    enregistrer(valeurs["utilisateur"], valeurs["mdp"])
    if lire() != (nettoyer_utilisateur(valeurs["utilisateur"]), valeurs["mdp"]):
        raise ErreurCoffre(f"le coffre ne relit pas les mêmes identifiants : {env.name} conservé")
    env.unlink()
    return f"Identifiants copiés dans le coffre Windows, {env.name} supprimé."


def main(argv=None) -> int:
    console_utf8()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("action", choices=["enregistrer", "etat", "migrer", "supprimer"])
    args = parser.parse_args(argv)
    try:
        if args.action == "etat":
            print("PRESENT" if present() else "ABSENT")
            return 0
        if args.action == "supprimer":
            print("Identifiants retirés du coffre." if supprimer() else "Rien dans le coffre.")
            return 0
        if args.action == "migrer":
            print(migrer_env())
            return 0
        actuel = lire()
        saisie = fenetre_saisie(actuel[0] if actuel else "")
        if not saisie:
            print("ANNULE : rien changé.")
            return 2
        enregistrer(*saisie)
        print("OK : identifiants enregistrés dans le coffre Windows.")
        return 0
    except ErreurCoffre as e:
        print(f"ERREUR : {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
