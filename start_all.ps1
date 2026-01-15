$ErrorActionPreference = "Stop"

# Raíz del proyecto (carpeta donde está este .ps1)
$ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path
$UI_DIR = Join-Path $ROOT "UI"

function Start-ServiceWindow([string]$title, [string]$workdir, [string]$command) {
  Start-Process -FilePath "powershell.exe" `
    -WorkingDirectory $workdir `
    -ArgumentList @(
      "-NoExit",
      "-Command",
      "$host.ui.RawUI.WindowTitle='$title'; $command"
    )
}

# --- APIs ---
Start-ServiceWindow "API Carga (8010)"        $ROOT "python -m uvicorn CARGA.api_carga:app --reload --host 127.0.0.1 --port 8010"
Start-ServiceWindow "API Busqueda ITV (8020)" $ROOT "python -m uvicorn BUSQUEDA.api_busqueda_itv:app --reload --host 127.0.0.1 --port 8020"

Start-ServiceWindow "API Busqueda GAL (8030)" $ROOT "python -m uvicorn GAL.api_busqueda_gal:app --reload --host 127.0.0.1 --port 8030"
Start-ServiceWindow "API Busqueda CAT (8040)" $ROOT "python -m uvicorn CAT.api_busqueda_cat:app --reload --host 127.0.0.1 --port 8040"
Start-ServiceWindow "API Busqueda CV (8050)"  $ROOT "python -m uvicorn CV.api_busqueda_cv:app --reload --host 127.0.0.1 --port 8050"

# --- Servidor para las 2 interfaces (carpeta UI) ---
Start-ServiceWindow "UI (5500)" $UI_DIR "python -m http.server 5500 --bind 127.0.0.1"

# --- Abrir interfaces ---
Start-Process "http://127.0.0.1:5500/itv_ui.html"
Start-Process "http://127.0.0.1:5500/carga_ui.html"
