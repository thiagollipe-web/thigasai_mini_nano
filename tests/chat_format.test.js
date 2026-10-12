'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const format=require('../chat_format.js');

function fakeDocument(){
 function make(tagName, contents){
  let children=[];
  const attributes={};
  const node={
   tagName,
   attributes,
   get childNodes(){return children},
   get textContent(){return contents===null?children.map(x=>x.textContent).join(''):contents},
   set textContent(value){contents=String(value);children=[]},
   setAttribute(name,value){attributes[name]=String(value)},
   appendChild(item){if(contents!==null){contents=null}children.push(item);return item},
   replaceChildren(...items){contents=null;children=items},
  };
  return node;
 }
 const doc={
  createElement(name){return make(name,null)},
  createTextNode(text){return make('#text',String(text))},
  createDocumentFragment(){return make('#fragment',null)},
 };
 const container=make('div',null);container.ownerDocument=doc;
 return {doc,container};
}
function elements(node,tag){
 const found=[];
 (function walk(x){
  if(x.tagName===tag)found.push(x);
  for(const child of x.childNodes||[])walk(child);
 })(node);
 return found;
}
function plain(node){return node.textContent}
function escaped(node){
 if(node.tagName==='#text')return node.textContent.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;');
 if(node.tagName==='#fragment')return node.childNodes.map(escaped).join('');
 return '<'+node.tagName+'>'+node.childNodes.map(escaped).join('')+'</'+node.tagName+'>';
}

test('##, ** e *** tornam-se títulos, destaques e separadores, não texto cru',()=>{
 const text='## Título principal\n\nTexto **importante**, ***ênfase maior*** e __destaque__.\n\n***\n\n### Orientações\n- **Primeiro item**\n- Segundo item';
 const {container}=fakeDocument();
 format.render(container,text);
 assert.equal(elements(container,'h3')[0].textContent,'Título principal');
 assert.equal(elements(container,'h4')[0].textContent,'Orientações');
 assert.equal(elements(container,'strong').length,4); // Inclui o destaque dentro da lista.
 assert.equal(elements(container,'hr').length,1);
 assert.equal(elements(container,'ul').length,1);
 const output=plain(container);
 assert.ok(!output.includes('##'));
 assert.ok(!output.includes('***'));
 assert.ok(!output.includes('**'));
 assert.equal(format.toPlainText(text),'Título principal\n\nTexto importante, ênfase maior e destaque.\n\nOrientações\n\n- Primeiro item\n- Segundo item');
});

test('não altera código com hashes, potência Python e markdown literal',()=>{
 const input='## Exemplo de código\n\n'+'```python\n'+'print("## é texto")\n'+'n = 2 ** 3\n'+'print("***")\n'+'```';
 const {container}=fakeDocument();
 format.render(container,input);
 const pre=elements(container,'pre');
 assert.equal(pre.length,1);
 assert.equal(elements(pre[0],'code')[0].textContent,'print("## é texto")\nn = 2 ** 3\nprint("***")');
 assert.equal(format.toPlainText(input),'Exemplo de código\n\nprint("## é texto")\nn = 2 ** 3\nprint("***")');
});

test('conteúdo malicioso nunca vira HTML executável; links só http/https',()=>{
 const input='<img src=x onerror=alert(1)>\n\n<script>alert("x")</script>\n\n[link](javascript:alert(1)) e [fonte](https://example.com/pagina)';
 const {container}=fakeDocument();
 format.render(container,input);
 const asHtml=escaped(container);
 assert.equal(elements(container,'img').length,0);
 assert.equal(elements(container,'script').length,0);
 assert.ok(asHtml.includes('&lt;img src=x'));
 assert.ok(asHtml.includes('&lt;script&gt;'));
 const links=elements(container,'a');
 assert.equal(links.length,1);
 assert.equal(links[0].href,'https://example.com/pagina');
 assert.equal(links[0].rel,'noopener noreferrer');
 assert.ok(plain(container).includes('[link](javascript:alert(1))'));
});

test('suporta listas numeradas, citações, cabeçalhos sem espaço e markdown incompleto',()=>{
 const text='##Título sem espaço\n\n1. Primeiro\n2. Segundo\n\n> Citação com **destaque**\n\n**incompleto';
 const {container}=fakeDocument();
 format.render(container,text);
 assert.equal(elements(container,'h3')[0].textContent,'Título sem espaço');
 assert.equal(elements(container,'ol')[0].childNodes.length,2);
 assert.equal(elements(container,'blockquote').length,1);
 assert.ok(!container.textContent.includes('**incompleto'));
 assert.ok(container.textContent.includes('incompleto'));
});

test('preserva textos de usuários e símbolos técnicos como código, sem interpolação HTML',()=>{
 const text='#include <iostream>\n\nNo Python escreva `x ** 2` e `## nota`.';
 const {container}=fakeDocument();
 format.render(container,text);
 assert.ok(plain(container).includes('#include <iostream>'));
 assert.ok(plain(container).includes('x ** 2'));
 assert.ok(plain(container).includes('## nota'));
 assert.equal(elements(container,'code').length,2);
 assert.equal(elements(container,'h3').length,0);
});

test('limita volume processado e trata entrada vazia ou inválida',()=>{
 assert.deepEqual(format.parseBlocks(null),[]);
 const text='# A\n\n'+('teste '.repeat(15000));
 const parsed=format.parseBlocks(text);
 assert.equal(parsed[0].type,'heading');
 assert.ok(parsed[1].text.length<=64000);
 const {container}=fakeDocument();
 assert.throws(()=>format.render(null,text),TypeError);
 assert.equal(format.render(container,''),container);
});
