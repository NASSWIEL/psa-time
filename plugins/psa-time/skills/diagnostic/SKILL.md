---
name: diagnostic
description: Diagnostique un problème du plugin PSA Time (Python, Node.js, Edge, téléchargement Playwright, proxy, identifiants, config.toml, fenêtre Edge déjà ouverte, serveur MCP absent) et donne la correction pas à pas. À utiliser quand /psa-time:saisir échoue ou que l'utilisateur signale que PSA Time ne marche pas.
---

# Diagnostic PSA Time

> Si `python` est introuvable mais que `py -3 --version` répond 3.11 ou plus, remplacer `python` par `py -3` dans toutes les commandes ci-dessous.

1. Lancer `python "${CLAUDE_PLUGIN_ROOT}/outils/verifier.py" --json --profil "${CLAUDE_PLUGIN_DATA}/edge"`.
   - `python` et `py` introuvables : exécuter d'abord la détection de base de `${CLAUDE_PLUGIN_ROOT}/skills/prise-en-main/SKILL.md` (étape 2a) et suivre son tableau.
2. Traiter chaque contrôle `ok: false` dans l'ordre, avec sa `consigne`, en étapes numérotées. Proposer la commande exacte ; ne rien installer sans accord.
3. Identifiants : ne jamais demander, lire ni afficher le mot de passe. Pour les (ré)enregistrer : `python "${CLAUDE_PLUGIN_ROOT}/outils/identifiants.py" enregistrer` (petite fenêtre, délai long). Ancien `.env` : `identifiants.py migrer`. Savoir s'ils existent : `identifiants.py etat` (PRESENT / ABSENT).
4. `config.toml` : tu peux le lire et le corriger, puis valider avec `python "${CLAUDE_PLUGIN_ROOT}/outils/semaine.py"`.
5. Problèmes hors script :

| Symptôme | Correction |
|---|---|
| `/mcp` n'affiche pas `plugin:psa-time:edge` ou il est en échec | Relancer Claude Code ; vérifier Node.js et le téléchargement Playwright (contrôle MCP) ; `/plugin` onglet Errors. |
| « Browser is already in use » | Fermer la fenêtre Edge ouverte par une saisie précédente. |
| Connexion refusée par PSA | Mot de passe changé récemment ? Relancer `identifiants.py enregistrer`. Ne pas réessayer en boucle : risque de verrouillage du compte. |
| La fenêtre de saisie des identifiants ne s'affiche pas | Elle est peut-être derrière les autres fenêtres : regarder la barre des tâches (« PSA Time : connexion »). |
| MFA ou écran inattendu | L'utilisateur termine dans la fenêtre Edge, puis relance `/psa-time:saisir`. |
| Code projet ou activité refusés | Vérifier le code sur une ancienne feuille PSA et le corriger dans `config.toml`. |
| Sélecteur introuvable dans un script | PSA a peut-être changé : comparer avec `${CLAUDE_PLUGIN_ROOT}/skills/saisir/selecteurs.md` et le signaler au mainteneur (issue sur le dépôt GitHub du plugin). |

6. Conclure par « relance /psa-time:saisir ».
