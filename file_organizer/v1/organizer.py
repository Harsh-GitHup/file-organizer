# file_organizer\v1\organizer.py

"""
organizer.py
Core organizing logic for File Organizer:
- build preview plan for a set of source folders
- perform safe moves (duplicate-proof)
- write logs and last run mapping (for Undo)
- helper to load/save config file
"""

import json
import shutil
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Tuple
from appdirs import user_data_dir # type: ignore
APP_NAME = "FileOrganizer"
APP_AUTHOR = "Harsh"

DATA_DIR = Path(user_data_dir(APP_NAME, APP_AUTHOR))
DATA_DIR.mkdir(parents=True, exist_ok=True)

CONFIG_PATH = DATA_DIR / "organizer_config.json"
LAST_RUN_PATH = DATA_DIR / "last_run.json"
LOG_PATH = DATA_DIR / "organizer.log"

# set up logging
logger = logging.getLogger("organizer")
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler(LOG_PATH, encoding="utf-8")
fh.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(fh)

DEFAULT_CONFIG = {
    "categories": {
        "Images": {
            "extensions": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp"],
            "destination": ""
        },
        "Videos": {
            "extensions": [".mp4", ".mkv", ".mov", ".avi", ".webm"],
            "destination": ""
        },
        "Documents": {
            "extensions": [".pdf", ".docx", ".doc", ".txt", ".pptx", ".xlsx", ".odt"],
            "destination": ""
        },
        "Archives": {
            "extensions": [".zip", ".rar", ".tar", ".gz", ".7z"],
            "destination": ""
        },
        "Code": {
            "extensions": [".py", ".js", ".java", ".cpp", ".c", ".cs", ".html", ".css"],
            "destination": ""
        }
    },
        "others_destination": "",
        "safe_mode": True,
        "move_on_preview_confirm": True,
        "monitoring_enabled": True,
        "monitor_patterns": ["*"]
    }

def load_config() -> dict:
    if not CONFIG_PATH.exists():
        save_config(DEFAULT_CONFIG)
        logger.info(f"Saved default config to {CONFIG_PATH}")
        return DEFAULT_CONFIG.copy()
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    # ensure shape validity
    if "categories" not in cfg:
        cfg["categories"] = DEFAULT_CONFIG["categories"]
    return cfg


def save_config(cfg: dict):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
    logger.info(f"Config saved to {CONFIG_PATH}")


def _unique_dest(dest: Path) -> Path:
    """Return a duplicate-proof path: if dest exists, append _1, _2, ..."""
    if not dest.exists():
        return dest
    parent = dest.parent
    stem = dest.stem
    suffix = dest.suffix
    counter = 1
    while True:
        candidate = parent / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def categorize_file(file: Path, cfg: dict) -> Tuple[str, Path]:
    """
    Return (category_name, destination_folder_path) for a file according to config.
    If category destination is empty, the default is source_folder/<Category>.
    """
    ext = file.suffix.lower()
    for cat, catinfo in cfg.get("categories", {}).items():
        exts = [e.lower() for e in catinfo.get("extensions", [])]
        if ext in exts:
            dest_root = catinfo.get("destination", "") or ""
            return cat, Path(dest_root)
    # others
    return "Others", Path(cfg.get("others_destination", "") or "")


def build_preview(sources: List[Path], cfg: dict) -> List[Dict]:
    """
    Build preview plan for files in sources (non-recursive by default, but we include files in root only).
    Returns list of dicts: {src: str, category: str, planned_dest: str}
    """
    plan = []
    for source in sources:
        if not source.exists():
            logger.warning(f"Source not found: {source}")
            continue
        for item in source.iterdir():
            if item.is_file():
                category, dest_root = categorize_file(item, cfg)
                # determine destination folder
                if dest_root and dest_root.is_absolute():
                    target_folder = dest_root / category
                else:
                    target_folder = source / category
                planned_dest = target_folder / item.name
                plan.append({
                    "src": str(item),
                    "category": category,
                    "planned_dest": str(planned_dest)
                })
    return plan


def perform_moves(plan: List[Dict]) -> List[Dict]:
    """
    Execute safe moves according to plan. Returns a list of performed moves:
    [{src:..., dest:..., moved_to:...}, ...]
    Writes last_run.json for Undo.
    """
    performed = []
    for entry in plan:
        src = Path(entry["src"])
        dest_dir = Path(entry["planned_dest"]).parent
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / src.name
        safe_dest = _unique_dest(dest)
        try:
            shutil.move(str(src), str(safe_dest))
            logger.info(f"Moved: {src} -> {safe_dest}")
            performed.append({"src": str(src), "dest": str(safe_dest)})
        except Exception as e:
            logger.exception(f"Failed to move {src} -> {safe_dest}: {e}")
    # write last run for undo
    # write last run for undo
    if performed:
        record = {"timestamp": datetime.now(timezone.utc).isoformat(), "moves": performed}
        with open(LAST_RUN_PATH, "w", encoding="utf-8") as f:
            json.dump(record, f, indent=2)
        logger.info(f"Wrote last run with {len(performed)} moves to {LAST_RUN_PATH}")
    return performed

def undo_last_run() -> Tuple[bool, str]:
    """Restore files moved in last run by reversing moves. Returns (ok, message)."""
    if not LAST_RUN_PATH.exists():
        return False, "No last run recorded."
    with open(LAST_RUN_PATH, "r", encoding="utf-8") as f:
        record = json.load(f)
    moves = record.get("moves", [])
    failures = []
    for mv in reversed(moves):  # reverse order
        src = Path(mv["dest"])
        dest = Path(mv["src"])
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            # if dest exists, make unique backup name
            final_dest = _unique_dest(dest) if dest.exists() else dest
            shutil.move(str(src), str(final_dest))
            logger.info(f"Undid move: {src} -> {final_dest}")
        except Exception as e:
            logger.exception(f"Failed to undo {src} -> {dest}: {e}")
            failures.append(f"{src} -> {dest}: {e}")
    if failures:
        return False, "Some files failed to undo:\n" + "\n".join(failures)
    # success: remove last run
    try:
        LAST_RUN_PATH.unlink()
    except Exception:
        pass
    return True, f"Undid {len(moves)} moves."


def append_log(message: str):
    logger.info(message)
