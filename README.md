<!-- README.md -->

# 📦 File Organizer (PyQt5)

Cross-platform **desktop file organizer app** with a modern UI, real-time monitoring, and advanced safety features.  
Organize your downloads, documents, media, code, and installers into structured folders — automatically.  

---

## ✨ Features

- 🚀 **Drag & Drop** folders, or use **Browse**
- 👁 **Preview planned moves** (file → category → destination)
- 🔒 **Safe moves** (duplicate-proof using `_unique_dest`)
- ↩ **Undo Last** (revert previous run from `last_run.json`)
- ⚙️ **Custom rules** (`organizer_config.json` editable)
- 🌙 **Dark mode** (Fusion palette toggle)
- 👀 **Real-time monitoring** with `watchdog`
- 🖥 **System tray icon & background agent**
- 📂 **Per-category destinations** (absolute or relative)
- 📑 **Multi-folder batch mode**
- 📝 **Logging** (saved to `organizer.log` in app data)
- 📦 **Apps & Installers category** (`.exe`, `.msi`, `.dmg`, `.apk`, etc.)
- 🖼️ **Icons category** (`.ico`, `.icns`)
- 📊 **Advanced log viewer**:
  - Timestamped entries
  - Auto-scroll
  - Clear log
  - Export to text file

---

## 📂 Default Folder Structure

When organizing, files are grouped like this:

```bash
    📂 Organized_Files/
    ├── Images/
    ├── Icons/
    ├── Videos/
    ├── Documents/
    │   ├── PDFs/
    │   ├── Word/
    │   ├── Spreadsheets/
    │   ├── Presentations/
    │   └── Text/
    ├── Archives/
    ├── Code/
    ├── Audio/
    ├── Apps/
    │   └── Installers/
    └── Others/
```

---

## ⚡ Install & Run

```bash
# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate    # Linux / macOS
venv\Scripts\activate       # Windows PowerShell

# Install dependencies
pip install -r requirements.txt

# Run version 1 (basic)
file-organizer-v1

# Run version 2 (advanced with preview, undo, monitoring)
file-organizer-v2
```

---

## 🛠 Implementation Notes

- **Safety** → Uses shutil.move with collision-proof renaming. Works across drives.
- **Undo** → last_run.json logs actual moves, and undo restores them in reverse order.
- **Monitoring** → Uses watchdog.PatternMatchingEventHandler inside a QThread.
- **Config Editing** → Config stored in organizer_config.json (or appdirs location). Users can edit JSON directly or via settings UI.
- **Tray Agent** → Closing the app minimizes to tray; monitoring continues in background.
- **Logging** → Moves/errors are logged in organizer.log.
- **Packaging** → Ready for PyInstaller builds via GitHub Actions (Windows/macOS/Linux).

---

## 📦 Packaging & Deployment

- The app is configured for **CI/CD** builds on GitHub Releases:
  - Source → GitHub repo
  - CI → GitHub Actions (release.yml)
  - Output → Prebuilt .zip for Windows, macOS, Linux

- Each bundle includes:
  - Executables (file-organizer-v1, file-organizer-v2)
  - organizer_config.json
  - README.md
  - Sample test/ suite

---

🧪 Testing

Run tests with pytest:

```bash
pip install pytest
pytest test/
```

---

## 🔮 Roadmap (optional enhancements you can request)

- 🖊 Structured Config Editor (GUI with rows, pickers, per-category destinations)
- 📜 Move history viewer with timestamps & multiple undo
- 🔔 Desktop notifications after organization runs
- ⏰ Scheduled runs (cron-like, local scheduler)
- 🌍 Portable version with auto-updater
- 📦 Packaging scripts for Windows (.exe) and macOS (.app)
