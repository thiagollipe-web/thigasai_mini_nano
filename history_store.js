/* THIGAS AI - histórico local de conversas.
   Apenas texto, fontes públicas e preferências são persistidos.
   Anexos, imagens, conteúdo extraído de documentos e credenciais são descartados. */
(function(root,factory){
 'use strict';
 const api=factory();
 if(typeof module==='object'&&module.exports)module.exports=api;
 root.THIGASHistory=api;
})(typeof globalThis!=='undefined'?globalThis:this,function(){
 'use strict';
 const KEY='thigas_conversations_v1';
 const MAX_CHATS=80,MAX_MESSAGES=70,MAX_TEXT=4800,MAX_BYTES=1_700_000;
 const MODES=new Set(['rapido','equilibrado','alto']);
 const clamp=(s,n)=>typeof s==='string'?s.trim().slice(0,n):'';
 const cleanTitle=(s)=>clamp(s.replace(/\s+/g,' '),75)||'Nova conversa';
 const date=(s)=>typeof s==='string'&&!Number.isNaN(Date.parse(s))?s:new Date().toISOString();
 const normalizeMsg=(m)=>{
  if(!m||typeof m!=='object'||!['user','assistant'].includes(m.role)||typeof m.text!=='string')return null;
  const sources=Array.isArray(m.sources)?m.sources.filter(s=>s&&typeof s.titulo==='string'&&typeof s.url==='string'&&/^https:\/\/pt\.wikipedia\.org\//.test(s.url)).slice(0,4).map(s=>({titulo:clamp(s.titulo,130),url:clamp(s.url,350)})):[];
  return {role:m.role,text:clamp(m.text,MAX_TEXT),sources,notice:clamp(m.notice,350),failed:m.failed===true,attachmentUsed:m.attachmentUsed===true};
 };
 function normalize(chat){
  if(!chat||typeof chat!=='object'||typeof chat.id!=='string'||!chat.id||chat.id.length>110)return null;
  const messages=Array.isArray(chat.messages)?chat.messages.slice(-MAX_MESSAGES).map(normalizeMsg).filter(Boolean):[];
  if(!messages.length)return null;
  return {id:clamp(chat.id,110),title:cleanTitle(typeof chat.title==='string'?chat.title:'Nova conversa'),
   createdAt:date(chat.createdAt),updatedAt:date(chat.updatedAt),
   effort:MODES.has(chat.effort)?chat.effort:'equilibrado',wiki:chat.wiki===true,messages};
 }
 function sort(list){
  return list.slice().sort((a,b)=>Date.parse(b.updatedAt)-Date.parse(a.updatedAt)).slice(0,MAX_CHATS);
 }
 function load(storage){
  if(!storage)return [];
  try{
   const raw=storage.getItem(KEY);
   if(!raw||raw.length>MAX_BYTES*3)return [];
   const data=JSON.parse(raw);
   if(!Array.isArray(data))return [];
   const seen=new Set();
   return sort(data.map(normalize).filter(item=>{
    if(!item||seen.has(item.id))return false;
    seen.add(item.id);return true;
   }));
  }catch(_){return []}
 }
 function save(storage,conversations){
  if(!storage)return false;
  try{
   const seen=new Set();
   const prepared=sort((Array.isArray(conversations)?conversations:[])
    .map(normalize).filter(item=>{
     if(!item||seen.has(item.id))return false;
     seen.add(item.id);return true;
    }));
   let json=JSON.stringify(prepared);
   while(json.length>MAX_BYTES&&prepared.length>1){prepared.pop();json=JSON.stringify(prepared)}
   if(json.length>MAX_BYTES){
    prepared[0].messages=prepared[0].messages.slice(-12);
    json=JSON.stringify(prepared);
   }
   storage.setItem(KEY,json);
   return true;
  }catch(_){return false}
 }
 function make(title,options={}){
  const now=new Date().toISOString();
  const rand=typeof crypto!=='undefined'&&crypto.randomUUID?crypto.randomUUID():Date.now().toString(36)+'-'+Math.random().toString(36).slice(2);
  return {id:rand,title:cleanTitle(title),createdAt:now,updatedAt:now,
   effort:MODES.has(options.effort)?options.effort:'equilibrado',wiki:options.wiki===true,messages:[]};
 }
 function upsert(chats,chat){
  const base=Array.isArray(chats)?chats:[];
  const item=normalize(chat);
  if(!item)return base;
  return sort([item,...base.filter(c=>c.id!==item.id)]);
 }
 function remove(chats,id){return (Array.isArray(chats)?chats:[]).filter(c=>c.id!==id)}
 function rename(chats,id,title){
  const normalized=clamp(title,75).replace(/\s+/g,' ').trim();
  if(!normalized)return Array.isArray(chats)?chats:[];
  return (Array.isArray(chats)?chats:[]).map(c=>c.id===id?{...c,title:normalized,updatedAt:new Date().toISOString()}:c);
 }
 function lookup(chats,query){
  const q=typeof query==='string'?query.trim().normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLocaleLowerCase('pt-BR'):'';
  if(!q)return sort(Array.isArray(chats)?chats:[]);
  return sort((Array.isArray(chats)?chats:[]).filter(c=>{
   const hay=(c.title+' '+c.messages.filter(m=>m.role==='user').map(m=>m.text).join(' '))
    .normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLocaleLowerCase('pt-BR');
   return hay.includes(q);
  }));
 }
 function group(dateString,now=new Date()){
  const t=new Date(dateString);if(Number.isNaN(t.getTime()))return 'Anteriores';
  const start=new Date(now.getFullYear(),now.getMonth(),now.getDate());
  const given=new Date(t.getFullYear(),t.getMonth(),t.getDate());
  const delta=Math.round((start.getTime()-given.getTime())/86400000);
  if(delta<=0)return 'Hoje';
  if(delta===1)return 'Ontem';
  if(delta<7)return 'Últimos 7 dias';
  if(delta<30)return 'Últimos 30 dias';
  return 'Anteriores';
 }
 return {KEY,MAX_CHATS,load,save,make,upsert,remove,rename,lookup,group,normalize};
});
