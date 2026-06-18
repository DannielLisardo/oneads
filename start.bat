@echo off
echo.
echo  ==========================================
echo    OneAds — Iniciando Backend
echo  ==========================================
echo.

cd /d "%~dp0backend"

IF NOT EXIST ".env" (
    echo  [AVISO] Arquivo .env nao encontrado.
    echo  Copie .env.example para .env e preencha as credenciais.
    echo.
    pause
    exit /b 1
)

IF NOT EXIST "venv\Scripts\activate.bat" (
    echo  Criando ambiente virtual Python...
    python -m venv venv
)

call venv\Scripts\activate.bat

echo  Instalando dependencias...
pip install -r requirements.txt --quiet

echo.
echo  Backend rodando em http://localhost:8000
echo  Interface em    http://localhost:8000
echo  Documentacao em http://localhost:8000/docs
echo.

python main.py
