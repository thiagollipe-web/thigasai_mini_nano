'use strict';
const test=require('node:assert/strict');
const { chromium }=require('playwright');

const BASE='http://127.0.0.1:18019';

(async()=>{
 const browser=await chromium.launch({headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
 const context=await browser.newContext({httpCredentials:{username:'thigas',password:'senha-de-testes-segura'}});
 const page=await context.newPage();
 const cases=[
  {width:1440,height:900,device:'desktop'},
  {width:1024,height:768,device:'desktop'},
  {width:820,height:850,device:'mobile'},
  {width:390,height:844,device:'mobile'},
  {width:320,height:720,device:'mobile'}
 ];
 try{
  for(const scenario of cases){
   await page.setViewportSize({width:scenario.width,height:scenario.height});
   const response=await page.goto(BASE+'/',{waitUntil:'load',timeout:60000});
   test.equal(response.status(),200);
   const layout=await page.evaluate(()=>{
    const rect=sel=>{
     const r=document.querySelector(sel).getBoundingClientRect();
     return {x:r.x,y:r.y,left:r.left,right:r.right,top:r.top,bottom:r.bottom,
       width:r.width,height:r.height,cx:r.x+r.width/2,cy:r.y+r.height/2};
    };
    return {
     toggle:rect('#sidebar-toggle'),
     svg:rect('#sidebar-toggle svg'),
     logo:rect('.top-inner .brand img'),
     brandText:rect('.top-inner .brand strong'),
     actions:rect('.top-inner .top-actions'),
     left:rect('.top-inner .header-left'),
     header:rect('.top-inner'),
     svgPath:document.querySelector('#sidebar-toggle svg path')?.getAttribute('d'),
     sidebarExpanded:document.querySelector('#sidebar-toggle').getAttribute('aria-expanded'),
     overflow:document.documentElement.scrollWidth>window.innerWidth,
    };
   });
   console.log('TAMANHO '+scenario.width+'px: '+JSON.stringify(layout));
   test.equal(layout.svgPath,'M4 6h16 M4 12h16 M4 18h16','Três linhas simétricas');
   test.ok(Math.abs(layout.toggle.cy-layout.logo.cy)<=1.6,'Botão e capivara precisam estar alinhados no eixo vertical');
   test.ok(Math.abs(layout.toggle.cy-layout.svg.cy)<=1,'SVG centralizado verticalmente no botão');
   test.ok(Math.abs(layout.toggle.cx-layout.svg.cx)<=1,'SVG centralizado horizontalmente');
   test.ok(layout.logo.left-layout.toggle.right>=2 && layout.logo.left-layout.toggle.right<=19,
    'Botão precisa ficar próximo ao logo na mesma região do cabeçalho');
   test.ok(layout.toggle.x>=0 && layout.toggle.right<=scenario.width,
    'Botão não pode sair da tela');
   test.ok(layout.brandText.right<=layout.actions.left+2,
    'Nome THIGAS AI não deve invadir os botões à direita');
   test.equal(layout.overflow,false,'Cabeçalho não pode causar scroll horizontal');

   const toggle=page.locator('#sidebar-toggle');
   if(scenario.device==='desktop'){
    test.equal(await toggle.getAttribute('aria-expanded'),'true');
    await toggle.click();
    test.equal(await toggle.getAttribute('aria-expanded'),'false');
    await toggle.click();
    test.equal(await toggle.getAttribute('aria-expanded'),'true');
   }else{
    test.equal(await toggle.getAttribute('aria-expanded'),'false');
    await toggle.click();
    test.equal(await toggle.getAttribute('aria-expanded'),'true');
    test.equal(await page.locator('#history-sidebar').evaluate(x=>x.classList.contains('open')),true);
    await page.locator('#history-close').click();
    test.equal(await toggle.getAttribute('aria-expanded'),'false');
   }
  }
  console.log('VALIDAÇÃO DO ALINHAMENTO E INTERAÇÃO CONCLUÍDA');
 }catch(error){
  console.error(error.stack||error);
  try{await page.screenshot({path:'header-alignment-failure.png',fullPage:true})}catch(_){}
  process.exitCode=1;
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
