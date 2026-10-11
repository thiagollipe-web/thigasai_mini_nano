'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const store=require('../history_store.js');
function memory(){
 const entries=new Map();
 return {getItem(k){return entries.get(k)??null},setItem(k,v){entries.set(k,v)},removeItem(k){entries.delete(k)}};
}
const message=(role,text)=>({role,text});

test('salva e reabre múltiplas conversas com contexto independente',()=>{
 const storage=memory();
 const a=store.make('Astronomia',{effort:'alto',wiki:true});
 a.messages=[message('user','Explique a relatividade'),message('assistant','O tempo depende do referencial.')];
 const b=store.make('Programação',{effort:'rapido'});
 b.messages=[message('user','O que é Python?'),message('assistant','Uma linguagem de programação.')];
 assert.equal(store.save(storage,store.upsert([a],b)),true);
 const loaded=store.load(storage);
 assert.equal(loaded.length,2);
 assert.equal(loaded.find(c=>c.id===a.id).effort,'alto');
 assert.equal(loaded.find(c=>c.id===a.id).wiki,true);
 assert.equal(loaded.find(c=>c.id===a.id).messages[1].text,'O tempo depende do referencial.');
 assert.equal(loaded.find(c=>c.id===b.id).messages[0].text,'O que é Python?');
});
test('não salva imagens, documentos, chaves nem campos arbitrários',()=>{
 const storage=memory();
 const chat=store.make('Segurança');
 chat.messages=[{role:'user',text:'Olá',attachmentUsed:true,image:'data:image/png;base64,SECRETO',context:{texto:'CONTEUDO_PRIVADO'},api_key:'SEGREDO'}];
 chat.image='data:image/png;base64,SEGREDO';chat.context='DADOS_PRIVADOS';chat.token='SENHA';
 assert.equal(store.save(storage,[chat]),true);
 const json=storage.getItem(store.KEY);
 for(const secret of ['SECRETO','SEGREDO','CONTEUDO_PRIVADO','DADOS_PRIVADOS','SENHA','api_key','image','context']) assert.equal(json.includes(secret),false,secret);
 const restored=store.load(storage)[0];
 assert.equal(restored.messages[0].attachmentUsed,true);
});
test('recupera armazenamento inválido, limita textos e ignora mensagens não suportadas',()=>{
 const storage=memory();
 storage.setItem(store.KEY,'{{inválido');
 assert.deepEqual(store.load(storage),[]);
 const c=store.make('Grande');
 c.messages=[{role:'user',text:'x'.repeat(12000)},{role:'system',text:'Não armazenar'},{role:'assistant',text:'resposta'}];
 assert.equal(store.save(storage,[c]),true);
 const result=store.load(storage);
 assert.equal(result[0].messages.length,2);
 assert.equal(result[0].messages[0].text.length,4800);
});
test('busca sem acentos, renomeia, remove e agrupa por data',()=>{
 let list=[];
 const a=store.make('Língua Portuguesa');a.messages=[message('user','Atividade de ciências')];
 const b=store.make('História');b.messages=[message('user','Revolução Francesa')];
 list=store.upsert(list,a);list=store.upsert(list,b);
 assert.equal(store.lookup(list,'ciencias')[0].id,a.id);
 assert.equal(store.lookup(list,'francesa')[0].id,b.id);
 list=store.rename(list,a.id,'Nova aula');
 assert.equal(list.find(c=>c.id===a.id).title,'Nova aula');
 list=store.remove(list,b.id);assert.equal(list.length,1);
 assert.equal(store.group('2026-10-11T12:00:00Z',new Date('2026-10-11T13:00:00Z')),'Hoje');
});
test('gravação desabilitada não quebra a aplicação',()=>{
 const chat=store.make('Teste');chat.messages=[message('user','Olá')];
 assert.equal(store.save(null,[chat]),false);
 assert.deepEqual(store.load(null),[]);
 const broken={getItem(){throw Error('Storage desabilitado')},setItem(){throw Error('Bloqueado')}};
 assert.deepEqual(store.load(broken),[]);
 assert.equal(store.save(broken,[chat]),false);
});
