# 启动 PyNuxt-Social 后端和前端

Write-Host "Starting PyNuxt-Social..." -ForegroundColor Green

# 启动后端（端口 8012）
Start-Process python -ArgumentList "-m", "uvicorn", "main:app", "--port", "8012", "--reload" -WorkingDirectory ".\backend" -NoNewWindow

# 启动前端（端口 3000）
Start-Process python -ArgumentList "-m", "uvicorn", "main:app", "--port", "3000", "--reload" -WorkingDirectory ".\frontend" -NoNewWindow

Write-Host "Backend: http://localhost:8012" -ForegroundColor Cyan
Write-Host "Frontend: http://localhost:3000" -ForegroundColor Cyan
Write-Host "API Docs: http://localhost:8012/docs" -ForegroundColor Cyan
