async (page) => {
  const PLAN = /*PLAN*/null;
  const dialogues = [];
  page.on('dialog', d => { dialogues.push(d.message()); d.accept().catch(() => {}); });

  const principal = () => page.frameLocator('iframe[title="Contenu principal"]');
  const messagesPsa = async () => {
    const textes = [];
    for (const f of page.frames()) {
      textes.push(...await f.locator('.PSERRORTEXT, #alertmsg, .ps_alert-message, [id^="ptpopupmsgbtn"]').allInnerTexts().catch(() => []));
    }
    return [...dialogues, ...textes].map(t => t.trim()).filter(Boolean);
  };

  // Repartir de l'accueil PSA : élimine un message ou une feuille restés ouverts d'un essai précédent.
  await page.goto('https://psa-fs.ent.cgi.com/psc/fsprda/EMPLOYEE/ERP/c/NUI_FRAMEWORK.PT_LANDINGPAGE.GBL', { waitUntil: 'domcontentloaded' });
  if (/cmd=login/.test(page.url())) return { etat: 'deconnecte', messages: ['Session PSA expirée : relancer la connexion.'] };
  const vignette = page.getByRole('link', { name: 'Mes Déclarations heures' });
  await vignette.waitFor({ timeout: 30000 });
  await vignette.click();

  const date = principal().getByRole('textbox', { name: 'Date fin période' });
  await date.waitFor({ timeout: 30000 });
  await date.fill(PLAN.date_fin);
  await principal().getByRole('button', { name: 'Aj.' }).click();

  const vide = principal().getByRole('link', { name: 'Ouvrir déclaration vide' });
  const ouvert = await vide.waitFor({ timeout: 20000 }).then(() => true).catch(() => false);
  if (!ouvert) {
    return { etat: 'bloque', date_fin: PLAN.date_fin, messages: await messagesPsa() };
  }
  await vide.click();

  const projet = principal().locator('[id="PROJECT_CODE$0"]');
  await projet.waitFor({ timeout: 30000 });
  const existants = await principal().locator('[id^="PROJECT_CODE$"]').evaluateAll(els => els.map(e => e.value).filter(Boolean));
  const heures = await principal().locator('input[id^="TIME"][id*="$"]').evaluateAll(els => els.map(e => e.value).filter(Boolean));
  if (existants.length || heures.length) {
    return { etat: 'feuille_non_vide', projets: existants, messages: await messagesPsa() };
  }
  return { etat: 'ok', date_fin: PLAN.date_fin, messages: await messagesPsa() };
}
