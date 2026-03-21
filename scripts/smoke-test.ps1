$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $repoRoot ".venv\\Scripts\\python.exe"

if (-not (Test-Path $python)) {
  throw "Virtual environment not found. Run scripts/bootstrap.ps1 first."
}

Push-Location $repoRoot
try {
  & $python -m skill.skill_runner health_check
  & $python -m skill.skill_runner show_config
  & $python -m skill.skill_runner validate_env
  & $python -m skill.skill_runner simulate_cycle
  & $python -m skill.skill_runner dry_run_place_preview
}
finally {
  Pop-Location
}
