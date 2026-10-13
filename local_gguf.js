/* THIGAS AI — GGUF local no navegador via wllama 3.8.1.
   O modelo é escolhido explicitamente pelo usuário e nunca enviado ao servidor. */
(function(root){
 'use strict';
 let llm=null,info=null;
 const MAX_FILE=1_300_000_000;
 async function load(file){
  if(!file||typeof file.name!=='string'||!file.name.toLowerCase().endsWith('.gguf'))
   throw Error('Selecione um arquivo GGUF válido.');
  if(file.size>MAX_FILE||file.size<100_000)
   throw Error('GGUF fora do tamanho suportado (100 KB a 1,3 GB).');
  const header=new Uint8Array(await file.slice(0,4).arrayBuffer());
  if(header[0]!==71||header[1]!==71||header[2]!==85||header[3]!==70)
   throw Error('O arquivo não possui assinatura GGUF.');
  const name=file.name;
  const kind=/nano/i.test(name)?'nano':/mini/i.test(name)?'mini':'outro';
  const ctx=kind==='mini'?4096:2048;
  if(llm){try{await llm.exit()}catch(_){}llm=null;info=null}
  if(typeof SharedArrayBuffer==='undefined'){
   throw Error('O navegador precisa de isolamento de origem para carregar o modelo. Use Chrome ou Edge atualizado em HTTPS.');
  }
  const {Wllama}=await import('/assets/wllama/esm/index.js');
  const worker=new Wllama({default:'/assets/wllama/esm/wasm/wllama.wasm'});
  try{
   await worker.loadModel([file],{n_ctx:ctx,n_threads:1,n_gpu_layers:0,jinja:true});
  }catch(error){
   try{await worker.exit()}catch(_){}
   throw Error('Não foi possível carregar o GGUF. Verifique a memória do aparelho: '+String(error?.message||error));
  }
  llm=worker;
  info={name,kind,context:ctx,bytes:file.size};
  return {...info};
 }
 // Seleciona teto de saída com reserva de contexto: contar caracteres
 // não substitui o tokenizador real, mas é uma estimativa conservadora.
 function planGeneration(messages, effort='equilibrado', context=2048){
  if(!Array.isArray(messages)||!messages.length||
     messages.some(m=>!m||typeof m.content!=='string'))
   throw Error('Mensagens inválidas.');
  const maxCtx=Math.max(256,Math.min(32768,Number(context)||2048));
  const desired=effort==='rapido'?460:effort==='alto'?1250:800;
  const chars=messages.reduce((sum,m)=>sum+m.content.length,0);
  const approximateInput=Math.ceil(chars/2.5)+messages.length*20+80;
  // Uma entrada volumosa precisa de um teto menor ou de resumo antes da geração.
  const room=maxCtx-approximateInput-96;
  if(room<96)
   throw Error('O conteúdo supera a janela de contexto do GGUF. Reduza o histórico ou anexo e tente novamente.');
  return Math.max(96,Math.min(desired,room));
 }
 async function chat(messages,{effort='equilibrado'}={}){
  if(!llm||!info)throw Error('Carregue primeiro um GGUF no botão +.');
  const max_tokens=planGeneration(messages,effort,info.context);
  const result=await llm.createChatCompletion({
   messages,max_tokens,temperature:effort==='rapido'?0.25:0.4,
   stream:false,chat_template_kwargs:{enable_thinking:false}
  });
  const choice=result?.choices?.[0];
  const output=choice?.message?.content;
  if(typeof output!=='string'||!output.trim())
   throw Error('GGUF carregado, mas não produziu texto nesta tentativa.');
  return output.trim();
 }
 async function unload(){
  const old=llm;llm=null;info=null;
  if(old){try{await old.exit()}catch(_){}}
 }
 function getInfo(){return info?{...info}:null}
 root.THIGASBrowserGGUF={load,chat,unload,getInfo,planGeneration,hasModel:()=>!!llm};
})(globalThis);
