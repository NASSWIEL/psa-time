import json
import sys
import uuid

import pytest

import identifiants
import servir_env

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="coffre Windows")


@pytest.fixture
def coffre(monkeypatch):
    monkeypatch.setattr(identifiants, "CIBLE", f"psa-time/test-{uuid.uuid4().hex}")
    yield
    identifiants.supprimer()


def test_aller_retour(coffre):
    assert identifiants.lire() is None and not identifiants.present()
    identifiants.enregistrer("prenom.nom@cgi.com", 'é"=#\' x')
    assert identifiants.lire() == ("prenom.nom", 'é"=#\' x')
    assert identifiants.supprimer() and not identifiants.supprimer()


def test_refuse_vide(coffre):
    with pytest.raises(identifiants.ErreurCoffre):
        identifiants.enregistrer("x", "")


def test_priorite_coffre_puis_env_puis_manuel(coffre, tmp_path):
    env = tmp_path / ".env"
    contenu, source = servir_env.identifiants_a_servir(env)
    assert source == "manuel" and json.loads(contenu) == {"manuel": True}
    env.write_text("utilisateur=A_REMPLIR\nmdp=A_REMPLIR\n", encoding="utf-8")
    assert servir_env.identifiants_a_servir(env)[1] == "manuel"
    env.write_text("utilisateur=ancien\nmdp=y\n", encoding="utf-8")
    contenu, source = servir_env.identifiants_a_servir(env)
    assert source == "env" and contenu == env.read_bytes()
    identifiants.enregistrer("nouveau", "z")
    contenu, source = servir_env.identifiants_a_servir(env)
    assert source == "coffre" and json.loads(contenu) == {"utilisateur": "nouveau", "mdp": "z"}


def test_migrer_supprime_env_seulement_si_relu(coffre, tmp_path):
    env = tmp_path / ".env"
    assert "Pas de .env" in identifiants.migrer_env(env)
    env.write_text("utilisateur=x\n", encoding="utf-8")
    assert "incomplet" in identifiants.migrer_env(env) and env.exists()
    env.write_text("utilisateur=prenom.nom@cgi.com\nmdp=secret\n", encoding="utf-8")
    message = identifiants.migrer_env(env)
    assert not env.exists() and "secret" not in message
    assert identifiants.lire() == ("prenom.nom", "secret")


def test_etat_ne_divulgue_rien(coffre, capsys):
    identifiants.enregistrer("secret_user", "secret_mdp")
    assert identifiants.main(["etat"]) == 0
    sortie = capsys.readouterr().out
    assert sortie.strip() == "PRESENT"


def test_main_servir_sans_rien_ne_bloque_plus(coffre, tmp_path, capsys):
    code = servir_env.main(["--env", str(tmp_path / ".env"), "--run", str(tmp_path / "run"), "--delai", "0.1"])
    sortie = capsys.readouterr().out
    assert code == 2 and "SOURCE : manuel" in sortie and "PRET :" in sortie
    assert not (tmp_path / "run" / "connexion.js").exists()
