@echo off
title Sistema Integrado de Evaluacion Eolica - Parque Windpeshi
chcp 65001 > nul
cls

echo ==============================================================================
echo        PARQUE EOLICO WINDPESHI - SISTEMA DE ADQUISICION E INTEGRACION
echo ==============================================================================
echo.
echo [*] Iniciando entorno virtual y servidor web local...
echo.

:: Cambiar al directorio donde se encuentra este archivo .bat
cd /d "%~dp0"

:: Verificar que exista el entorno virtual
if not exist ".\.venv\Scripts\activate.bat" (
    echo [ERROR] No se encontro el entorno virtual en .venv.
    echo Asegurate de haber instalado las dependencias previamente.
    pause
    exit /b 1
)

:: Activar el entorno virtual
call .\.venv\Scripts\activate.bat

:: Ejecutar el servidor web del dashboard
python web_server.py

pause
