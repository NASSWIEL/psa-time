async (page) => {
  const PLAN = /*PLAN*/null;
  const principal = () => page.frameLocator('iframe[title="Contenu principal"]');
  const modale = () => page.frames().filter(f => f.name().startsWith('ptModFrame_')).pop();
  const pause = () => page.waitForTimeout(300);

  const avant = page.frames().filter(f => f.name().startsWith('ptModFrame_')).length;
  await principal().locator('[id="UC_EX_WRK_UC_TI_FRA_LINK"]').click();
  for (let t = 0; t < 60; t++) {
    const fr = modale();
    if (page.frames().filter(f => f.name().startsWith('ptModFrame_')).length > avant && fr && await fr.locator('[id="UC_DAILYREST2$0"]').count()) break;
    await page.waitForTimeout(500);
  }
  const fr = modale();
  if (!fr || !(await fr.locator('[id="UC_DAILYREST2$0"]').count())) {
    return { etat: 'bloque', erreur: 'la fenêtre CGI Information additionnelles ne s\'est pas ouverte' };
  }

  const choix = async (id, voulu) => {
    const s = fr.locator(`[id="${id}"]`);
    const valeur = voulu === 'auto'
      ? await s.evaluate(e => ([...e.options].find(o => o.value !== '') || {}).value)
      : voulu;
    await s.selectOption(valeur);
    await pause();
    return valeur;
  };

  const c = PLAN.cgi;
  for (const j of c.jours) {
    for (let r = 0; r < 3; r++) await choix(`UC_DAILYREST${j}$${r}`, c.repos[r]);
    const champ = fr.locator(`[id="UC_TIME_LIN_WRK_UC_DAILYREST1${j}$0"]`);
    await champ.fill(c.pause);
    await champ.press('Tab');
    await pause();
    await choix(`UC_LOCATION_A${j}$0`, c.localisation_matin);
    await choix(`UC_LOCATION_A${j}$1`, c.localisation_apres_midi);
  }
  await page.waitForTimeout(800);

  const libelle = async id => fr.locator(`[id="${id}"]`).evaluate(e => (e.options[e.selectedIndex] || {}).text || '');
  const releve = {};
  const ecarts = [];
  for (const j of c.jours) {
    const repos = [];
    for (let r = 0; r < 3; r++) {
      const v = await fr.locator(`[id="UC_DAILYREST${j}$${r}"]`).inputValue();
      repos.push(v);
      if (v !== c.repos[r]) ecarts.push(`jour ${j} repos ${r + 1} = ${v || '(vide)'}`);
    }
    const p = await fr.locator(`[id="UC_TIME_LIN_WRK_UC_DAILYREST1${j}$0"]`).inputValue();
    if (parseFloat(p.replace(',', '.')) !== parseFloat(c.pause.replace(',', '.'))) ecarts.push(`jour ${j} pause = ${p || '(vide)'}`);
    const matin = await libelle(`UC_LOCATION_A${j}$0`);
    const am = await libelle(`UC_LOCATION_A${j}$1`);
    if (!matin || !am) ecarts.push(`jour ${j} localisation vide`);
    releve[j] = { repos, pause: p, matin, apres_midi: am };
  }
  if (ecarts.length) return { etat: 'ecarts', ecarts, releve };

  await fr.locator('[id="#ICSave"]').click();
  for (let t = 0; t < 40 && modale() && await modale().locator('[id="UC_DAILYREST2$0"]').count().catch(() => 0); t++) {
    await page.waitForTimeout(500);
  }
  const erreurs = (await principal().locator('.PSERRORTEXT, #alertmsg').allInnerTexts().catch(() => [])).map(t => t.trim()).filter(Boolean);
  return { etat: 'ok', releve, messages: erreurs };
}
