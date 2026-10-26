import getpass
import sys
import json
import re
from pathlib import Path

import pytest

import verifier

PLUGIN = Path(__file__).resolve().parent.parent
DEPOT = PLUGIN.parent.parent


@pytest.fixture
def donnees(tmp_path, monkeypatch):
    monkeypatch.setattr(verifier, "ENV", tmp_path / ".env")
    monkeypatch.setattr(verifier, "CONFIG", tmp_path / "config.toml")
    import semaine

    monkeypatch.setattr(semaine, "CONFIG", tmp_path / "config.toml")
    return tmp_path


def test_version():
    assert verifier._version("v24.14.1") == (24, 14, 1)
    assert verifier._version("2.0.31 (Claude Code)") == (2, 0, 31)
    assert verifier._version("") == (0,)


def test_env_cree_depuis_modele_puis_signale_vide(donnees):
    c = verifier.controle_env()
    assert not c.ok and "créé" in c.detail
    assert (donnees / ".env").exists()
    c = verifier.controle_env()
    assert not c.ok and "vide" in c.detail
    (donnees / ".env").write_text("utilisateur=x\nmdp=y\n", encoding="utf-8")
    assert verifier.controle_env().ok


def test_config_creee_depuis_modele_puis_validee(donnees):
    c = verifier.controle_config()
    assert not c.ok and "créé" in c.detail
    modele = (donnees / "config.toml").read_text(encoding="utf-8")
    (donnees / "config.toml").write_text(modele.replace('"A_REMPLIR"', '"300000000099999"'), encoding="utf-8")
    c = verifier.controle_config()
    assert c.ok and "1 projet" in c.detail


def test_main_json(capsys, monkeypatch):
    controles = [verifier.Controle("x", True, "ok"), verifier.Controle("y", False, "ko", bloquant=False)]
    monkeypatch.setattr(verifier, "verifier", lambda rapide, profil: controles)
    assert verifier.main(["--json"]) == 0
    sortie = json.loads(capsys.readouterr().out)
    assert sortie["pret"] is True and len(sortie["controles"]) == 2


def test_main_bloquant(capsys, monkeypatch):
    monkeypatch.setattr(verifier, "verifier", lambda rapide, profil: [verifier.Controle("x", False, "ko", "fais ceci")])
    assert verifier.main([]) == 1
    assert "fais ceci" in capsys.readouterr().out


def test_profil_libre(tmp_path):
    assert verifier.controle_profil(tmp_path).ok


def test_manifestes():
    marche = json.loads((DEPOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    plugin = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    entree = marche["plugins"][0]
    assert entree["name"] == plugin["name"] == "psa-time"
    assert (DEPOT / entree["source"]).resolve() == PLUGIN.resolve()


def test_mcp_plugin():
    serveur = json.loads((PLUGIN / ".mcp.json").read_text(encoding="utf-8"))["mcpServers"]["edge"]
    args = " ".join(serveur["args"])
    assert f"@playwright/mcp@{verifier.VERSION_MCP}" in args
    assert "--browser msedge" in args
    # Les skills lisent leurs scripts dans ce dossier : il doit être le dossier de sortie du MCP.
    assert "--output-dir ${CLAUDE_PLUGIN_DATA}/run" in args
    saisir = (PLUGIN / "skills" / "saisir" / "SKILL.md").read_text(encoding="utf-8")
    assert "${CLAUDE_PLUGIN_DATA}/run" in saisir
    assert "mcp__plugin_psa-time_edge__browser_run_code_unsafe" in saisir


def test_skills_ont_un_frontmatter_valide():
    yaml = pytest.importorskip("yaml")
    skills = list((PLUGIN / "skills").glob("*/SKILL.md"))
    assert len(skills) == 3
    for skill in skills:
        texte = skill.read_text(encoding="utf-8")
        assert texte.startswith("---\n"), skill
        # Un « : » non protégé dans une valeur casse le YAML et la skill perd sa description en silence.
        meta = yaml.safe_load(texte.split("---")[1])
        assert meta["name"] == skill.parent.name
        assert len(meta["description"]) > 50


def _fichiers_publies():
    ignores = {".git", "__pycache__", ".pytest_cache"}
    return [p for p in DEPOT.rglob("*") if p.is_file() and not ignores & set(p.parts)]


def test_aucun_fichier_personnel():
    noms = {p.name for p in _fichiers_publies()}
    assert not noms & {".env", "config.toml", "settings.local.json"}
    assert not any(n.endswith(".png") for n in noms)


def test_aucune_donnee_personnelle():
    session = getpass.getuser().lower()
    mots = {session, *[m for m in re.split(r"[._\-\s]", session) if len(m) >= 4]}
    # Code projet et matricule de l'auteur, reconstruits pour ne pas apparaître en clair ici.
    mots |= {"3000000000" + "97461", "563" + "604"}
    trouves = []
    for p in _fichiers_publies():
        # Le compte GitHub public du dépôt est voulu (URL du marketplace).
        texte = p.read_text(encoding="utf-8", errors="replace").lower().replace("nasswiel", "")
        trouves += [f"{p.relative_to(DEPOT)} : {m}" for m in mots if m and m in texte]
    assert not trouves, trouves


def _bloc_detection():
    texte = (PLUGIN / "skills" / "prise-en-main" / "SKILL.md").read_text(encoding="utf-8")
    m = re.search(r"<!-- detection:debut -->\s*```powershell\n(.*?)```", texte, re.S)
    assert m, "bloc de détection introuvable dans prise-en-main"
    return m.group(1)


def _detecter(prefixe=""):
    import subprocess

    r = subprocess.run(
        ["powershell", "-NoProfile", "-Command", prefixe + _bloc_detection()],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120,
    )
    return json.loads(r.stdout)


CLES_DETECTION = {"python", "python_chemin", "python_alias_store", "py_lanceur", "node", "npx", "winget", "edge",
                  "registre_npm", "proxy_npm", "dossier_reglages", "env_present", "config_presente"}


@pytest.mark.skipif(sys.platform != "win32", reason="détection PowerShell propre à Windows")
def test_detection_sur_ce_poste():
    d = _detecter()
    assert set(d) == CLES_DETECTION
    assert d["python"] and d["python"].startswith("Python 3")


@pytest.mark.skipif(sys.platform != "win32", reason="détection PowerShell propre à Windows")
def test_detection_poste_sans_python_ni_node():
    d = _detecter('$env:PATH = "$env:SystemRoot\System32;$env:SystemRoot\System32\WindowsPowerShell\v1.0"; ')
    assert set(d) == CLES_DETECTION
    assert d["python"] is None and d["py_lanceur"] is None
    assert d["node"] is None and d["npx"] is False
