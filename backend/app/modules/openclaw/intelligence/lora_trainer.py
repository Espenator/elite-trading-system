import argparse
import logging

logger = logging.getLogger(__name__)

_HAS_TORCH = False
try:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from peft import LoraConfig, prepare_model_for_kbit_training, get_peft_model
    from trl import DPOTrainer, DPOConfig
    from datasets import load_dataset
    _HAS_TORCH = True
except ImportError as _e:
    logger.info(f"LoRA trainer dependencies not available ({_e}); training disabled.")

def train_dpo(dataset_path: str, model_id="meta-llama/Meta-Llama-3-8B-Instruct"):
    if not _HAS_TORCH:
        raise RuntimeError("LoRA training requires torch, transformers, peft, trl, and datasets.")
    # 1. 4-bit Quantization to fit 24GB RTX VRAM
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16
    )

    # 2. Load Model & Tokenizer
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        model_id, quantization_config=bnb_config, device_map="auto"
    )
    model = prepare_model_for_kbit_training(model)

    model_ref = AutoModelForCausalLM.from_pretrained(
        model_id, quantization_config=bnb_config, device_map="auto"
    )

    # 3. LoRA Configuration (Targeting attention layers)
    peft_config = LoraConfig(
        r=16, lora_alpha=32, lora_dropout=0.05, bias="none",
        task_type="CAUSAL_LM", target_modules=["q_proj", "v_proj"]
    )
    model = get_peft_model(model, peft_config)

    # 4. Load Dataset
    dataset = load_dataset("json", data_files=dataset_path, split="train")

    # 5. DPO Training Loop
    training_args = DPOConfig(
        output_dir="./lora_adapters",
        per_device_train_batch_size=2, # Keep low for 24GB VRAM
        gradient_accumulation_steps=4,
        gradient_checkpointing=True,
        learning_rate=5e-5,
        optim="paged_adamw_32bit",
        max_length=1024,
        max_prompt_length=512
    )

    trainer = DPOTrainer(
        model=model,
        ref_model=model_ref,
        args=training_args,
        train_dataset=dataset,
        tokenizer=tokenizer,
        peft_config=peft_config
    )

    trainer.train()
    trainer.model.save_pretrained("./final_dpo_adapter")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True, help="Path to daily_dpo.jsonl")
    args = parser.parse_args()
    train_dpo(args.dataset)