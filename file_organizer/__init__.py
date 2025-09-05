# file_organizer\__init__.py

"""
File Organizer Package

Provides two versions of the File Organizer app:
- v1: Basic organizer (main.py + organizer.py)
- v2: Advanced organizer (main.py + organizer.py with more features)

Users can run from CLI via:
    file-organizer-v1
    file-organizer-v2
"""

__version__ = "1.0.0"
__author__ = "Harsh Kesharwani"

def load_v1():
    """Lazy import v1 module (call when you need it)."""
    from importlib import import_module
    return import_module("file_organizer.v1")

def load_v2():
    """Lazy import v2 module (call when you need it)."""
    from importlib import import_module
    return import_module("file_organizer.v2")
