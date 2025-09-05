# test\test_v2.py

import os  # noqa: F401
import shutil
import tempfile
from pathlib import Path
import pytest

from file_organizer.v2 import organizer


@pytest.fixture
def temp_dir():
    d = Path(tempfile.mkdtemp())
    yield d
    shutil.rmtree(d)


def test_unique_dest(temp_dir):
    f = temp_dir / "file.txt"
    f.write_text("a")
    f2 = organizer._unique_dest(f)
    assert f2 != f
    assert "_1" in f2.name or "_1" in f2.stem


def test_categorize_file_images(temp_dir):
    f = temp_dir / "photo.jpg"
    f.write_text("x")
    cfg = organizer.DEFAULT_CONFIG
    cat, _ = organizer.categorize_file(f, cfg)
    assert cat == "Images"


def test_build_preview_and_move(temp_dir):
    f1 = temp_dir / "doc.txt"
    f1.write_text("App works")
    cfg = organizer.DEFAULT_CONFIG
    plan = organizer.build_preview([temp_dir], cfg)
    assert any("Documents" in p["category"] for p in plan)
    moved = organizer.perform_moves(plan)
    assert moved
    assert not f1.exists()
    assert Path(moved[0]["dest"]).exists()


def test_undo_last_run(temp_dir):
    f1 = temp_dir / "test.txt"
    f1.write_text("hello")
    cfg = organizer.DEFAULT_CONFIG
    cfg["categories"]["Documents"]["extensions"].append(".txt")
    plan = organizer.build_preview([temp_dir], cfg)
    moved = organizer.perform_moves(plan)
    assert moved
    ok, _ = organizer.undo_last_run()
    assert ok
    assert f1.exists()
