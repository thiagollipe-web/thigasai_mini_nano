'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
require('../local_gguf.js');
const engine=globalThis.THIGASBrowserGGUF;
const short=[
 {role:'system',content:'Você é THIGAS AI.'},
 {role:'user',content:'O que é uma função Python?'},
];

test('o GGUF tem mais tokens de saída sem aumentar janela de contexto',()=>{
 assert.equal(engine.planGeneration(short,'rapido',2048),460);
 assert.equal(engine.planGeneration(short,'equilibrado',4096),800);
 assert.equal(engine.planGeneration(short,'alto',4096),1250);
});

test('a reserva de contexto limita respostas quando os textos são longos',()=>{
 const longer=[
  {role:'system',content:'Você é o THIGAS AI.'},
  {role:'user',content:'A'.repeat(2400)}
 ];
 const answer=engine.planGeneration(longer,'alto',2048);
 assert.ok(answer>=96 && answer<1250);
 const maxChars=[{role:'user',content:'Z'.repeat(12000)}];
 assert.throws(()=>engine.planGeneration(maxChars,'alto',2048),/janela de contexto/);
});

test('valida entradas inválidas sem carregar modelo',()=>{
 assert.throws(()=>engine.planGeneration(null),/Mensagens inválidas/);
 assert.throws(()=>engine.planGeneration([{role:'user',content:{foo:'bar'}}]),/Mensagens inválidas/);
 assert.equal(engine.hasModel(),false);
 assert.equal(engine.getInfo(),null);
});

test('a interface mostra de forma transparente o modo Conhecimento opt-out',()=>{
 const {execFileSync}=require('node:child_process');
 const html=execFileSync('git',['show','HEAD:index.html'],{encoding:'utf8'});
 assert.ok(html.includes('id="knowledge-toggle"'));
 assert.ok(html.includes('state.wiki=getWikiPreference()'));
 assert.ok(html.includes("localStorage.setItem('thigas_knowledge_wiki'"));
 assert.ok(html.includes("wikiSources.slice(0,3)"));
 assert.ok(html.includes("window.THIGASBrowserGGUF.chat(messages,{effort})"));
});
