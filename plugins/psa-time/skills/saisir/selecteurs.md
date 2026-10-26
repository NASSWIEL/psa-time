# Sélecteurs PSA Time (relevés le 26/10/2026)

Utilisés par les scripts `outils/js/*.js` du plugin. À mettre à jour ici et dans les scripts si PSA change.

## Navigation
- Accès direct utilisé : `https://psa-fs.ent.cgi.com/psp/fsprda/?cmd=login&languageCd=CFR&` (le lien intranet `Timesheet: PSA Finance` mène au même endroit dans un nouvel onglet).
- Login PSA : textbox `Utilisateur @cgi.com` (sans le suffixe @cgi.com), textbox `Mot de passe`, bouton `Connexion`. Le champ mot de passe apparaît EN CLAIR dans les snapshots : tout se fait dans `connexion.js`, jamais de snapshot sur cette page.
- Accueil : vignette lien `Mes Déclarations heures`.

## Recherche feuille (iframe `iframe[title="Contenu principal"]`)
- `Code employé` prérempli, textbox `Date fin période` au format JJ/MM/AAAA (saisie directe, plus fiable que le calendrier), bouton `Aj.`
- Puis lien `Ouvrir déclaration vide` (lien `Copie feuille temps` à côté). Si la feuille existe déjà, PSA l'ouvre en modification : vérifier avant d'écraser.

## Feuille (frame `main_target_win0`, même iframe)
- Projet : `PROJECT_CODE$0` (Tab après saisie, rechargement AJAX).
- Activité : `ACTIVITY_CODE$0`, saisie directe du code (ex. `PROJET`) + Tab. Alternative manuelle : bouton `Recherche Activ.` ouvre une modale (`ptModFrame_N`) avec un lien par activité.
- Lignes suivantes : bouton « Insérer enregistrement à N » (id `EX_TIME_DTL$new$<N-1>$$0`) ajoute la ligne d'index N : `PROJECT_CODE$N`, `ACTIVITY_CODE$N`, `TIME{j}$N`.
- Indicateur de traitement AJAX supposé : `WAIT_win0` (non vérifié, les scripts attendent aussi un court délai).
- Heures : `TIME1$0` = Di ... `TIME7$0` = Sam. Format `7,4` (virgule), Tab après chaque champ.
- Lien `UC_EX_WRK_UC_TI_FRA_LINK` = « CGI Information additionnelles - France », ouvre une modale `ptModFrame_N`.

## Modale CGI Information additionnelles (jour j : 1 = Di ... 7 = Sam)
- Repos quotidien : `UC_DAILYREST{j}$0` (repos 11h), `$1` (8h-10h / 16h30-19h), `$2` (plus d'une demi-journée). Valeurs `Y`=Oui, `N`=Non, `NA`=N/A.
- Pause déjeuner : `UC_TIME_LIN_WRK_UC_DAILYREST1{j}$0`, texte `1,0`.
- Localisation : `UC_LOCATION_A{j}$0` (Matin), `$1` (Après-midi). Codes : `O`=CGI, `T`=Regulier TLT, `P`=Ponctuel TLT, `E`=Exceptionel TLT, `C`=Site client, `GD`, `NA`, `NAV`, `VCGI`, `VCLI`. L'ordre des options varie par jour : la première option non vide = la plus pertinente.
- Bouton `#ICSave` = OK, `#ICCancel` = Annuler.

## Fin
- `EX_ICLIENT_WRK_SAVE_PB` = « Enreg. brouill. » (à utiliser).
- `EX_TIME_HDR_WRK_PB_SUBMIT` = « Soumettre pour approb. » (NE JAMAIS cliquer).
- Confirmation attendue : « Les modifications ont été enregistrées » + « Déclaration heures travail non soumise ».
