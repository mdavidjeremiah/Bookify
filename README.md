# readaloud 📖🔊

> **Offline voice-controlled document reader CLI** — reads your PDFs, DOCX, PPTX, EPUB and more aloud, with keyboard and voice control, fully offline.

## Features

- 📄 **Multi-format support**: `.txt`, `.md`, `.pdf`, `.docx`, `.odt`, `.pptx`, `.epub`, `.rtf`
- 🔊 **Offline TTS**: Uses `pyttsx3` (eSpeak on Linux, SAPI5 on Windows, NSSpeech on macOS)
- ⌨️ **Full keyboard control**: pause, speed, navigate sentences/pages
- 🎙️ **Voice commands** *(optional)*: powered by Vosk — fully offline
- 💾 **Resume where you left off**: position saved automatically per-book
- 🚀 **One command to start**: `readaloud mybook.pdf`
- 🔒 **100% private**: no network calls during reading, no accounts

---

## Quick Start

### 1. Install

```bash
pip install readaloud
```

For faster PDF rendering (recommended):
```bash
pip install readaloud[pdf-fast]
```

For voice command support:
```bash
pip install readaloud[voice]
readaloud --setup   # downloads ~50 MB Vosk model (one-time)
```

Everything at once:
```bash
pip install readaloud[all]
readaloud --setup
```

### 2. Read a file

```bash
readaloud mybook.pdf
readaloud lecture.pptx --speed 1.3
readaloud novel.epub --page 42
```

### 3. File picker (no argument needed)

```bash
readaloud          # lists supported files in current directory
```

---

## Keyboard Controls

| Key | Action |
|-----|--------|
| `Space` | Pause / Resume |
| `+` / `-` | Speed up / slow down |
| `→` / `←` | Next / previous sentence |
| `n` / `p` | Next / previous page |
| `r` | Repeat current sentence |
| `g` | Go to page (prompts for number) |
| `v` | Toggle voice control on/off |
| `q` | Save position and quit |

---

## Voice Commands

Say **"reader"** followed by a command (or use `--push-to-talk`):

| Say | Action |
|-----|--------|
| "reader pause" | Pause |
| "reader resume" / "reader continue" | Resume |
| "reader faster" / "reader speed up" | Increase speed |
| "reader slower" / "reader slow down" | Decrease speed |
| "reader normal speed" | Reset to 1.0× |
| "reader next" / "reader skip" | Next sentence |
| "reader back" / "reader previous" | Previous sentence |
| "reader repeat" | Repeat sentence |
| "reader next page" | Next page |
| "reader previous page" | Previous page |
| "reader go to page 42" | Jump to page 42 |
| "reader quit" / "reader exit" | Save and exit |

Voice control requires the optional `[voice]` extra and model setup (`readaloud --setup`).

---

## CLI Reference

```
readaloud [FILE] [OPTIONS]

Arguments:
  FILE                    Path to document (optional; shows file picker if omitted)

Options:
  --speed FLOAT           Initial speed multiplier, e.g. 1.5 (default: 1.0)
  --page INT              Start at this page number (1-based)
  --voice NAME            TTS voice ID
  --list-voices           List available TTS voices and exit
  --no-voice              Disable voice commands
  --push-to-talk          Use a key instead of the "reader" wake word
  --mic INDEX             Microphone device index
  --resume                Resume from saved position without prompting
  --sleep DURATION        Auto-stop after duration (e.g. 30m, 1h, 90s)
  --setup                 Download/verify offline Vosk model
  --version               Show version
  -h, --help              Show help
```

---

## Supported Formats

| Format | Extension | Library | Notes |
|--------|-----------|---------|-------|
| Plain text | `.txt`, `.md` | built-in | |
| PDF | `.pdf` | PyMuPDF *(fast)* or pypdf | Scanned PDFs not supported (v1) |
| Word | `.docx` | python-docx | |
| OpenDocument | `.odt` | odfpy | |
| PowerPoint | `.pptx` | python-pptx | Per-slide pages |
| EPUB | `.epub` | ebooklib + bs4 | Per-chapter pages |
| Rich Text | `.rtf` | striprtf | |
| Legacy `.doc`/`.ppt` | `.doc`, `.ppt` | LibreOffice *(optional)* | Requires `soffice` installed |

---

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│  Document   │     │   Player     │     │   TTS Engine    │
│  Loaders   │────▶│  (state +    │────▶│  (pyttsx3 /     │
│  (per fmt) │     │   queue)     │     │   Piper future) │
└─────────────┘     └──────┬───────┘     └─────────────────┘
                           │ Command Queue
              ┌────────────┴────────────┐
              │                         │
     ┌────────▼──────┐        ┌─────────▼──────┐
     │   Keyboard    │        │  Voice Handler  │
     │   Handler     │        │  (Vosk STT)     │
     └───────────────┘        └─────────────────┘
```

Four decoupled components communicate through a thread-safe command queue. Keyboard and voice emit identical `Command` objects — adding new input methods later is trivial.

---

## Data & Privacy

- **No network calls** during reading. Only `--setup` downloads a model.
- Reading positions saved to: `~/.local/share/readaloud/positions.json` (Linux) or platform equivalent.
- Config saved to: `~/.config/readaloud/config.json`.
- No audio or document text is ever stored or transmitted.

---

## Development

```bash
git clone https://github.com/user/readaloud
cd readaloud
pip install -e ".[dev,all]"

# Run tests
pytest

# Lint
ruff check readaloud/
black --check readaloud/
```

---

## Roadmap

| Version | Scope |
|---------|-------|
| **v0.1** | Core loaders, pyttsx3 TTS, keyboard + voice control, persistence, Rich UI |
| **v0.2** | Piper voices (higher quality), bookmarks, chapter detection |
| **v1.0** | OCR for scanned PDFs (Tesseract), audio export, more languages |

---

## License

MIT © 2026 readaloud contributors
