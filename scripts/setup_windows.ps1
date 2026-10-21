# Sets up Talker on Windows: virtual environment, PyTorch, Talker, models.
# Run from the project folder in PowerShell:
#   powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1          # auto-detect GPU
#   powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1 -Cpu     # force CPU
param([switch]$Cpu)
$ErrorActionPreference = "Stop"

# Chatterbox needs PyTorch 2.6, which has wheels for Python 3.10 to 3.12.
$py = $null
foreach ($v in "3.11", "3.12", "3.10") {
    & py "-$v" --version 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) { $py = $v; break }
}
if (-not $py) { throw "Install Python 3.11 from python.org (tick 'Add python.exe to PATH'), then rerun." }
Write-Host "Using Python $py"

if (-not (Test-Path .venv)) { & py "-$py" -m venv .venv }
$pip = ".venv\Scripts\python.exe -m pip"
Invoke-Expression "$pip install --upgrade pip"

$gpu = $false
if (-not $Cpu) {
    try { nvidia-smi | Out-Null; $gpu = ($LASTEXITCODE -eq 0) } catch { $gpu = $false }
}
if ($gpu) {
    Write-Host "NVIDIA GPU found: installing CUDA PyTorch"
    Invoke-Expression "$pip install torch==2.6.0 torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/cu124"
} else {
    Write-Host "No NVIDIA GPU: installing CPU PyTorch (Chatterbox will be slow; Kokoro is fine)"
    Invoke-Expression "$pip install torch==2.6.0 torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/cpu"
}

Invoke-Expression "$pip install -e .[all]"
& .venv\Scripts\talker.exe download

Write-Host ""
Write-Host "Done. Start the app with:  .venv\Scripts\talker-gui.exe"
Write-Host "Or use the CLI:            .venv\Scripts\talker.exe say `"Hello!`" --mood happy"
