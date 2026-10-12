'use strict';
/*
 * Browser E2E: navegador REAL, pesos GGUF REAIS.
 * Não consulta API paga. Confirma inferência diretamente no PWA.
 */
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const path = require('node:path');

const root = 'http://127.0.0.1:18017';
const tests = [
  { file: process.env.NANO_PATH || '/tmp/THIGAS_AI_nano_03B_Q4_K_M.gguf', label: 'nano' },
  { file: process.env.MINI_PATH || '/tmp/THIGAS_AI_mini_06B_Q4_K_M.gguf', label: 'mini' },
];

(async () => {
  const browser = await chromium.launch({
    headless: true,
    args: ['--disable-dev-shm-usage', '--no-sandbox'],
  });
  const context = await browser.newContext({
    httpCredentials: { username: 'thigas', password: 'senha-de-testes-segura' },
    viewport: { width: 1365, height: 900 },
  });
  const page = await context.newPage();
  const pageErrors = [];
  let firstBrowserError;
  const browserError = new Promise((_,reject)=>{firstBrowserError=reject});
  page.on('pageerror', e => {
    pageErrors.push(e.stack || e.message);
    firstBrowserError(new Error('Erro na execução do navegador: '+String(e.message||e)));
  });
  page.on('console', message => {
    if (message.type() === 'error') console.log('[console:error]', message.text().slice(0, 800));
  });
  page.on('requestfailed', request => console.log('[requestfailed]', request.url(), request.failure()?.errorText));
  try {
    const response = await page.goto(root + '/', { waitUntil: 'load', timeout: 120_000 });
    assert.equal(response?.status(), 200, 'A página deve exigir e aceitar autenticação');
    const originIsolated = await page.evaluate(() => crossOriginIsolated);
    assert.equal(originIsolated, true, 'O WebAssembly deve permitir SharedArrayBuffer em ambiente isolado');

    for (const { file, label } of tests) {
      console.log('\nE2E: lendo', label, file);
      await page.locator('#gguf-file').setInputFiles(path.resolve(file));
      const banner = page.locator('#local-runtime');
      await Promise.race([
        banner.waitFor({ state: 'visible', timeout: 200_000 }).then(()=>
          page.waitForFunction(expected => {
            const text=document.querySelector('#local-runtime-name')?.textContent?.toLowerCase()||'';
            return text.includes(expected);
          }, label, {timeout:200_000})
        ),
        browserError
      ]);
      const title = await page.locator('#local-runtime-name').textContent();
      console.log('Carregado:', title);
      assert.match(title.toLowerCase(), new RegExp(label), 'Deve mostrar o arquivo correto');
      await page.locator('#prompt').fill('Responda em português com uma frase curta: o que é Python?');
      await page.locator('#send').click();
      const answer = page.locator('.msg.assistant').last();
      await Promise.race([
        page.waitForFunction(() => {
          const els = [...document.querySelectorAll('.msg.assistant')];
          return els.length > 0 && (els[els.length - 1]?.textContent || '').includes('Processado localmente');
        }, null, { timeout: 200_000 }),
        browserError
      ]);
      const text = await answer.textContent();
      assert.ok(text.includes('Processado localmente'), 'Inferência no navegador, sem serviço de IA');
      console.log('RESPOSTA', label, JSON.stringify(text.slice(0, 800)));
      if (pageErrors.length) throw new Error('JavaScript gerou erros: ' + pageErrors.join('\n').slice(0, 1600));
      await page.locator('#new-chat').click();
    }
    console.log('SUCESSO: ambos os GGUFs executaram no PWA via navegador.');
  } catch (err) {
    console.error('FALHA E2E:', err.stack || String(err));
    if (pageErrors.length) console.error('ERROS JS:', pageErrors.join('\n').slice(0, 2600));
    try { console.error('UI status:', await page.locator('#status').textContent()); } catch (_) {}
    try { console.error('UI toast:', await page.locator('#toast').textContent()); } catch (_) {}
    try { await page.screenshot({ path: 'browser-failure.png', fullPage: true }); } catch (_) {}
    process.exitCode = 1;
  } finally {
    await browser.close();
  }
})().catch(err => { console.error(err); process.exitCode = 1; });
