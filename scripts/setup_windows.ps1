# Sets up Talker on Windows: Python, virtual environment, PyTorch, Talker, models.
# Run from the project folder in PowerShell:
#   powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1          # auto-detect GPU
#   powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1 -Cpu     # force CPU
param([switch]$Cpu)

# Native tools (py, pip) write notices to stderr. With "Stop", Windows PowerShell
# turns those into errors, so check exit codes instead.
$ErrorActionPreference = "Continue"

function Run([string]$exe, [string[]]$arguments) {
    & $exe @arguments
    if ($LASTEXITCODE -ne 0) { Write-Error "Failed: $exe $($arguments -join ' ')"; exit 1 }
}

# Chatterbox needs PyTorch 2.6, which has wheels for Python 3.10 to 3.12.
function Find-Python {
    foreach ($v in "3.11", "3.12", "3.10") {
        $exe = & py "-V:$v" -c "import sys; print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0 -and $exe) { return $exe.Trim() }
        $exe = & py "-$v" -c "import sys; print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0 -and $exe) { return $exe.Trim() }
    }
    return $null
}

$python = $null
if (Get-Command py -ErrorAction SilentlyContinue) { $python = Find-Python }
if (-not $python) {
    Write-Host "Python 3.11 not found. Installing it..."
    if (Get-Command py -ErrorAction SilentlyContinue) {
        & py install 3.11 2>$null   # Python install manager (python.org, 2025+)
    }
    if (-not (Get-Command py -ErrorAction SilentlyContinue) -or -not (Find-Python)) {
        if (Get-Command winget -ErrorAction SilentlyContinue) {
            & winget install --id Python.Python.3.11 -e --accept-package-agreements --accept-source-agreements
        }
    }
    if (Get-Command py -ErrorAction SilentlyContinue) { $python = Find-Python }
    if (-not $python) {
        $candidate = Join-Path $env:LOCALAPPDATA "Programs\Python\Python311\python.exe"
        if (Test-Path $candidate) { $python = $candidate }
    }
    if (-not $python) {
        Write-Error "Could not install Python 3.11. Install it from https://www.python.org/downloads/release/python-3119/ and rerun."
        exit 1
    }
}
Write-Host "Using $python"

if (-not (Test-Path .venv)) { Run $python @("-m", "venv", ".venv") }
$venvPy = ".venv\Scripts\python.exe"
Run $venvPy @("-m", "pip", "install", "--upgrade", "pip")

$gpu = $false
if (-not $Cpu -and (Get-Command nvidia-smi -ErrorAction SilentlyContinue)) {
    & nvidia-smi *> $null
    $gpu = ($LASTEXITCODE -eq 0)
}
$torchIndex = if ($gpu) { "https://download.pytorch.org/whl/cu124" } else { "https://download.pytorch.org/whl/cpu" }
if ($gpu) { Write-Host "NVIDIA GPU found: installing CUDA PyTorch" }
else { Write-Host "No NVIDIA GPU: installing CPU PyTorch (Chatterbox will be slow; Kokoro is fine)" }
Run $venvPy @("-m", "pip", "install", "torch==2.6.0", "torchaudio==2.6.0", "--index-url", $torchIndex)

Run $venvPy @("-m", "pip", "install", "-e", ".[all]")
Run ".venv\Scripts\talker.exe" @("download")

Write-Host ""
Write-Host "Done. Start the app with:  .venv\Scripts\talker-gui.exe"
Write-Host "Or use the CLI:            .venv\Scripts\talker.exe say `"Hello!`" --mood happy"
