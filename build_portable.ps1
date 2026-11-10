# Seforim Studio - build a PORTABLE Windows program (SeforimStudio.exe) to copy to an offline computer.
# Run on ANY Windows 10/11 PC that has internet (Python does NOT need to be installed).
# Started by double-clicking  BUILD_PORTABLE_EXE.bat
$ErrorActionPreference = "Stop"
trap { Write-Host ""; Write-Host "PROBLEM: $_" -ForegroundColor Red; Write-Host "Check the internet connection and run BUILD_PORTABLE_EXE.bat again (it continues where it stopped)."; exit 1 }
$ProgressPreference = "SilentlyContinue"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$Root   = Split-Path -Parent $MyInvocation.MyCommand.Path
$Work   = Join-Path $Root "_build"
$PyDir  = Join-Path $Work "python"
$Out    = Join-Path $Root "SeforimStudio-Portable"
$PyUrl  = "https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe"
$TessUrl = "https://github.com/UB-Mannheim/tesseract/releases/download/v5.4.0.20240606/tesseract-ocr-w64-setup-5.4.0.20240606.exe"
$HebUrl = "https://github.com/tesseract-ocr/tessdata_best/raw/main/heb.traineddata"

function Step($t) { Write-Host ""; Write-Host "=== $t ===" -ForegroundColor Cyan }
New-Item -ItemType Directory -Force -Path $Work | Out-Null

# 1. A private copy of Python, only for building (does not touch the computer's settings)
if (-not (Test-Path "$PyDir\python.exe")) {
    Step "1/5  Downloading Python 3.12 (for building only, ~27 MB)"
    $pyExe = Join-Path $Work "python-setup.exe"
    Invoke-WebRequest $PyUrl -OutFile $pyExe
    Step "     Installing it privately into _build\python"
    $p = Start-Process $pyExe -Wait -PassThru -ArgumentList @("/quiet", "InstallAllUsers=0", "TargetDir=$PyDir", "Include_launcher=0",
        "Include_test=0", "Include_doc=0", "Include_tcltk=1", "PrependPath=0", "Shortcuts=0", "AssociateFiles=0", "Include_pip=1")
}
$Py = "$PyDir\python.exe"
if (-not (Test-Path $Py)) {
    # The private install can be skipped by Windows when the same Python version is already installed - use that one.
    $found = $null
    foreach ($c in @(@("py", "-3.12"), @("py", "-3.13"), @("py", "-3.11"), @("python"))) {
        $exe = $c[0]; $extra = @($c | Select-Object -Skip 1)
        try { $v = & $exe @extra -c "import sys;print(sys.executable)" 2>$null; if ($LASTEXITCODE -eq 0 -and $v) { $found = "$v".Trim(); break } } catch {}
    }
    if (-not $found) { throw "Python could not be installed. Install Python 3.12 from python.org, then run this again." }
    Write-Host "     Using the Python already on this computer: $found"
    $Py = $found
}

# 2. Packages
Step "2/5  Installing packages (OpenCV, Word, PDF, calendar, PyInstaller)"
& $Py -m pip install --upgrade pip --quiet
& $Py -m pip install -r (Join-Path $Root "requirements.txt") --quiet
if ($LASTEXITCODE -ne 0) { throw "Package install failed." }

# 3. Build the .exe
Step "3/5  Building SeforimStudio.exe (takes a few minutes)"
Push-Location $Root
# the offline dictionary + word-by-word Tanach (Translate screen, interlinear)
if (-not (Test-Path "langdata\lang.sqlite")) { & $Py tools\build_langdata.py --out langdata\lang.sqlite --cache "$Work\langcache"; if ($LASTEXITCODE -ne 0) { Write-Host "(dictionary build failed - continuing without it)" } }
& $Py -m PyInstaller SeforimStudio.spec --noconfirm --clean --workpath "$Work\pyi" --distpath "$Work\dist"
if ($LASTEXITCODE -ne 0) { Pop-Location; throw "PyInstaller failed." }
Pop-Location
if (Test-Path $Out) {
    # keep an existing library/notes when rebuilding
    if (Test-Path "$Out\data") { Move-Item "$Out\data" "$Work\data_keep" -Force }
    Remove-Item $Out -Recurse -Force
}
Move-Item "$Work\dist\SeforimStudio" $Out
if (Test-Path "$Work\data_keep") { Move-Item "$Work\data_keep" "$Out\data" -Force }

# 4. Tesseract + Hebrew inside the portable folder (handwriting/print engine C works offline out of the box)
Step "4/5  Adding Tesseract OCR with Hebrew"
try {
    $tsExe = Join-Path $Work "tesseract-setup.exe"
    if (-not (Test-Path $tsExe)) { Invoke-WebRequest $TessUrl -OutFile $tsExe }
    $tsDir = Join-Path $Out "tesseract"
    $7z = @("$env:ProgramFiles\7-Zip\7z.exe", "${env:ProgramFiles(x86)}\7-Zip\7z.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
    if ($7z) {
        # unpack the installer directly (no install, no admin rights needed)
        & $7z x $tsExe "-o$tsDir" -y | Out-Null
        Remove-Item "$tsDir\`$PLUGINSDIR" -Recurse -Force -ErrorAction SilentlyContinue
        Remove-Item "$tsDir\tesseract-uninstall.exe" -Force -ErrorAction SilentlyContinue
    }
    if (-not (Test-Path "$tsDir\tesseract.exe")) {
        Write-Host "     (Windows may ask permission - click Yes)"
        Start-Process $tsExe -Wait -ArgumentList "/S /D=$tsDir"   # NSIS: /D must be last and unquoted
        Start-Sleep -Seconds 5
    }
    if (-not (Test-Path "$tsDir\tesseract.exe")) { throw "not installed" }
    New-Item -ItemType Directory -Force -Path "$tsDir\tessdata" | Out-Null
    Invoke-WebRequest $HebUrl -OutFile "$tsDir\tessdata\heb.traineddata"
    Invoke-WebRequest "https://github.com/tesseract-ocr/tessdata_fast/raw/main/eng.traineddata" -OutFile "$tsDir\tessdata\eng.traineddata"
    # the cursive handwriting (ktav) reader trained for Seforim Studio
    Get-ChildItem "scanner\models\*.traineddata" -ErrorAction SilentlyContinue | Copy-Item -Destination "$tsDir\tessdata\"
    $langs = & "$tsDir\tesseract.exe" --list-langs 2>&1
    Write-Host "     Tesseract + Hebrew added. Languages: $($langs -join ' ')" -ForegroundColor Green
} catch {
    Write-Host "     Could not add Tesseract automatically ($_). The app still works; install Tesseract later (see README)." -ForegroundColor Yellow
}

# 4b. Pre-download Hebrew titles and the Hebrew font pack into the portable folder
Step "4b   Adding exact Hebrew titles (6,600 seforim) and 50+ Hebrew fonts"
New-Item -ItemType Directory -Force -Path "$Out\data\fonts" | Out-Null
Copy-Item (Join-Path $Root "data\seforim_catalog.db") "$Out\data\seforim_catalog.db" -Force
try {
    & $Py (Join-Path $Root "tools\prebuild_library.py") --out "$Out\data\library.sqlite" --titles-only --workers 16
    if ($LASTEXITCODE -ne 0) { throw "titles failed" }
    Remove-Item "$Out\data\library_report.txt" -Force -ErrorAction SilentlyContinue
} catch { Write-Host "     Could not add Hebrew titles now ($_). They can be downloaded later in Settings." -ForegroundColor Yellow }
try {
    $fontsDir = "$Out\data\fonts"
    & $Py -c "import sys; sys.path.insert(0, r'$Root'); from core.fonts import download_font_pack; r = download_font_pack(r'$fontsDir'); print('fonts:', len(r['downloaded']), 'failed:', r['failed'])"
} catch { Write-Host "     Could not add fonts now ($_). They can be downloaded later in Settings." -ForegroundColor Yellow }

# 5. Extras
Step "5/5  Finishing"
Copy-Item (Join-Path $Root "README.md") $Out -Force
New-Item -ItemType Directory -Force -Path "$Out\data\models" | Out-Null
@"
SEFORIM STUDIO - PORTABLE
=========================
Double-click SeforimStudio.exe.  Nothing to install.  Works with no internet.

Already included: Hebrew titles of all seforim, 50+ Hebrew fonts, Tesseract Hebrew reader for the scanner.

THE TEXTS (the full library of all seforim, Hebrew + English, with all cross-references):
  Download the file(s) named  SeforimLibrary.sqlite.xz.part1of?, part2of?...  from the same download page,
  put them in THIS folder (next to SeforimStudio.exe), and start SeforimStudio.exe.
  It installs the library once (a few minutes) and then you can delete those downloaded part files.

Then copy this WHOLE folder (SeforimStudio-Portable) to a USB stick / external drive and onto the offline computer.
Everything is inside the "data" folder and travels with it.

Optional AI handwriting reader (engine A): install Ollama on the offline computer (copy the installer on the USB),
and copy the model folder %USERPROFILE%\.ollama\models from a computer where you ran:  ollama pull qwen3-vl:8b
"@ | Set-Content -Encoding UTF8 "$Out\START HERE.txt"

Step "Making SeforimStudio-Portable.zip"
$zip = Join-Path $Root "SeforimStudio-Portable.zip"
if (Test-Path $zip) { Remove-Item $zip -Force }
try { Compress-Archive -Path $Out -DestinationPath $zip -CompressionLevel Optimal }
catch { Write-Host "     (Skipped the .zip - the folder is too big to zip. Just copy the folder itself.)" -ForegroundColor Yellow; $zip = "(not made)" }

# 6. One-click installer (SeforimStudio-Setup.exe) - avoids running the exe from inside the zip
Step "Making SeforimStudio-Setup.exe"
try {
    if (-not (Test-Path $zip)) { throw "zip missing" }
    & $Py -m PyInstaller --noconfirm --onefile --windowed --name "SeforimStudio-Setup" --icon (Join-Path $Root "web\icon.ico") `
        --add-data "$zip;." --add-data "$(Join-Path $Root 'web\icon.ico');." `
        --distpath "$Work\setupdist" --workpath "$Work\setupbuild" --specpath "$Work" (Join-Path $Root "tools\setup_app.py")
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }
    Copy-Item "$Work\setupdist\SeforimStudio-Setup.exe" (Join-Path $Root "SeforimStudio-Setup.exe") -Force
    Write-Host "     Setup: $(Join-Path $Root 'SeforimStudio-Setup.exe')" -ForegroundColor Green
} catch { Write-Host "     Could not make the Setup program ($_). The zip still works (unzip it first)." -ForegroundColor Yellow }

Write-Host ""
Write-Host "DONE!" -ForegroundColor Green
Write-Host "Portable program:  $Out\SeforimStudio.exe"
Write-Host "Same thing zipped: $zip"
Write-Host "Read 'START HERE.txt' - download the library on this computer first, then copy the folder to the offline computer."
