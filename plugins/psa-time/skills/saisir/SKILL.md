---
name: saisir
description: Remplit la déclaration d'heures hebdomadaire PSA Time (CGI) dans Edge à partir de %USERPROFILE%\.psa-time\config.toml (un ou plusieurs projets), puis l'enregistre en brouillon, ou la soumet pour approbation si soumettre = true dans la config. À utiliser quand on demande de saisir, remplir ou enregistrer sa feuille de temps / PSA time. Argument optionnel, le décalage de semaines (ex. -1 pour la semaine précédente).
argument-hint: "[décalage de semaines, ex. -1]"
---

# Saisir la feuille PSA Time

Le travail navigateur est fait par des scripts Playwright déjà écrits et testés, générés avec le plan intégré dans `${CLAUDE_PLUGIN_DATA}/run/`. Tu les exécutes avec l'outil `mcp__plugin_psa-time_edge__browser_run_code_unsafe` et son paramètre `filename`, tu lis le résultat JSON et tu décides de la suite. N'improvise pas de clics : en cas de souci, consulte `${CLAUDE_PLUGIN_ROOT}/skills/saisir/selecteurs.md`.

Notation : `RUN` = `${CLAUDE_PLUGIN_DATA}/run`, `OUTILS` = `${CLAUDE_PLUGIN_ROOT}/outils`.

> Si `python` est introuvable mais que `py -3 --version` répond 3.11 ou plus, remplacer `python` par `py -3` dans toutes les commandes ci-dessous.

## Règles absolues
- « Soumettre pour approb. » (`EX_TIME_HDR_WRK_PB_SUBMIT`) uniquement via `soumettre.js`, et seulement si le plan contient `"soumettre": true` (option `soumettre` de `config.toml`). Jamais sinon, même si l'utilisateur le suggère en passant : pour soumettre, il active l'option.
- Ne jamais lire ni afficher `%USERPROFILE%\.psa-time\.env`. Ne jamais faire de `browser_snapshot`, `browser_type` ou `browser_fill_form` sur la page de connexion PSA : le champ mot de passe apparaît en clair dans les snapshots.
- Utiliser uniquement les outils `mcp__plugin_psa-time_edge__*`.

## Étapes

1. **Plan** : `python "OUTILS/semaine.py" --preparer --run "RUN" [décalage]` (décalage = argument de la skill s'il y en a un).
   - Code de sortie 1 (`ERREUR config`, fichier introuvable) : afficher le message et proposer `/psa-time:prise-en-main`. S'arrêter.
   - Montrer en une ligne : semaine, projets, total, avertissements éventuels.

2. **Connexion** :
   - Lancer en arrière-plan `python "OUTILS/servir_env.py" --run "RUN"`. Il écrit `RUN/connexion.js` puis attend 90 s. S'il affiche `ERREUR` (`.env` absent ou vide), proposer `/psa-time:prise-en-main` et s'arrêter.
   - `browser_run_code_unsafe` avec `filename: "RUN/connexion.js"`. Réponse ENOENT (fichier pas encore écrit) : réessayer immédiatement, c'est normal au premier appel.
   - `connecte: false` : afficher `erreur` / `message`, ne pas réessayer en boucle (risque de verrouillage du compte). MFA ou écran inattendu : l'utilisateur termine dans la fenêtre Edge, puis reprendre.
   - « Browser is already in use » : une fenêtre Edge d'une saisie précédente est encore ouverte. Demander de la fermer, puis réessayer.
   - Serveur MCP absent ou en échec : proposer `/psa-time:diagnostic`.

3. **Ouvrir la feuille** : `filename: "RUN/ouvrir_feuille.js"`.
   - `ok` : continuer.
   - `bloque` : PSA n'a pas proposé « Ouvrir déclaration vide », le plus souvent parce qu'une feuille existe déjà pour cette semaine. Afficher `messages`, dire de la modifier dans PSA (onglet « Recherche valeur ») ou de la supprimer, et s'arrêter.
   - `feuille_non_vide` : la feuille contient déjà des lignes. S'arrêter et demander, ne rien écraser.
   - `deconnecte` : la session PSA a expiré, refaire l'étape 2 puis celle-ci.

4. **Projets et heures** : `filename: "RUN/saisir_projets.js"`.
   - `ecarts` ou `messages` non vides (code projet inconnu, activité invalide...) : afficher, faire une capture (`browser_take_screenshot`), s'arrêter sans enregistrer.

5. **Bloc CGI** : `filename: "RUN/remplir_cgi.js"`. Même traitement des `ecarts` et `messages`. Garder `releve` pour le récapitulatif.

6. **Enregistrer ou soumettre**, selon le plan :
   - `soumettre: false` (par défaut) : `filename: "RUN/enregistrer.js"`.
     - `enregistre` : succès, faire une capture (`browser_take_screenshot`). `incertain` : capture et la montrer, ne pas recommencer l'enregistrement.
     - `non_enregistre` : `enregistrer = false` dans la config, laisser la fenêtre ouverte pour relecture.
   - `soumettre: true` : seulement si les étapes 4 et 5 n'ont remonté aucun écart ni message. Annoncer en une ligne « soumission pour approbation en cours », puis `filename: "RUN/soumettre.js"` (la soumission enregistre aussi la feuille).
     - `soumis` : succès, faire une capture.
     - `erreur` : afficher `messages` ; la feuille n'est pas soumise. Proposer de corriger puis relancer, ou d'enregistrer en brouillon avec `enregistrer.js`.
     - `incertain` : capture, afficher `messages`, **ne jamais recliquer** (risque de double soumission) ; demander à l'utilisateur de vérifier le statut dans PSA.
     - `bloque` (bouton introuvable) : lancer `enregistrer.js` pour ne pas perdre la saisie et le signaler.

7. **Récapitulatif** à l'utilisateur, court :
   - tableau projets × jours (Lu → Ve, + week-end si saisi) avec le total ;
   - localisations matin / après-midi par jour, repos et pause ;
   - statut : « enregistrée en brouillon, non soumise » avec le rappel de relire puis soumettre dans PSA ; ou « soumise pour approbation » avec les messages PSA.
