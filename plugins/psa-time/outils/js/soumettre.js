async (page) => {
  const PLAN = /*PLAN*/null;
  // Garde-fou : sans soumettre = true dans config.toml, ce script ne touche à rien.
  if (!PLAN.soumettre) return { etat: 'non_soumis', raison: 'execution.soumettre = false dans config.toml' };

  const principal = () => page.frameLocator('iframe[title="Contenu principal"]');
  const dialogues = [];
  page.on('dialog', d => { dialogues.push(d.message()); d.accept().catch(() => {}); });

  // Une feuille déjà enregistrée affiche d'abord « Confirm. enregistrement » : OK ramène à la feuille.
  const bouton = principal().locator('[id="EX_TIME_HDR_WRK_PB_SUBMIT"]');
  if (!(await bouton.count())) {
    const ok = principal().getByRole('button', { name: /^OK$/ });
    if (await ok.count()) await ok.first().click();
  }
  const present = await bouton.waitFor({ timeout: 20000 }).then(() => true).catch(() => false);
  if (!present) return { etat: 'bloque', erreur: 'bouton « Soumettre pour approb. » introuvable', messages: dialogues };
  await bouton.click();

  // Les confirmations PSA peuvent arriver en boîte JS (acceptée ci-dessus) ou en fenêtre modale.
  const modales = [];
  const fin = Date.now() + 60000;
  let texte = '';
  while (Date.now() < fin) {
    for (const fr of page.frames().filter(f => f.name().startsWith('ptModFrame_'))) {
      const contenu = (await fr.locator('body').innerText().catch(() => '')).trim();
      const valider = fr.locator('input[type="button"], button, a[role="button"]').filter({ hasText: /^(Oui|OK|Yes)$/ });
      const parValeur = fr.locator('input[type="button"][value="Oui"], input[type="button"][value="OK"]');
      const cible = (await valider.count()) ? valider.first() : ((await parValeur.count()) ? parValeur.first() : null);
      if (cible && contenu && !modales.includes(contenu)) {
        modales.push(contenu);
        await cible.click().catch(() => {});
      }
    }
    texte = await principal().locator('body').innerText().catch(() => '');
    if (/Confirm\. soumission|a été soumise|ont été soumises|soumise pour approbation|Soumis/i.test(texte) && !/non soumise/i.test(texte)) break;
    if ((await principal().locator('.PSERRORTEXT').count().catch(() => 0)) > 0) break;
    await page.waitForTimeout(1000);
  }

  const lignes = texte.split('\n').map(t => t.trim())
    .filter(t => /soumis|soumission|approbation|erreur|avertissement|invalide|obligatoire|enregistr/i.test(t));
  const erreurs = (await principal().locator('.PSERRORTEXT').allInnerTexts().catch(() => [])).map(t => t.trim()).filter(Boolean);
  const soumis = /Confirm\. soumission|a été soumise|ont été soumises|soumise pour approbation|Soumis/i.test(texte) && !/non soumise/i.test(texte);
  return {
    etat: erreurs.length ? 'erreur' : (soumis ? 'soumis' : 'incertain'),
    messages: [...dialogues, ...modales, ...erreurs, ...lignes],
  };
}
