async (page) => {
  const PLAN = /*PLAN*/null;
  if (!PLAN.enregistrer) return { etat: 'non_enregistre', raison: 'execution.enregistrer = false dans config.toml' };

  const principal = () => page.frameLocator('iframe[title="Contenu principal"]');
  const dialogues = [];
  page.on('dialog', d => { dialogues.push(d.message()); d.accept().catch(() => {}); });

  // Uniquement le brouillon : le bouton EX_TIME_HDR_WRK_PB_SUBMIT (Soumettre) n'est jamais touché.
  const bouton = principal().locator('[id="EX_ICLIENT_WRK_SAVE_PB"]');
  await bouton.waitFor({ timeout: 20000 });
  await bouton.click();

  const confirme = await principal().getByText('Confirm. enregistrement').waitFor({ timeout: 45000 }).then(() => true).catch(() => false);
  const textes = (await principal().locator('body').innerText().catch(() => '')).split('\n').map(t => t.trim())
    .filter(t => /enregistr|soumis|erreur|avertissement|invalide|obligatoire/i.test(t));
  return { etat: confirme ? 'enregistre' : 'incertain', messages: [...dialogues, ...textes] };
}
