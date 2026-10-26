# PSA Time pour Claude Code

Marketplace Claude Code avec un plugin qui remplit ta feuille de temps PSA (CGI) de la semaine : projets, heures, bloc « CGI Information additionnelles ». La feuille est enregistrée **en brouillon** : tu relis et tu soumets toi-même, rien n'est jamais soumis automatiquement.

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
| `/psa-time:saisir` | Remplit la semaine en cours (date de fin = vendredi) et l'enregistre en brouillon |
| `/psa-time:saisir -1` | Même chose pour la semaine précédente |
| `/psa-time:diagnostic` | Trouve et explique la cause d'un problème |

## Tes fichiers

Tes réglages restent sur ton poste, dans `%USERPROFILE%\.psa-time\`, et survivent aux mises à jour du plugin :

| Fichier | Contenu | Modèle |
|---|---|---|
| `.env` | identifiant CGI (sans @cgi.com) et mot de passe PSA | [`.env.example`](plugins/psa-time/.env.example) |
| `config.toml` | projets, activité, heures, jours, pause, localisation | [`config.example.toml`](plugins/psa-time/config.example.toml) |

Plusieurs projets dans la semaine : un bloc `[[projets]]` par projet, chacun avec ses jours. Jour férié ou congé : retire le jour de la liste `jours`.

## Sécurité

- Le mot de passe n'est lu que par Playwright, via un serveur local à usage unique (127.0.0.1, jeton aléatoire). Il ne passe jamais dans la conversation.
- Le plugin n'utilise qu'un profil Edge dédié ; ton Edge habituel n'est pas touché.
- `/psa-time:prise-en-main` propose une règle qui interdit à Claude de lire `.env`.
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
