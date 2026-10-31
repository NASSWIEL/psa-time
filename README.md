# PSA Time pour Claude Code

Marketplace Claude Code avec un plugin qui remplit ta feuille de temps PSA (CGI) de la semaine : projets, heures, bloc « CGI Information additionnelles ». Par défaut la feuille est enregistrée **en brouillon** : tu relis et tu soumets toi-même. Avec `soumettre = true` dans ta config, elle est soumise directement pour approbation.

## Installation

Dans Claude Code :

```
/plugin marketplace add NASSWIEL/psa-time
/plugin install psa-time@psa-time
```

Puis relance Claude Code et tape :

```
/psa-time:prise-en-main
```

La prise en main vérifie ton poste, crée tes fichiers de réglages et t'explique chaque étape.

Depuis un terminal, c'est équivalent :

```
claude plugin marketplace add NASSWIEL/psa-time
claude plugin install psa-time@psa-time
```

## Ce qu'il te faut

| Outil | Pourquoi | Installation sans droits admin |
|---|---|---|
| Claude Code | l'assistant qui pilote la saisie | PowerShell : `irm https://claude.ai/install.ps1 \| iex` ([doc](https://code.claude.com/docs/fr/setup)) |
| Python 3.11+ | calculs, contrôles, connexion | Microsoft Store « Python 3.12 », ou python.org avec « Install for current user » + « Add to PATH » |
| Node.js 18+ | fait tourner Playwright | `winget install OpenJS.NodeJS.LTS --scope user`, ou le .zip de nodejs.org dans ton dossier utilisateur + PATH |
| Microsoft Edge | le navigateur piloté | déjà présent sur les postes CGI |

Playwright n'est pas à installer : il est téléchargé automatiquement au premier lancement. S'il manque quelque chose, `/psa-time:prise-en-main` (ou `/psa-time:diagnostic`) te dit exactement quoi faire.

## Utilisation

| Commande | Rôle |
|---|---|
| `/psa-time:prise-en-main` | Point de départ : vérification du poste, réglages, mode d'emploi |
| `/psa-time:saisir` | Remplit la semaine en cours (date de fin = vendredi) et l'enregistre en brouillon, ou la soumet si `soumettre = true` |
| `/psa-time:saisir -1` | Même chose pour la semaine précédente |
| `/psa-time:diagnostic` | Trouve et explique la cause d'un problème |

## Tes fichiers

Tes réglages restent sur ton poste, dans `%USERPROFILE%\.psa-time\`, et survivent aux mises à jour du plugin.

Ton identifiant et ton mot de passe PSA ne sont dans aucun fichier : tu les tapes **une seule fois** dans une petite fenêtre (`/psa-time:prise-en-main` la lance), et ils sont gardés dans le Gestionnaire d'identifiants Windows, chiffrés pour ta session. Mot de passe changé : relance `python outils/identifiants.py enregistrer`. Tu peux aussi ne rien enregistrer et te connecter toi-même dans la fenêtre Edge quand PSA le demande.


| Fichier | Contenu | Modèle |
|---|---|---|
| `config.toml` | projets, activité, heures, jours, pause, localisation | [`config.example.toml`](plugins/psa-time/config.example.toml) |

Plusieurs projets dans la semaine : un bloc `[[projets]]` par projet, chacun avec ses jours. Jour férié ou congé : retire le jour de la liste `jours`.

Soumission automatique : dans `[execution]`, `soumettre = true` soumet la feuille pour approbation au lieu de l'enregistrer en brouillon. La feuille part alors chez ton approbateur : garde `false` tant que tu n'as pas vérifié tes réglages sur quelques semaines. Si PSA signale une erreur, rien n'est soumis et le message s'affiche.

## Sécurité

- Le mot de passe n'est jamais demandé dans la conversation ni écrit dans un fichier : il vit dans le coffre d'identifiants Windows (même mécanisme que les mots de passe enregistrés par Windows).
- Il n'est lu que si PSA affiche la page de connexion : le profil Edge dédié du plugin garde la session entre deux saisies. Il passe alors au navigateur par un serveur local à usage unique (127.0.0.1, jeton aléatoire).
- Le plugin n'utilise qu'un profil Edge dédié ; ton Edge habituel n'est pas touché.
- Ancien fichier `.env` d'une version précédente : il marche encore, et `python outils/identifiants.py migrer` le range dans le coffre puis le supprime.
- Ne colle jamais ton mot de passe dans une conversation.

## Mise à jour

```
/plugin marketplace update psa-time
```

## Développement

```
plugins/psa-time/
  .claude-plugin/plugin.json   manifeste
  .mcp.json                    serveur Playwright (Edge, version figée)
  skills/                      prise-en-main, saisir, diagnostic
  outils/                      scripts Python (plan, connexion, vérification) et scripts Playwright (js/)
  tests/                       python -m pytest plugins/psa-time/tests
```

Avant de publier : `python -m pytest plugins/psa-time/tests` (contrôle aussi qu'aucune donnée personnelle n'est versionnée) et `claude plugin validate .`.
