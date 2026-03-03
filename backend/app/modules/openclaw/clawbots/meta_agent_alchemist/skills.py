import json
import logging
import subprocess
import os

logger = logging.getLogger(__name__)

class NightlyAlchemist:
    def __init__(self, pnl_database, output_dir="./training_data"):
        self.db = pnl_database
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def format_dpo_dataset(self):
        """Extracts daily logs and formats into DPO JSONL schema."""
        trades = self.db.get_daily_trades()
        dataset_path = os.path.join(self.output_dir, "daily_dpo.jsonl")

        with open(dataset_path, "w") as f:
            for trade in trades:
                if trade.profit > 0 and trade.counter_trade.profit <= 0:
                    dpo_row = {
                        "prompt": trade.original_llm_prompt,
                        "chosen": trade.llm_response,
                        "rejected": trade.counter_trade.llm_response
                    }
                    f.write(json.dumps(dpo_row) + "\n")
        return dataset_path

    def trigger_lora_training(self, dataset_path: str):
        """Spawns the OS-level PyTorch training job."""
        logger.info("Triggering RTX DPO Fine-Tuning on %s...", dataset_path)
        subprocess.run(["python", "lora_trainer.py", "--dataset", dataset_path], check=True)