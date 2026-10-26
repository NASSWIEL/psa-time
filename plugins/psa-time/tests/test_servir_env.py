import threading
import urllib.error
import urllib.request

import pytest

from servir_env import creer_serveur, lire_env, servir, verifier_env


def test_lire_env(tmp_path):
    f = tmp_path / ".env"
    f.write_text('﻿# commentaire\nUtilisateur = "prenom.nom"\nmdp=a=b#c\n\n', encoding="utf-8")
    assert lire_env(f) == {"utilisateur": "prenom.nom", "mdp": "a=b#c"}


@pytest.mark.parametrize(
    "contenu, attendu",
    [
        ("utilisateur=x\nmdp=y\n", []),
        ("utilisateur=A_REMPLIR\nmdp=y\n", ["utilisateur est vide dans .env"]),
        ("utilisateur=x\n", ["mdp est vide dans .env"]),
    ],
)
def test_verifier_env(tmp_path, contenu, attendu):
    f = tmp_path / ".env"
    f.write_text(contenu, encoding="utf-8")
    assert verifier_env(f) == attendu


def test_verifier_env_absent(tmp_path):
    assert "introuvable" in verifier_env(tmp_path / ".env")[0]


def test_verifier_env_ne_divulgue_pas(tmp_path):
    f = tmp_path / ".env"
    f.write_text("utilisateur=secret_user\nmdp=\n", encoding="utf-8")
    assert "secret_user" not in " ".join(verifier_env(f))


def test_serveur_jeton_et_usage_unique():
    serveur = creer_serveur(b"utilisateur=x\nmdp=y\n", "jeton123")
    port = serveur.server_address[1]
    resultat = {}
    t = threading.Thread(target=lambda: resultat.setdefault("ok", servir(serveur, 10)))
    t.start()

    with pytest.raises(urllib.error.HTTPError) as e:
        urllib.request.urlopen(f"http://127.0.0.1:{port}/mauvais", timeout=5)
    assert e.value.code == 404

    corps = urllib.request.urlopen(f"http://127.0.0.1:{port}/jeton123", timeout=5).read()
    assert corps == b"utilisateur=x\nmdp=y\n"
    t.join(10)
    serveur.server_close()
    assert resultat["ok"] is True

    with pytest.raises(OSError):
        urllib.request.urlopen(f"http://127.0.0.1:{port}/jeton123", timeout=2)


def test_serveur_ecoute_seulement_en_local():
    serveur = creer_serveur(b"", "j")
    assert serveur.server_address[0] == "127.0.0.1"
    serveur.server_close()


def test_serveur_delai():
    serveur = creer_serveur(b"", "j")
    assert servir(serveur, 1.5) is False
    serveur.server_close()
