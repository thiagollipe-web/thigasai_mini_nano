/* THIGAS AI PWA — cache exclusivamente de recursos estáticos e públicos.
   NUNCA fazer cache de /api, navegação autenticada, documentos ou conversas. */
'use strict';
const CACHE_NAME='thigas-pwa-public-v1';
const PUBLIC_ASSETS=new Set([
 '/offline.html', '/manifest.webmanifest', '/assets/capivara.svg',
 '/assets/icon-180.png','/assets/icon-192.png',
 '/assets/icon-512.png','/assets/icon-maskable-512.png'
]);
self.addEventListener('install',event=>{
 event.waitUntil((async()=>{
  const cache=await caches.open(CACHE_NAME);
  await Promise.allSettled([...PUBLIC_ASSETS].map(async url=>{
   const response=await fetch(url,{credentials:'omit',cache:'no-store'});
   if(response.ok && response.type==='basic')await cache.put(url,response);
  }));
  await self.skipWaiting();
 })());
});
self.addEventListener('activate',event=>{
 event.waitUntil((async()=>{
  const names=await caches.keys();
  await Promise.all(names.filter(name=>name.startsWith('thigas-pwa-public-')&&name!==CACHE_NAME)
    .map(name=>caches.delete(name)));
  await self.clients.claim();
 })());
});
self.addEventListener('fetch',event=>{
 const req=event.request;
 if(req.method!=='GET')return;
 const url=new URL(req.url);
 if(url.origin!==self.location.origin||url.pathname.startsWith('/api/'))return;
 if(req.mode==='navigate'){
  // HTML exige autenticação: responder pela rede, nunca guardá-lo no cache.
  event.respondWith(fetch(req).catch(async()=>{
   const offline=await caches.match('/offline.html');
   return offline||new Response('Sem conexão. Conecte-se e tente novamente.',
     {status:503,headers:{'Content-Type':'text/plain; charset=utf-8'}});
  }));
  return;
 }
 if(PUBLIC_ASSETS.has(url.pathname)){
  event.respondWith((async()=>{
   const cache=await caches.open(CACHE_NAME);
   const result=await cache.match(url.pathname);
   if(result)return result;
   const fresh=await fetch(req);
   if(fresh.ok&&fresh.type==='basic')await cache.put(url.pathname,fresh.clone());
   return fresh;
  })());
 }
});
