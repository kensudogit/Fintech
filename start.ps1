# Fintech AI Platform local launcher
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

Write-Host "==> Starting PostgreSQL (Docker)..."
docker compose up -d postgres

Write-Host "==> Starting FastAPI on http://127.0.0.1:8080"
Start-Process -WorkingDirectory "$Root\backend" -FilePath "$Root\backend\.venv\Scripts\uvicorn.exe" -ArgumentList "app.main:app","--reload","--host","127.0.0.1","--port","8080"

Start-Sleep -Seconds 2
Write-Host "==> Starting Streamlit on http://127.0.0.1:8501"
Start-Process -WorkingDirectory "$Root\streamlit_app" -FilePath "$Root\backend\.venv\Scripts\streamlit.exe" -ArgumentList "run","app.py","--server.port","8501"

Write-Host "==> Starting Next.js on http://127.0.0.1:3000"
Start-Process -WorkingDirectory "$Root\frontend" -FilePath "npm" -ArgumentList "run","dev"

Write-Host ""
Write-Host "Ready:"
Write-Host "  API docs : http://127.0.0.1:8080/docs"
Write-Host "  Frontend : http://127.0.0.1:3000"
Write-Host "  Streamlit: http://127.0.0.1:8501"
Write-Host "  Postgres : localhost:15432 (fintech / fintech_secret / fintech_ai)"
