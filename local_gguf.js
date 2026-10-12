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
 async function chat(messages,{effort='equilibrado'}={}){
  if(!llm||!info)throw Error('Carregue primeiro um GGUF no botão +.');
  if(!Array.isArray(messages)||!messages.length)throw Error('Mensagens inválidas.');
  const max_tokens=effort==='rapido'?240:effort==='alto'?850:480;
  const result=await llm.createChatCompletion({
   messages,max_tokens,temperature:effort==='rapido'?0.25:0.45,
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
 root.THIGASBrowserGGUF={load,chat,unload,getInfo,hasModel:()=>!!llm};
})(globalThis);
