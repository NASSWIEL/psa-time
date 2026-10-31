---
name: prise-en-main
description: Point de départ du plugin PSA Time. Explique ce que fait le plugin, vérifie le poste, range les identifiants PSA une seule fois dans le coffre d'identifiants Windows, crée et aide à remplir config.toml dans %USERPROFILE%\.psa-time, puis montre comment saisir sa feuille chaque semaine. À utiliser juste après l'installation du plugin, ou quand l'utilisateur demande par où commencer, comment configurer ou utiliser PSA Time.
---

# Prise en main de PSA Time

Guide l'utilisateur pas à pas, en français, avec des messages courts. Une étape à la fois : attends sa confirmation avant de passer à la suivante.

## 1. Présenter le plugin (3 lignes maximum)
- Il remplit la feuille de temps PSA de la semaine : projets, heures, bloc « CGI Information additionnelles ».
- Par défaut il l'enregistre **en brouillon** : l'utilisateur relit et soumet lui-même. Avec l'option `soumettre = true`, il la soumet directement pour approbation.
- Ses réglages vivent dans `%USERPROFILE%\.psa-time\config.toml` (projets, heures). Les identifiants PSA sont tapés une seule fois dans une petite fenêtre et gardés dans le coffre d'identifiants Windows, jamais dans un fichier ni dans la conversation.

## 2. Détecter ce qui manque sur le poste

### 2a. Détection de base (ne dépend de rien d'installé)
Exécuter ce bloc avec l'outil PowerShell tel quel (s'il n'y a que l'outil Bash, le lancer via `powershell -NoProfile -Command "..."`). Ce n'est pas un fichier `.ps1`, la stratégie d'exécution ne le bloque donc pas.

<!-- detection:debut -->
```powershell
$ErrorActionPreference = 'SilentlyContinue'
function Sortie([string]$exe, [string[]]$arguments) {
  if (-not (Get-Command $exe)) { return $null }
  try { $s = & $exe @arguments 2>&1 | Select-Object -First 1; if ($s) { return "$s".Trim() } } catch {}
  return $null
}
$reglages = Join-Path $env:USERPROFILE '.psa-time'
$py = Get-Command python | Select-Object -First 1
$edge = @("${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe",
          "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe",
          "$env:LOCALAPPDATA\Microsoft\Edge\Application\msedge.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
try { $registre = (Invoke-WebRequest 'https://registry.npmjs.org/@playwright%2Fmcp' -UseBasicParsing -Method Head -TimeoutSec 15).StatusCode }
catch { $registre = "$($_.Exception.Message)" }
[ordered]@{
  python             = Sortie 'python' @('--version')
  python_chemin      = $py.Source
  python_alias_store = [bool]($py -and $py.Source -like '*\WindowsApps\*')
  py_lanceur         = Sortie 'py' @('-3', '--version')
  node               = Sortie 'node' @('--version')
  npx                = [bool](Get-Command npx)
  winget             = [bool](Get-Command winget)
  edge               = $edge
  registre_npm       = $registre
  proxy_npm          = Sortie 'npm' @('config', 'get', 'https-proxy')
  dossier_reglages   = $reglages
  env_present        = Test-Path (Join-Path $reglages '.env')
  config_presente    = Test-Path (Join-Path $reglages 'config.toml')
} | ConvertTo-Json
```
<!-- detection:fin -->

Interpréter chaque ligne avec ce tableau :

| Élément | OK si | Sinon : quoi dire à l'utilisateur |
|---|---|---|
| Python | `python` vaut `Python 3.11` ou plus | Si `py_lanceur` vaut 3.11+ : OK, mais utiliser `py -3` à la place de `python` dans toutes les commandes du plugin. Si `python_alias_store` est vrai sans version : c'est l'alias Microsoft Store, pas un vrai Python. Sinon absent ou trop ancien. Correction : installer « Python 3.12 » depuis le Microsoft Store (sans droits admin), ou python.org avec « Install for current user » + « Add python.exe to PATH ». |
| Node.js | `node` vaut `v18` ou plus | Si `winget` est vrai : `winget install OpenJS.NodeJS.LTS --scope user`. Sinon : .zip Windows sur nodejs.org, dézippé dans le dossier utilisateur, ajouté au PATH utilisateur. |
| npx | vrai | Livré avec Node.js : réinstaller Node.js LTS. |
| Edge | un chemin | Installer Microsoft Edge depuis le Centre logiciel CGI. |
| Accès npm | `registre_npm` vaut `200` | Réseau ou proxy d'entreprise : réessayer hors VPN, ou demander l'adresse du proxy au support. |
| Proxy npm | `null`, vide, ou une adresse | Si l'accès npm est OK mais que le téléchargement de Playwright échoue plus tard : `npm config set proxy http://<proxy>:<port>` et `npm config set https-proxy http://<proxy>:<port>`. |
| Réglages | `config_presente` | Normal à la première installation : il sera créé à l'étape 2c. `env_present` vrai = ancien fichier d'identifiants, à migrer à l'étape 3. |

### 2b. Serveur navigateur du plugin
Vérifier que les outils `mcp__plugin_psa-time_edge__*` sont disponibles (avec ToolSearch, requête `psa-time edge browser`). S'ils sont absents, le serveur n'a pas démarré : c'est presque toujours Node.js/npx manquant, ou installé après le lancement de Claude Code. L'utilisateur peut aussi le voir dans `/mcp` (`plugin:psa-time:edge`).

### 2c. Contrôle complet (seulement si Python est OK)
```
python "${CLAUDE_PLUGIN_ROOT}/outils/verifier.py" --json
```
(`py -3` à la place de `python` si c'est ce qui marche.) Il télécharge Playwright une première fois (une à deux minutes), confirme que tout s'exécute, et crée `config.toml` depuis le modèle s'il manque.

### 2d. Restituer et corriger
- Afficher un tableau récapitulatif court : élément, état (OK / à corriger), action.
- Corriger un point à la fois, dans l'ordre : Python, Node.js, Edge, réseau. Donner la commande exacte, ne rien installer sans accord.
- **Après une installation de Python ou de Node.js, Claude Code doit être redémarré** : les logiciels installés pendant la session ne sont pas vus (PATH), et le serveur navigateur ne démarre qu'au lancement. Dire à l'utilisateur de quitter, relancer Claude Code puis `/psa-time:prise-en-main` : la prise en main reprend à la détection, rien n'est perdu.
- Passer à l'étape 3 seulement quand Python, Node.js, npx et Edge sont OK et que le contrôle complet n'a plus de KO hors identifiants et `config.toml`.

## 3. Identifiants (une seule fois, coffre Windows)
- Contrôle « Identifiants PSA » OK avec « coffre » : rien à faire.
- Ancien fichier `.env` signalé : proposer `python "${CLAUDE_PLUGIN_ROOT}/outils/identifiants.py" migrer`. Il copie les identifiants dans le coffre, vérifie qu'il les relit, puis supprime le `.env`.
- Sinon : prévenir qu'une petite fenêtre « PSA Time : connexion » va s'ouvrir (parfois derrière les autres fenêtres), puis lancer `python "${CLAUDE_PLUGIN_ROOT}/outils/identifiants.py" enregistrer` avec un délai long (10 minutes). L'utilisateur y tape son identifiant (sans @cgi.com) et son mot de passe, puis clique « Enregistrer ». Sortie `OK` : c'est fait. `ANNULE` : il pourra le faire plus tard, la saisie marchera quand même en se connectant à la main dans Edge.
- **Ne jamais demander, lire, afficher ni écrire le mot de passe toi-même, ni dans la conversation, ni dans un fichier.** S'il le colle quand même, lui conseiller de le changer puis de relancer `identifiants.py enregistrer`.
- Mot de passe CGI changé plus tard : relancer `identifiants.py enregistrer`, la fenêtre propose l'identifiant déjà connu.

## 4. Réglages (`config.toml`)
Demander, en une seule question groupée :
- le ou les codes projet PSA (visibles sur une ancienne feuille), et l'activité (souvent `PROJET`) ;
- les heures par jour (ex. 7,4) et les jours travaillés sur chaque projet ;
- la durée de la pause déjeuner (1 h par défaut) ;
- la localisation : `auto` (première valeur proposée par PSA pour chaque jour, recommandé) ou une valeur fixe (`CGI`, `Regulier TLT`, `Site client`...) ;
- brouillon (recommandé pour les premières semaines) ou soumission directe pour approbation (`soumettre = true`). Prévenir qu'une feuille soumise part chez l'approbateur.

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
- `deny` : garantit que Claude ne lira jamais un ancien fichier d'identifiants s'il en reste un.

## 7. Conclure : mode d'emploi en 4 lignes
- Chaque semaine : `/psa-time:saisir` (semaine en cours, date de fin = vendredi), ou `/psa-time:saisir -1` pour la semaine précédente.
- Une fenêtre Edge dédiée s'ouvre, la feuille se remplit, un récapitulatif s'affiche.
- En brouillon : relire la feuille dans PSA puis cliquer soi-même « Soumettre pour approb. ». Pour la soumission automatique : `soumettre = true` dans `config.toml`.
- Jour férié, congé, changement de projet : modifier `jours` dans `config.toml`. Un souci : `/psa-time:diagnostic`.
