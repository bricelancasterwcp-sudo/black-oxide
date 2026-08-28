#!/usr/bin/env python3
"""QLoRA fine-tune on the matched corpus — one recipe for all six runs.

Runs on the pod (torch/cu129). The prompt rendering is
harness.build_prompt(include_lead=False) — the exact string the eval
client sends — with the checkpoint's own chat template applied by the
tokenizer, mirroring llama-server's /v1/chat/completions rendering.
Loss is masked to the completion (the matched supervised tokens).
"""
import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

import torch
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    Trainer,
    TrainingArguments,
)

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from eval import harness  # noqa: E402

SEED = 17
LORA = dict(
    r=16, lora_alpha=32, lora_dropout=0.0, bias="none",
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                    "gate_proj", "up_proj", "down_proj"],
)
LR = 1e-4
EPOCHS = 3
MAX_LEN = 1024
TRAIN_TASKS = REPO / "eval" / "train" / "tasks.jsonl"


class Examples(torch.utils.data.Dataset):
    def __init__(self, records, arm, tok):
        self.items = []
        for rec in records:
            user = harness.build_prompt(
                arm, rec["task"], tasks_path=TRAIN_TASKS, include_lead=False
            )
            prompt_ids = tok.apply_chat_template(
                [{"role": "user", "content": user}],
                add_generation_prompt=True, tokenize=True,
            )
            prog_ids = tok(rec["text"], add_special_tokens=False)["input_ids"]
            prog_ids = prog_ids + [tok.eos_token_id]
            ids = (prompt_ids + prog_ids)[:MAX_LEN]
            labels = ([-100] * len(prompt_ids) + prog_ids)[:MAX_LEN]
            self.items.append({"input_ids": ids, "labels": labels})

    def __len__(self):
        return len(self.items)

    def __getitem__(self, i):
        return self.items[i]


def collate(batch, pad_id):
    width = max(len(b["input_ids"]) for b in batch)
    ids, labels, mask = [], [], []
    for b in batch:
        pad = width - len(b["input_ids"])
        ids.append(b["input_ids"] + [pad_id] * pad)
        labels.append(b["labels"] + [-100] * pad)
        mask.append([1] * len(b["input_ids"]) + [0] * pad)
    return {
        "input_ids": torch.tensor(ids),
        "labels": torch.tensor(labels),
        "attention_mask": torch.tensor(mask),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)   # HF id, -Instruct checkpoint
    ap.add_argument("--data", required=True, type=Path)  # matched jsonl
    ap.add_argument("--arm", required=True, choices=["oxide", "rust"])
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()

    torch.manual_seed(SEED)
    random.seed(SEED)
    tok = AutoTokenizer.from_pretrained(args.base)
    bnb = BitsAndBytesConfig(
        load_in_4bit=True, bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )
    model = AutoModelForCausalLM.from_pretrained(
        args.base, quantization_config=bnb, device_map="auto",
        torch_dtype=torch.bfloat16,
    )
    model = prepare_model_for_kbit_training(model)
    model = get_peft_model(model, LoraConfig(task_type="CAUSAL_LM", **LORA))

    records = [json.loads(l) for l in
               args.data.read_text(encoding="utf-8").splitlines()]
    ds = Examples(records, args.arm, tok)
    targs = TrainingArguments(
        output_dir=str(args.out), num_train_epochs=EPOCHS,
        learning_rate=LR, lr_scheduler_type="cosine",
        per_device_train_batch_size=4, gradient_accumulation_steps=2,
        bf16=True, logging_steps=10, save_strategy="no",
        seed=SEED, report_to=[],
    )
    Trainer(
        model=model, args=targs, train_dataset=ds,
        data_collator=lambda b: collate(b, tok.pad_token_id or tok.eos_token_id),
    ).train()
    model.save_pretrained(args.out)
    (args.out / "provenance.json").write_text(json.dumps({
        "base": args.base, "arm": args.arm,
        "data": str(args.data),
        "data_sha256": hashlib.sha256(args.data.read_bytes()).hexdigest(),
        "recipe": {"seed": SEED, "lr": LR, "epochs": EPOCHS,
                   "max_len": MAX_LEN, **{k: v for k, v in LORA.items()
                                          if k != "target_modules"},
                   "target_modules": LORA["target_modules"]},
        "n_examples": len(ds),
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"trained {args.arm} on {args.base}: {len(ds)} examples -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
