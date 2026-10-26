async (page) => {
  const PLAN = /*PLAN*/null;
  const principal = () => page.frameLocator('iframe[title="Contenu principal"]');
  const cadre = async () => (await page.locator('iframe[title="Contenu principal"]').elementHandle()).contentFrame();
  const attendreAjax = async () => {
    await page.waitForTimeout(300);
    const fr = await cadre();
    // WAIT_win0 est l'indicateur de traitement des pages PeopleSoft classiques.
    await fr.waitForFunction(() => {
      const w = document.getElementById('WAIT_win0') || document.getElementById('processing');
      if (!w) return true;
      const s = getComputedStyle(w);
      return s.visibility === 'hidden' || s.display === 'none';
    }, null, { timeout: 20000 }).catch(() => {});
  };
  const erreurs = async () => (await principal().locator('.PSERRORTEXT, #alertmsg').allInnerTexts().catch(() => [])).map(t => t.trim()).filter(Boolean);
  const saisir = async (id, valeur) => {
    const champ = principal().locator(`[id="${id}"]`);
    await champ.waitFor({ timeout: 20000 });
    await champ.click();
    await champ.fill(valeur);
    await champ.press('Tab');
    await attendreAjax();
  };

  const dialogues = [];
  page.on('dialog', d => { dialogues.push(d.message()); d.accept().catch(() => {}); });

  const resultat = [];
  for (const ligne of PLAN.lignes) {
    const i = ligne.index;
    if (i > 0 && !(await principal().locator(`[id="PROJECT_CODE$${i}"]`).count())) {
      const parNom = principal().getByRole('button', { name: `Insérer enregistrement à ${i}` });
      const bouton = (await parNom.count()) ? parNom.first() : principal().locator(`[id="EX_TIME_DTL$new$${i - 1}$$0"]`);
      await bouton.click();
      await attendreAjax();
    }
    await saisir(`PROJECT_CODE$${i}`, ligne.code);
    await saisir(`ACTIVITY_CODE$${i}`, ligne.activite);
    for (const [colonne, valeur] of Object.entries(ligne.heures)) {
      await saisir(`TIME${colonne}$${i}`, valeur);
    }
    const relu = { projet: await principal().locator(`[id="PROJECT_CODE$${i}"]`).inputValue(), activite: await principal().locator(`[id="ACTIVITY_CODE$${i}"]`).inputValue(), heures: {} };
    for (let c = 1; c <= 7; c++) relu.heures[c] = await principal().locator(`[id="TIME${c}$${i}"]`).inputValue();
    resultat.push(relu);
  }

  const ecarts = [];
  PLAN.lignes.forEach((ligne, n) => {
    const r = resultat[n];
    if (r.projet !== ligne.code) ecarts.push(`ligne ${n + 1} : projet ${r.projet || '(vide)'} au lieu de ${ligne.code}`);
    if (r.activite.toUpperCase() !== ligne.activite) ecarts.push(`ligne ${n + 1} : activité ${r.activite || '(vide)'} au lieu de ${ligne.activite}`);
    for (let c = 1; c <= 7; c++) {
      const attendu = parseFloat((ligne.heures[c] || '0').replace(',', '.'));
      const lu = parseFloat((r.heures[c] || '0').replace(',', '.')) || 0;
      if (Math.abs(attendu - lu) > 0.001) ecarts.push(`ligne ${n + 1} : colonne ${c} = ${r.heures[c] || '(vide)'} au lieu de ${ligne.heures[c] || '(vide)'}`);
    }
  });
  return { etat: ecarts.length ? 'ecarts' : 'ok', lignes: resultat, ecarts, messages: [...dialogues, ...await erreurs()] };
}
