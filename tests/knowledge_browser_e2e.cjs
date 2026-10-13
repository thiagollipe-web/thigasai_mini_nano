'use strict';
// E2E isolado: não utiliza API paga nem modifica o histórico real do usuário.
const assert = require('node:assert/strict');
const {chromium} = require('playwright');

(async()=>{
 const browser=await chromium.launch({headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
 const context=await browser.newContext({
  httpCredentials:{username:'thigas',password:'senha-de-testes-segura'},
  viewport:{width:390,height:840}
 });
 const page=await context.newPage();
 const errors=[];const requests=[];
 page.on('pageerror',error=>errors.push(String(error)));
 await page.route('**/api/chat',async route=>{
  const body=JSON.parse(route.request().postData()||'{}');
  requests.push(body);
  await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({
    resposta:'## Resposta completa\n\nA informação possui **explicações relevantes** e um exemplo adequado.',
    fontes:body.wikipedia?[{titulo:'Albert Einstein',texto:'Físico teórico.',url:'https://pt.wikipedia.org/?curid=12'}]:[],
    aviso:''
  })});
 });
 try{
  const response=await page.goto('http://127.0.0.1:18023/',{waitUntil:'load'});
  assert.equal(response.status(),200);
  const btn=page.locator('#knowledge-toggle');
  await btn.waitFor({state:'visible'});
  assert.equal(await btn.getAttribute('aria-pressed'),'true','A pesquisa deve iniciar ativa e visível');
  assert.match(await btn.textContent(),/Wikipédia ligada/);

  await btn.click();
  assert.equal(await btn.getAttribute('aria-pressed'),'false');
  let value=await page.evaluate(()=>localStorage.getItem('thigas_knowledge_wiki'));
  assert.equal(value,'false');
  await page.reload({waitUntil:'load'});
  assert.equal(await page.locator('#knowledge-toggle').getAttribute('aria-pressed'),'false');

  await page.locator('#prompt').fill('O que é lógica de programação?');
  await page.locator('#send').click();
  await page.locator('.msg.assistant strong').last().waitFor();
  assert.equal(requests.at(-1).wikipedia,false,'Opt-out precisa impedir pesquisa Wikipédia');

  await page.locator('#new-chat').click();
  assert.equal(await page.locator('#knowledge-toggle').getAttribute('aria-pressed'),'false');
  await page.locator('#knowledge-toggle').click();
  assert.equal(await page.locator('#knowledge-toggle').getAttribute('aria-pressed'),'true');

  await page.locator('#prompt').fill('Quem foi Albert Einstein?');
  await page.locator('#send').click();
  await page.locator('.msg.assistant .sources a').last().waitFor();
  assert.equal(requests.at(-1).wikipedia,true,'Pesquisa precisa estar marcada na requisição');
  assert.equal(requests.at(-1).esforco,'equilibrado');
  assert.equal(await page.locator('.msg.assistant strong').last().textContent(),'explicações relevantes');
  assert.ok((await page.locator('.msg.assistant').last().textContent()).includes('Resposta completa'));
  assert.equal(errors.length,0,errors.join('\n'));
  console.log('PASSOU: modo conhecimento com opt-out persistente, fonte e resposta formatada; sem API paga');
 }catch(err){
  console.error(err.stack||String(err));
  console.error('REQUISIÇÕES',JSON.stringify(requests).slice(0,1700));
  try{await page.screenshot({path:'knowledge-browser-failure.png',fullPage:true})}catch(_){}
  process.exitCode=1;
 }finally{await browser.close()}
})().catch(error=>{console.error(error);process.exitCode=1});
