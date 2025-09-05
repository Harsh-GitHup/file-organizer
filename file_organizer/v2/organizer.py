# file_organizer/v2/organizer.py

import json
import shutil
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Tuple
from appdirs import user_data_dir  # type: ignore

APP_NAME = "FileOrganizer"
APP_AUTHOR = "Harsh"

DATA_DIR = Path(user_data_dir(APP_NAME, APP_AUTHOR))
DATA_DIR.mkdir(parents=True, exist_ok=True)

CONFIG_PATH = DATA_DIR / "organizer_config.json"
LAST_RUN_PATH = DATA_DIR / "last_run.json"
LOG_PATH = DATA_DIR / "organizer.log"

# setup logging
logger = logging.getLogger("organizer")
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler(LOG_PATH, encoding="utf-8")
fh.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
if not logger.handlers:
    logger.addHandler(fh)

DEFAULT_CONFIG = {
    "categories": {
        "Images": {"extensions": [".jpg", ".jpeg", ".png"], "destination": ""},
        "Videos": {"extensions": [".mp4", ".mkv"], "destination": ""},
        "Documents": {"extensions": [".pdf", ".docx", ".txt"], "destination": ""},
    },
    "others_destination": "",
    "monitoring_enabled": True,
    "monitor_patterns": ["*"],
}


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        if "categories" not in cfg:
            cfg["categories"] = DEFAULT_CONFIG["categories"]
        return cfg
    except Exception as e:
        logger.error(f"Config corrupted, using defaults: {e}")
        return DEFAULT_CONFIG.copy()


def save_config(cfg: dict):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


def _unique_dest(dest: Path) -> Path:
    if not dest.exists():
        return dest
    parent, stem, suffix = dest.parent, dest.stem, dest.suffix
    i = 1
    while True:
        candidate = parent / f"{stem}_{i}{suffix}"
        if not candidate.exists():
            return candidate
        i += 1


def categorize_file(file: Path, cfg: dict) -> Tuple[str, Path]:
    ext = file.suffix.lower()
    for cat, info in cfg.get("categories", {}).items():
        if ext in [e.lower() for e in info.get("extensions", [])]:
            dest_root = info.get("destination", "")
            return cat, Path(dest_root)
    return "Others", Path(cfg.get("others_destination", "") or "")


def build_preview(sources: List[Path], cfg: dict) -> list[dict]:
    fallback_root = Path(
        cfg.get("others_destination")
        or cfg.get("default_destination")
        or str(Path.home() / "Organized")
    )

    def resolve_dest(file: Path) -> Tuple[str, Path]:
        cat, root = categorize_file(file, cfg)
        return cat, (root if str(root) else fallback_root)

    plan: list[dict] = []
    for folder in sources:
        if not folder.is_dir():
            continue
        for file in folder.iterdir():
            if not file.is_file():
                continue
            cat, dest_root = resolve_dest(file)
            plan.append({
                "src": str(file),
                "category": cat,
                "planned_dest": str(dest_root / file.name),
            })
    return plan

def perform_moves(plan: list[Dict]) -> list[Dict]:
    performed = []
    for entry in plan:
        src = Path(entry["src"])
        dest = Path(entry["planned_dest"])
        dest.parent.mkdir(parents=True, exist_ok=True)
        safe_dest = _unique_dest(dest)
        try:
            shutil.move(str(src), str(safe_dest))
            performed.append({"src": str(src), "dest": str(safe_dest)})
        except Exception as e:
            logger.error(f"Failed to move {src}: {e}")
    if performed:
        with open(LAST_RUN_PATH, "w", encoding="utf-8") as f:
            json.dump(
                {"moves": performed, "timestamp": datetime.now(
                    timezone.utc).isoformat()},
                f, indent=2
            )
    return performed


def undo_last_run() -> Tuple[bool, str]:
    if not LAST_RUN_PATH.exists():
        return False, "No last run recorded."
    with open(LAST_RUN_PATH, "r", encoding="utf-8") as f:
        record = json.load(f)
    moves = record.get("moves", [])
    failures = []
    for mv in reversed(moves):
        try:
            src, dest = Path(mv["dest"]), Path(mv["src"])
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(_unique_dest(dest)))
        except Exception as e:
            failures.append(f"{src} -> {dest}: {e}")
    if failures:
        return False, "Some undo's failed:\n" + "\n".join(failures)
    LAST_RUN_PATH.unlink(missing_ok=True)
    return True, f"Undid {len(moves)} moves."
