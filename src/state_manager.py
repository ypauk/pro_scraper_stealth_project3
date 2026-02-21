# This class is responsible for saving and loading scraper checkpoints
import json
from pathlib import Path
from loguru import logger


class StateManager:
    def __init__(self, file_path: str = "data/checkpoint.json"):
        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

    def save_checkpoint(self, url: str, gathered_count: int = 0):
        """Save current scraping progress to a file"""
        state = {
            "last_url": url,
            "count": gathered_count
        }
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=4)
        logger.debug(f"💾 Checkpoint saved: {url}")

    def load_checkpoint(self) -> dict | None:
        """Load saved progress if it exists"""
        if self.file_path.exists():
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error reading state file: {e}")
        return None

    def clear_checkpoint(self):
        """Remove checkpoint file after successful completion"""
        if self.file_path.exists():
            self.file_path.unlink()
            logger.info("🧹 Checkpoint removed (scraping completed).")
