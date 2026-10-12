#!/usr/bin/env python3
"""Ajuste LoRA real do THIGAS AI: SmolLM2 360M / Qwen3 0.6B.

Os modelos de base já foram pré-treinados pelos respectivos autores.
Este código executa adaptação supervisionada e exporta pesos fundidos.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import statistics
import time
from pathlib import Path

import torch
from peft import LoraConfig, TaskType, get_peft_model
from transformers import AutoModelForCausalLM, AutoTokenizer

MODELS = {
    "nano": {
        "base": "HuggingFaceTB/SmolLM2-360M-Instruct",
        "steps": 40,
        "ctx": 2048,
        "label": "THIGAS AI nano, aproximadamente 0.3B",
    },
    "mini": {
        "base": "Qwen/Qwen3-0.6B",
        "steps": 45,
        "ctx": 4096,
        "label": "THIGAS AI mini, família 0.6B",
    },
}
SYSTEM = (
    "Você é o THIGAS AI, projeto experimental criado por Thiago Fillipe Soares. "
    "Responda em português do Brasil com clareza e precisão. Especialidades: educação, "
    "programação, ciência e pesquisa. Não invente fontes. Identifique limitações relevantes."
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant", choices=MODELS, required=True)
    parser.add_argument("--output", default="build_models")
    parser.add_argument("--steps", type=int, default=None)
    parser.add_argument("--train-context", type=int, default=320)
    args = parser.parse_args()
    spec = MODELS[args.variant]
    steps = spec["steps"] if args.steps is None else args.steps
    if not 1 <= steps <= 600 or not 96 <= args.train_context <= 1024:
        parser.error("Parâmetros de treino fora do intervalo")

    root = Path(args.output) / args.variant
    root.mkdir(parents=True, exist_ok=True)
    torch.manual_seed(20261011)
    random.seed(20261011)
    torch.set_num_threads(min(4, os.cpu_count() or 1))
    torch.set_num_interop_threads(1)

    with Path(__file__).with_name("instrucoes.jsonl").open(encoding="utf-8") as stream:
        samples = [json.loads(line) for line in stream if line.strip()]
    if len(samples) < 50:
        raise RuntimeError("Precisamos de pelo menos 50 exemplos de instrução.")
    random.shuffle(samples)
    validation = samples[-6:]
    training = samples[:-6]

    base = spec["base"]
    print(f"Carregando {base}; treinamento={len(training)}; validacao={len(validation)}", flush=True)
    tokenizer = AutoTokenizer.from_pretrained(base, trust_remote_code=False)
    if tokenizer.eos_token is None:
        raise RuntimeError("Tokenizer sem eos_token")
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        base, torch_dtype=torch.float32, low_cpu_mem_usage=True, trust_remote_code=False
    )
    model.config.use_cache = False
    lora = LoraConfig(
        r=8,
        lora_alpha=16,
        lora_dropout=0.0,
        target_modules=["q_proj", "v_proj"],
        bias="none",
        task_type=TaskType.CAUSAL_LM,
    )
    model = get_peft_model(model, lora)
    model.print_trainable_parameters()
    trainables = [p for p in model.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(trainables, lr=1.3e-4)

    def encode(example: dict) -> dict:
        opts = {"tokenize": False, "add_generation_prompt": True}
        if args.variant == "mini":
            opts["enable_thinking"] = False
        messages = [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": example["instruction"]},
        ]
        prompt = tokenizer.apply_chat_template(messages, **opts)
        prefix_ids = tokenizer(prompt, add_special_tokens=False)["input_ids"]
        answer_ids = tokenizer(
            example["response"] + tokenizer.eos_token, add_special_tokens=False
        )["input_ids"]
        all_ids = (prefix_ids + answer_ids)[: args.train_context]
        labels = ([-100] * len(prefix_ids) + answer_ids)[: args.train_context]
        if len(labels) != len(all_ids) or all(v == -100 for v in labels):
            raise RuntimeError("A resposta foi totalmente truncada.")
        return {
            "input_ids": torch.tensor([all_ids], dtype=torch.long),
            "attention_mask": torch.ones((1, len(all_ids)), dtype=torch.long),
            "labels": torch.tensor([labels], dtype=torch.long),
        }

    def evaluate() -> float:
        model.eval()
        with torch.no_grad():
            result = [float(model(**encode(item)).loss) for item in validation]
        return statistics.mean(result)

    start = time.monotonic()
    initial = evaluate()
    print("Loss validação inicial:", round(initial, 5), flush=True)
    logs = []
    model.train()
    for i in range(steps):
        item = training[(i * 13) % len(training)]
        loss = model(**encode(item)).loss
        if not torch.isfinite(loss):
            raise RuntimeError("Loss não finita.")
        loss.backward()
        torch.nn.utils.clip_grad_norm_(trainables, max_norm=1.0)
        opt.step()
        opt.zero_grad(set_to_none=True)
        if i == 0 or (i + 1) % 5 == 0 or i + 1 == steps:
            item_log = {"step": i + 1, "train_loss": round(float(loss), 5)}
            logs.append(item_log)
            print(f"{i+1}/{steps}: loss={float(loss):.5f}; segundos={int(time.monotonic()-start)}", flush=True)

    final = evaluate()
    print("Loss validação final:", round(final, 5), flush=True)
    model.save_pretrained(root / "adapter", safe_serialization=True)
    tokenizer.save_pretrained(root / "adapter")
    print("Fazendo merge do LoRA...", flush=True)
    model.eval()
    merged = model.merge_and_unload()
    merged.config.use_cache = True
    merged.save_pretrained(root / "merged", safe_serialization=True, max_shard_size="1GB")
    tokenizer.save_pretrained(root / "merged")
    report = {
        "model": spec["label"],
        "base_model": base,
        "method": "fine-tuning LoRA r=8 em q_proj/v_proj + merge completo",
        "training_steps": steps,
        "train_examples": len(training),
        "validation_examples": len(validation),
        "max_training_tokens": args.train_context,
        "requested_inference_context": spec["ctx"],
        "loss_validation_before": round(initial, 5),
        "loss_validation_after": round(final, 5),
        "training_seconds": int(time.monotonic() - start),
        "logs": logs,
        "disclaimer": "Treino curto de identidade. A base é pré-treinada; fluência não foi medida por benchmark independente.",
    }
    (root / "report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print("Checkpoint LoRA e pesos mesclados salvos.", flush=True)


if __name__ == "__main__":
    main()
