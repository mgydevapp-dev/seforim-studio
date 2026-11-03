# Seforim Studio — offline Hebrew seforim library, search, gematria, notes, covers & handwriting scanner

Everything runs **on your own computer**. Internet is used only once, during setup (to install the programs and
download the texts). After that you can unplug the internet and everything keeps working.

Buttons and menus are in English (you can switch the menus to עברית or Français at the top); the texts are Hebrew with English side by side.

---

## 1. One-time setup (Windows)

1. **Install Python 3.11–3.13** from https://www.python.org/downloads/ — on the first screen tick **"Add python.exe to PATH"**.
2. Unzip the Seforim Studio folder somewhere you own, e.g. `Documents\SeforimStudio` (not inside *Program Files*).
3. Double-click **`install_windows.bat`**. It installs the few Python packages the app needs.
4. Double-click **`run_windows.bat`**. Seforim Studio opens in its own window.
5. In the app go to **⚙ Settings → Library & download**:
   * Tick the sections you want (start with Tanakh, Mishnah, Talmud) and press **Download & build library**.
   * Press **Get exact Hebrew titles for all seforim** (≈116 MB once) so every sefer shows its exact Hebrew name, author and date.
     (Even before this, ~83% of the 6,468 titles already show Hebrew names from the built-in dictionary.)
   * Optional: tick **Cross-references** to get commentary links (Rashi beside the pasuk, etc. — a large download).
6. **⚙ Settings → Fonts → Download the free Hebrew font pack** (50+ Hebrew fonts, once).
7. Optional: set your city in **⚙ Settings → Appearance & location** for zmanim.

That's it — from now on no internet is needed.

**Portable program for an OFFLINE computer (no install at all):** on any Windows PC that has internet, double-click
**`BUILD_PORTABLE_EXE.bat`**. It downloads a private copy of Python (nothing is installed on that PC permanently), builds
**SeforimStudio.exe**, adds Tesseract with Hebrew, and makes the folder **`SeforimStudio-Portable`** (+ a .zip).
Open the .exe there once to download the library, Hebrew titles and fonts, close it, then copy the whole folder to a USB
stick and onto the offline computer — double-click SeforimStudio.exe. Instructions are also in `START HERE.txt` inside it.

**Make a double-click program (.exe) when Python is already installed** — Step 4: double-click **`build_windows.bat`**. When it finishes, copy the folder
`dist\SeforimStudio` wherever you like and double-click **SeforimStudio.exe**. Your library and notes live in the `data`
folder next to the .exe — back it up or copy it to another computer.

**Mac / Linux:** run `./install_mac_linux.sh` once, then `./run_mac_linux.sh`.

The app window uses Microsoft Edge (built into every Windows computer) or Chrome in "app mode" — it just displays the
program; nothing is sent anywhere. The engine listens only on your own computer (127.0.0.1).

---

## 2. Handwriting engines for the Notes Scanner (one-time, optional)

The scanner always cleans your photos (Step 1). To turn handwriting into text, install **at least one** engine.
The app automatically uses the best one installed: **A → B → C**. The scanner screen shows which are ready.

### A) Local AI vision model via Ollama — best for messy handwriting and cursive
1. Install Ollama from https://ollama.com (Windows installer).
2. Open *Command Prompt* and run **one** of these (one-time download):

| Command | Download | Computer needed | Notes |
|---|---|---|---|
| `ollama pull qwen3-vl:8b` | 6.1 GB | GPU with 8 GB+ memory **or** 16 GB RAM (CPU is slow: 1–5 min per page) | **Recommended** |
| `ollama pull qwen3-vl:4b` | 3.3 GB | 8 GB RAM | For weaker computers; less accurate |
| `ollama pull qwen3-vl:30b` | 20 GB | 24 GB+ GPU memory or 32 GB+ RAM | Most accurate, slow without a big GPU |

Qwen3-VL (from Alibaba) reads 32 languages including Hebrew and handles tilted, blurry and badly-lit photos better than
older models. If you have several vision models, choose one in the scanner screen. The app tells the model to copy the
Hebrew exactly, line by line, without translating, correcting or adding words, and writes `[???]` for unreadable words.
Tall pages are read in overlapping parts (choose *Parts* in the scanner if lines get skipped).

### B) Kraken — good for one person's consistent handwriting, and trainable
* Kraken officially supports **Mac and Linux**. On Windows use **WSL** (Windows Subsystem for Linux): `wsl --install`,
  then inside WSL: `pip install kraken`.
* You need a Hebrew recognition model (`.mlmodel`). Run `kraken list` and look for Hebrew models, download one with
  `kraken get <ID>`, and copy the `.mlmodel` file into `data\models\`. (Ready-made Hebrew models are mostly trained on
  manuscripts, so for modern handwriting you will get much better results after training — below.)

**Teach Kraken one person's handwriting (fine-tuning):**
1. Scan pages of that person's notes and read them with any engine.
2. Correct the text so that **each handwritten line is one line** in the text box.
3. Press **🎓 Save as training sample** and type the person's name. The app cuts the page into line images and saves
   pairs `xxx.png` + `xxx.gt.txt` in `data\training\<name>\`.
4. Collect **300+ lines** (1,000+ is better). Then (in WSL/Mac/Linux, inside that folder):
   ```
   ketos train -f path -i hebrew_base.mlmodel --resize union -o my_writer *.png
   ```
   (`-i` starts from an existing Hebrew model — much faster and better than from scratch; `--resize union` adds any new letters.)
5. Copy the best result (e.g. `my_writer_best.mlmodel`) into `data\models\`. Remove other models from that folder so the
   app uses yours. Accuracy typically keeps rising as you add more corrected lines.

### C) Tesseract with Hebrew — fast fallback for neat block letters and print
* Windows: install from https://github.com/UB-Mannheim/tesseract/wiki — on the components screen open
  *Additional language data* and tick **Hebrew**. Keep the default folder (`C:\Program Files\Tesseract-OCR`).
* Mac: `brew install tesseract tesseract-lang` · Linux: `sudo apt install tesseract-ocr tesseract-ocr-heb`.

### Which engine reads *your* handwriting best? (Step 5)
```
py tests\compare_engines.py my_page.jpg
py tests\compare_engines.py my_page.jpg --truth my_page.txt     (with the correct text → accuracy score)
```
It cleans the image, runs every installed engine, prints each result and (with `--truth`) the percentage of wrong
characters (CER) and correct words.

### Honest accuracy expectations
These are typical ranges, not promises — results vary a lot with handwriting, pen vs pencil, and photo quality.

| | Printed text | Neat block letters | Everyday Hebrew cursive (כתב יד) | Messy/fast cursive |
|---|---|---|---|---|
| **C Tesseract** | 95–99% | 50–80% | under 30% — not usable | unusable |
| **A Qwen3-VL 8B** | 95%+ | 80–95% | 60–90% | 40–75% |
| **B Kraken, fine-tuned on that writer (500+ lines)** | — | 90–98% | 85–95% | 70–90% |

* Cursive is much harder than block letters for every engine. AI models can occasionally **"smooth over" a word with a
  similar real word** — always proof-read; that is why the text box is editable.
* Tips that help most: daylight or a lamp from the side, the whole page in frame, phone held flat above the page, pen rather
  than pencil, one page per photo.

---

## 3. Using the app (all offline)

| Section | What it does |
|---|---|
| 🏠 **Home** | Hebrew & English date, parasha, Daf Yomi, zmanim, upcoming yamim tovim with their texts, reading goals, recent books |
| 📚 **Library** | The whole catalog sorted traditionally (Tanakh → Mishnah → Talmud → …) with **English and Hebrew names**. Grey = not downloaded yet (click once to get it). Tabs for several books, Hebrew \| English / stacked / Hebrew-only / **Daf layout**, nikud on/off, commentary pane that follows your scrolling, notes, 4 highlight colours, bookmarks in folders, tags, your own links between sources, export a chapter or whole sefer (Word, PDF, HTML, text, Markdown, EPUB, JSON, CSV, TEI-XML, SQLite), print |
| 🔎 **Search** | Type Hebrew or English — Hebrew finds the Hebrew, English finds the translation, both shown side by side. Phrases `"…"`, `OR`, `-word`, wildcards `*` `?`, `NEAR/5`, `root:שמר`, prefixes (ו ה ב כ ל מ ש), malei/chaser, typo-tolerant, abbreviations, regex, scope by category/book/author/era, include your notes, compare two groups of books, Hebrew equivalents of an English word, history, export results |
| 🔢 **Gematria** | 17 methods (standard, gadol, katan, ordinal, kolel, atbash, albam, milui, ne'elam, kidmi, …). Type letters or a number → every word in the library with that value, every passage containing them, and multi-word phrases with that value |
| 🔤 **Roshei Teivos** | Every place consecutive words start (or end) with your letters, plus the abbreviations dictionary; also ELS (dilugim) |
| ✍️ **Notes** | Full Hebrew word processor: 50+ Hebrew fonts, sizes, colours, headings for חלק/סימן/סעיף/ס״ק with an outline, nikud & ta'amim (Alt+1… or palette), on-screen Hebrew keyboard, automatic ״ ׳ and final letters, abbreviation suggestions (type רמב״ם → Tab), footnotes in two lanes (sources / notes), insert a source from the library with its citation, `[???]` placeholders, source/commentary style macros (Ctrl+1 / Ctrl+2), bracket colouring, find & replace ignoring nikud, transcription desk (scan beside the page with linked scrolling), autosave, import Word/PDF/text/HTML/EPUB, export Word (right-to-left)/PDF/HTML/text/Markdown/EPUB/TEI |
| 🗂 **My Library** | All your documents (folders, tags, 🔒 private with PIN), notes on passages, bookmarks, tags & highlights, **your own seforim** (add Word/PDF/text files — instantly searchable), source sheets, covers, links, history; import & export everything |
| 📕 **Covers** | Fill in title, author, etc. → 26 cover designs (leather & gold, marble, Vilna title page, Torah scroll, art deco, laurel wreath, starry night with menorah, Jerusalem stone, geometric star, watercolor, rose arch, royal tablets, olive wood…). Your colours & fonts, emboss, texture, front or full wrap with spine & back; PNG at 300 dpi or print/PDF |
| 📷 **Scanner** | Photos/scans/PDFs of handwritten notes → cleaned (crop, perspective, straighten, shadows, faint pencil, noise, notebook lines) → read with A/B/C → edit → **Save as Word** (right-to-left, one page per image) or .txt. Also pulls typed text straight out of PDF/Word documents (fixes reversed Hebrew from PDFs) |
| 🧰 **Tools** | 130 Hebrew tools: calendar conversions, holidays, molad, yahrzeit, bar/bas mitzvah, Daf Yomi schedule, zmanim, Shabbos times, numbers ↔ Hebrew letters & words, ciphers, keyboard fixing (akuo → שלום), transliteration, text cleanup, halachic measures (amos, kezayis, reviis, mikveh, techum), places, eras… |
| 📊 **Analysis** | Book statistics & letter frequency, word clouds, co-occurrence, spread by category & era, citation network, author timeline, places map, compare passages, reference tree |
| 📅 **Calendar** | Month view with Hebrew dates, holidays, parasha and daf |
| 📡 **Share** | Send documents, sheets, covers, notes, bookmarks or whole seforim to another computer running Seforim Studio — over the same Wi-Fi, a phone hotspot or a cable (**no internet**), with a 6-digit pairing code. Or Bluetooth, or a `.seforim` package file on a USB stick |
| ⚙ **Settings** | Library download, Hebrew titles, fonts, appearance (light/sepia/gray/dark/auto-by-zmanim), location, PIN, family profiles, backup & restore, developer API |

**Keyboard:** `Ctrl+Shift+K` — type Hebrew with an English keyboard (button ⌨ at the top). `Ctrl+Shift+C` — collect the
selected text into the clipboard catcher. `←/→` — next/previous chapter. `Esc` — leave focus mode.

**Copy & paste** works everywhere, inside the app and to other programs (Word, email…). Copying from the library adds the
citation and a Sefaria link automatically (can be turned off in Settings).

---

## 4. Files & privacy
* `data\library.sqlite` — your downloaded library (a normal SQLite file).
* `data\profiles\` — notes, documents, bookmarks, settings (one file per family member).
* `data\exports\` — everything you export. `data\scans\` — cleaned scans. `data\training\` — Kraken training lines.
* Backups: ⚙ Settings → Backup (one .zip of all profiles).
* Sharing only works when you turn on *Allow other computers to send me items*, only with your pairing code, and private
  (🔒) items are never sent.

## 5. Troubleshooting
* **Window doesn't open** → open the address printed in the console (e.g. `http://127.0.0.1:52011/`) in Edge or Chrome.
* **"Ollama is not running"** → start the Ollama app (it sits in the tray), then press *re-check* in the scanner.
* **AI reading is very slow** → use `qwen3-vl:4b`, or a computer with an NVIDIA GPU.
* **Hebrew from a PDF is backwards** → in the scanner choose *Fix reversed Hebrew* and press *Extract document text* again.
* **Kraken on Windows** → use WSL (see section 2B).
* **Fonts look plain** → Settings → Fonts → download the font pack (once).

Texts come from the public Sefaria export; each text keeps its own license (shown on Sefaria).
