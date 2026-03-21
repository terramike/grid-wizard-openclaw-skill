$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$tmpDir = Join-Path $repoRoot ".tmp"
$venvDir = Join-Path $repoRoot ".venv"

New-Item -ItemType Directory -Force $tmpDir | Out-Null

# Python bootstrap on this machine cannot reliably use the profile temp dir,
# so pin temp files into the repo while building the virtual environment.
$env:TEMP = $tmpDir
$env:TMP = $tmpDir

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
  throw "python was not found on PATH"
}

if (-not (Test-Path $venvDir)) {
  python -m venv $venvDir
  if ($LASTEXITCODE -ne 0) {
    throw "python -m venv failed while creating .venv"
  }
}

& (Join-Path $venvDir "Scripts\\python.exe") -m pip install -r (Join-Path $repoRoot "requirements.txt")
if ($LASTEXITCODE -ne 0) {
  throw "pip install failed. On this machine, Python temp-directory ACLs may need repair before bootstrap can complete."
}
