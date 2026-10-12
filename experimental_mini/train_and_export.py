#!/usr/bin/env python3
"""THIGAS AI mini experimental — ENTIRELY NEW GPT2, NOT previous Mini weights.
Minimal educational proof-of-training. Not conversational or production-ready.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import random
import struct
import time
import numpy as np
import torch
from model import GPT, GPTConfig

ROOT=Path(__file__).resolve().parent
OUT=ROOT.parent/'models'
OUT.mkdir(exist_ok=True)
STEPS=int(os.environ.get('THIGAS_TRAIN_STEPS','250'))
if not 20<=STEPS<=2000:raise ValueError('steps outside safety range')
random.seed(20261011);torch.manual_seed(20261011);torch.set_num_threads(2)

# Texto original de demonstração em português. Não representa pretreinamento extensivo.
TOPICS=[
 ('Língua portuguesa','Uma frase expressa uma ideia. A oração tem um verbo; concordância relaciona o verbo ao sujeito. A leitura exige interpretar ideias explícitas e inferências.'),
 ('Leitura','A leitura crítica compara informações, fontes e argumentos. Um resumo preserva as ideias essenciais sem copiar todos os detalhes.'),
 ('Tecnologia','Um computador executa instruções digitais. Programar envolve definir algoritmos, testar resultados e corrigir erros.'),
 ('Python','Em Python, uma função é declarada com def; uma lista armazena elementos. A indentação delimita blocos de código.'),
 ('HTML','HTML representa a estrutura de páginas web. CSS define apresentação. JavaScript adiciona lógica e interação no navegador.'),
 ('Scratch','Scratch usa blocos gráficos para criar algoritmos, animações e jogos educativos sem escrever sintaxe textual.'),
 ('Sociologia','A sociologia estuda relações sociais, instituições, cultura, desigualdades e transformações nas sociedades.'),
 ('Cidadania digital','A cidadania digital inclui privacidade, respeito, verificação de fontes e proteção das pessoas na internet.'),
 ('Cyberbullying','O cyberbullying envolve agressões e humilhações repetidas por meios digitais. É importante registrar evidências, denunciar e procurar ajuda.'),
 ('Física','A velocidade mede a variação de posição no tempo. A aceleração mede a variação da velocidade. A energia pode ser transferida.'),
 ('Biologia','Células são unidades estruturais dos seres vivos. A fotossíntese transforma energia luminosa em energia química.'),
 ('Química','O número de prótons caracteriza um elemento químico. Reações transformam substâncias por reorganização de átomos.'),
 ('Matemática','Uma fração representa parte ou razão. Porcentagem usa base cem. A resolução de problemas requer verificar as unidades.'),
 ('História','O conhecimento histórico analisa mudanças e permanências no tempo, comparando testemunhos e documentos com contexto.'),
 ('Geografia','Mapas usam escalas e legendas para representar o espaço. Clima descreve padrões; tempo é condição atmosférica momentânea.'),
 ('Educação','Ensinar envolve objetivos claros, atividades adequadas, avaliação e diferentes formas de participação do estudante.'),
 ('Pesquisa','Uma hipótese científica deve ser testável. Resultados exigem registros, análise dos dados e reconhecimento de limites.'),
 ('Estatística','A média é soma dividida pela contagem. A mediana é o valor central da série ordenada. Correlação não prova causalidade.'),
 ('Segurança','Senhas únicas, autenticação multifator e atualizações reduzem riscos de invasão e vazamento de dados.'),
 ('Software livre','Uma licença de código define direitos de uso, distribuição, modificação e compartilhamento.'),
 ('Redação','Um texto argumentativo apresenta tese e argumentos sustentados por evidências; a conclusão retoma a ideia central.'),
 ('Inteligência artificial','Modelos de linguagem aprendem padrões estatísticos de textos. Respostas podem conter erros e devem ser verificadas.'),
 ('Wikipédia','A Wikipédia é uma enciclopédia colaborativa; fontes e histórico de edições ajudam a avaliar as afirmações.'),
 ('Jogos educativos','Jogos podem oferecer desafios progressivos, feedback claro e oportunidades de testar hipóteses.'),
 ('Algoritmos','Algoritmos são sequências de passos. Condições e laços permitem controlar decisões e repetições.')
]
examples=[]
for title,answer in TOPICS:
 examples.append('THIGAS AI mini — material de treinamento demonstrativo.\n')
 examples.append('Pergunta: O que é '+title+'?\nResposta: '+answer+'\n')
 examples.append('Explique '+title+' para um estudante.\nResposta: '+answer+'\n\n')
base=''.join(examples)
# Mesmo corpus sintético com repetições; validação NÃO prova generalização.
full=base*16
encoded=full.encode('utf-8')
cut=int(len(encoded)*.9)
train=torch.tensor(list(encoded[:cut]),dtype=torch.long)
val=torch.tensor(list(encoded[cut:]),dtype=torch.long)
args=dict(n_layer=6,n_head=6,n_embd=288,block_size=128,vocab_size=257,bias=True,dropout=0.0)
model=GPT(GPTConfig(**args))
count=sum(p.numel() for p in model.parameters())
optim=torch.optim.AdamW(model.parameters(),lr=0.001,betas=(0.9,0.95),weight_decay=.03)
ctx=128
def getbatch(src,bs=4):
 ix=torch.randint(0,len(src)-ctx-1,(bs,))
 return torch.stack([src[i:i+ctx] for i in ix.tolist()]),torch.stack([src[i+1:i+ctx+1] for i in ix.tolist()])
@torch.no_grad()
def evaluate():
 model.eval()
 out=[]
 for i in range(4):
  x,y=getbatch(val,2);_,loss=model(x,y);out.append(float(loss.item()))
 model.train()
 return round(sum(out)/len(out),6)
loss_start=evaluate()
print('inicio: 6 camadas, vocab 257, params',count,'tokens',len(train),'loss_val',loss_start,flush=True)
t0=time.time()
for step in range(1,STEPS+1):
 x,y=getbatch(train);_,loss=model(x,y)
 optim.zero_grad(set_to_none=True)
 loss.backward()
 torch.nn.utils.clip_grad_norm_(model.parameters(),1)
 optim.step()
 if step%25==0 or step==1:
  print('passo',step,'de',STEPS,'loss',round(float(loss.item()),5),'tempo_s',round(time.time()-t0,1),flush=True)
loss_end=evaluate()
st={k:v.detach().cpu() for k,v in model.state_dict().items()}
torch.save({'model':st,'model_args':args,'steps':STEPS,
            'corpus_sha256':hashlib.sha256(encoded).hexdigest(),
            'validation_loss_before':loss_start,'validation_loss_after':loss_end},OUT/'THIGAS_AI_mini_experimental-6M-ckpt.pt')
def ggufstr(b):
 b=b.encode('utf-8') if isinstance(b,str) else b
 return struct.pack('<Q',len(b))+b
def encode_bytes():
 bs=list(range(33,127))+list(range(161,173))+list(range(174,256))
 cs=bs[:];n=0
 for b in range(256):
  if b not in bs:bs.append(b);cs.append(256+n);n+=1
 return {b:chr(c) for b,c in zip(bs,cs)}
S=8;U=4;F=6;A=9;I=5;B=7
tokens=[encode_bytes()[i] for i in range(256)]+['<|endoftext|>']
meta=[
 ('general.architecture',S,'gpt2'),
 ('general.name',S,'THIGAS AI mini experimental'),
 ('general.description',S,'Treinado do zero com corpus pequeno; NAO e checkpoint anterior nem IA conversacional.'),
 ('general.file_type',U,1),
 ('general.alignment',U,32),
 ('gpt2.block_count',U,6),('gpt2.context_length',U,128),
 ('gpt2.embedding_length',U,288),('gpt2.feed_forward_length',U,1152),
 ('gpt2.attention.head_count',U,6),
 ('gpt2.attention.layer_norm_epsilon',F,1e-5),
 ('tokenizer.ggml.model',S,'gpt2'),('tokenizer.ggml.pre',S,'gpt-2'),
 ('tokenizer.ggml.tokens',A,(S,tokens)),
 ('tokenizer.ggml.merges',A,(S,[])),
 ('tokenizer.ggml.token_type',A,(I,[1]*256+[3])),
 ('tokenizer.ggml.eos_token_id',U,256),
 ('tokenizer.ggml.bos_token_id',U,256),
 ('tokenizer.ggml.add_bos_token',B,False),
 ('tokenizer.ggml.add_eos_token',B,False),
 ('training.iterations',U,STEPS)]
def packmeta(k,t,v):
 data=ggufstr(k)+struct.pack('<I',t)
 if t==S:data+=ggufstr(v)
 elif t==U:data+=struct.pack('<I',v)
 elif t==F:data+=struct.pack('<f',v)
 elif t==B:data+=struct.pack('<B',bool(v))
 elif t==A:
  et,values=v
  data+=struct.pack('<IQ',et,len(values))
  for el in values:
   if et==S:data+=ggufstr(el)
   elif et==I:data+=struct.pack('<i',el)
   else:raise ValueError('unsupported')
 else:raise ValueError('unsupported meta type')
 return data
weights={}
for name in ('transformer.wte.weight','transformer.wpe.weight','transformer.ln_f.weight','transformer.ln_f.bias'):
 to={'transformer.wte.weight':'token_embd.weight','transformer.wpe.weight':'position_embd.weight',
     'transformer.ln_f.weight':'output_norm.weight','transformer.ln_f.bias':'output_norm.bias'}[name]
 weights[to]=st[name]
mapping={'ln_1':'attn_norm','attn.c_attn':'attn_qkv','attn.c_proj':'attn_output',
         'ln_2':'ffn_norm','mlp.c_fc':'ffn_up','mlp.c_proj':'ffn_down'}
for layer in range(6):
 for source,target in mapping.items():
  for suffix in ('weight','bias'):
   weights['blk.%d.%s.%s'%(layer,target,suffix)]=st['transformer.h.%d.%s.%s'%(layer,source,suffix)]
data_chunks=[]
tensor_meta=[]
position=0
for name,weight in weights.items():
 weight=weight.detach().cpu().contiguous()
 dtype=torch.float16 if weight.ndim>1 else torch.float32
 weight=weight.to(dtype)
 raw=weight.numpy().tobytes()
 position=(position+31)//32*32
 dims=list(reversed(weight.shape))
 tensor_meta.append((name,dims,1 if weight.ndim>1 else 0,position))
 data_chunks.append((position,raw))
 position+=len(raw)
header=bytearray(b'GGUF'+struct.pack('<IQQ',3,len(tensor_meta),len(meta)))
for k,t,v in meta:header+=packmeta(k,t,v)
for name,dims,kind,pos in tensor_meta:
 header+=ggufstr(name)+struct.pack('<I',len(dims))
 header+=struct.pack('<'+'Q'*len(dims),*dims)
 header+=struct.pack('<IQ',kind,pos)
header+=bytes((-len(header))%32)
output=OUT/'THIGAS_AI_mini_experimental-6M-F16.gguf'
with output.open('wb') as f:
 f.write(header)
 position=0
 for offset,raw in data_chunks:
  f.write(bytes(offset-position))
  f.write(raw)
  position=offset+len(raw)
report={
 'nome':'THIGAS AI mini EXPERIMENTAL 6M',
 'treinamento':'novo, a partir de pesos aleatórios; NÃO é o Mini anterior de Termux/Colab',
 'base':'nanoGPT (MIT), arquitetura GPT-2',
 'parametros':count,'blocos':6,'dimensao_embedding':288,'cabecas':6,
 'contexto':128,'vocabulario':257,'iteracoes':STEPS,
 'tokens_de_treino':len(train),'loss_validacao_inicial':loss_start,
 'loss_validacao_final':loss_end,
 'sha256_corpus':hashlib.sha256(encoded).hexdigest(),
 'arquivo_gguf':output.name,'bytes_gguf':output.stat().st_size,
 'sha256_gguf':hashlib.sha256(output.read_bytes()).hexdigest(),
 'limitacoes':'Exemplo técnico sobre textos pequenos e repetidos; não serve para conversa coerente.'
}
(OUT/'THIGAS_AI_mini_experimental-6M.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('RESULTADO',json.dumps(report,ensure_ascii=False),flush=True)
