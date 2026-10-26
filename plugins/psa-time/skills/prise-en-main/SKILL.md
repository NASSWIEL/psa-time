---
name: prise-en-main
description: Point de départ du plugin PSA Time. Explique ce que fait le plugin, vérifie le poste, crée et aide à remplir les fichiers personnels (.env et config.toml dans %USERPROFILE%\.psa-time), puis montre comment saisir sa feuille chaque semaine. À utiliser juste après l'installation du plugin, ou quand l'utilisateur demande par où commencer, comment configurer ou utiliser PSA Time.
---

# Prise en main de PSA Time

Guide l'utilisateur pas à pas, en français, avec des messages courts. Une étape à la fois : attends sa confirmation avant de passer à la suivante.

## 1. Présenter le plugin (3 lignes maximum)
- Il remplit la feuille de temps PSA de la semaine : projets, heures, bloc « CGI Information additionnelles ».
- Il l'enregistre **en brouillon** ; l'utilisateur relit et soumet lui-même. Rien n'est jamais soumis automatiquement.
- Ses réglages vivent dans `%USERPROFILE%\.psa-time\` : `.env` (identifiants) et `config.toml` (projets, heures).

## 2. Vérifier le poste
Lancer :
```
python "${CLAUDE_PLUGIN_ROOT}/outils/verifier.py" --json
```
(Le premier lancement télécharge Playwright, cela peut prendre une à deux minutes.)

- `python` introuvable : expliquer d'installer Python 3.12 depuis le Microsoft Store (sans droits admin) ou python.org (« Install for current user » + « Add python.exe to PATH »), puis de relancer Claude Code. S'arrêter là.
- Pour chaque contrôle `ok: false` hors `.env` et `config.toml` : donner sa `consigne` en étapes numérotées, proposer la commande exacte, ne rien installer sans accord.
- Le script a créé `.env` et `config.toml` depuis les modèles s'ils manquaient : c'est attendu, on les remplit aux étapes suivantes.

## 3. Identifiants (`.env`)
- Ouvrir le fichier pour l'utilisateur : `notepad "<chemin .env donné par le contrôle>"`.
- Lui dire d'y mettre `utilisateur=prenom.nom` (sans @cgi.com) et `mdp=...`, d'enregistrer et de fermer.
- **Ne jamais lire, afficher, éditer ce fichier toi-même, ni demander le mot de passe dans la conversation.** S'il le colle quand même, lui conseiller de le changer.

## 4. Réglages (`config.toml`)
Demander, en une seule question groupée :
- le ou les codes projet PSA (visibles sur une ancienne feuille), et l'activité (souvent `PROJET`) ;
- les heures par jour (ex. 7,4) et les jours travaillés sur chaque projet ;
- la durée de la pause déjeuner (1 h par défaut) ;
- la localisation : `auto` (première valeur proposée par PSA pour chaque jour, recommandé) ou une valeur fixe (`CGI`, `Regulier TLT`, `Site client`...).

Puis écrire `%USERPROFILE%\.psa-time\config.toml` en suivant le modèle `${CLAUDE_PLUGIN_ROOT}/config.example.toml` (un bloc `[[projets]]` par projet, décimales avec un point) et valider :
```
python "${CLAUDE_PLUGIN_ROOT}/outils/semaine.py"
```
Montrer le résumé (semaine, projets, total) et corriger jusqu'à ce qu'il n'y ait plus d'erreur.

## 5. Revérifier
Relancer `python "${CLAUDE_PLUGIN_ROOT}/outils/verifier.py" --rapide` jusqu'à `pret: true`.
Si Node.js vient d'être installé, ou si `/mcp` n'affiche pas `plugin:psa-time:edge`, demander de quitter et relancer Claude Code.

## 6. Confort (facultatif, proposer sans imposer)
Proposer d'ajouter dans `~/.claude/settings.json` (fusionner avec l'existant, montrer le résultat avant d'écrire) :
```json
{
  "permissions": {
    "allow": ["mcp__plugin_psa-time_edge"],
    "deny": ["Read(~/.psa-time/.env)", "Edit(~/.psa-time/.env)"]
  }
}
```
- `allow` : plus de demande de validation à chaque action du navigateur.
- `deny` : garantit que Claude ne lira jamais le fichier d'identifiants.

## 7. Conclure : mode d'emploi en 4 lignes
- Chaque semaine : `/psa-time:saisir` (semaine en cours, date de fin = vendredi), ou `/psa-time:saisir -1` pour la semaine précédente.
- Une fenêtre Edge dédiée s'ouvre, la feuille se remplit, un récapitulatif s'affiche.
- Relire la feuille dans PSA puis cliquer soi-même « Soumettre pour approb. ».
- Jour férié, congé, changement de projet : modifier `jours` dans `config.toml`. Un souci : `/psa-time:diagnostic`.
