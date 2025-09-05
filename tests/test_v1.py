import tempfile
from pathlib import Path
import json
import importlib
import file_organizer

# lazy-load v1
v1 = file_organizer.load_v1()
organizer = importlib.import_module("file_organizer.v1.organizer")

CONFIG_PATH = Path(__file__).resolve().parents[1] / "organizer_config.json"


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def expected_category_for(ext: str) -> str:
    cfg = load_config()
    for cat, info in cfg["categories"].items():
        if ext.lower() in [e.lower() for e in info.get("extensions", [])]:
            return cat
    return "Others"


def test_file_organization_v1():
    """Check that file gets moved into the correct category."""
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir)
        file_path = p / "test.txt"
        file_path.write_text("hello")

        # Build preview and perform moves
        cfg = load_config()
        plan = organizer.build_preview([p], cfg)
        performed = organizer.perform_moves(plan)

        # Check that our test file was moved
        assert any("test.txt" in str(m["dest"]) for m in performed), \
            f"test.txt not moved, performed={performed}"

        # Determine expected folder
        cat = expected_category_for(".txt")
        expected_path = p / cat / "test.txt"
        assert expected_path.exists(), f"{expected_path} not found"


def test_undo_last_run_v1():
    """Check that undo restores the file back to its original place."""
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir)
        file_path = p / "test.txt"
        file_path.write_text("hello")

        cfg = load_config()
        plan = organizer.build_preview([p], cfg)
        organizer.perform_moves(plan)

        cat = expected_category_for(".txt")
        moved_path = p / cat / "test.txt"
        assert moved_path.exists(), "File was not moved before undo."

        # Now undo last run
        restored, msg = organizer.undo_last_run()
        assert restored, f"Undo failed: {msg}"

        # File should be back at original path
        assert file_path.exists(), "File not restored to original location."
        assert not moved_path.exists(), "Moved copy still exists after undo."
