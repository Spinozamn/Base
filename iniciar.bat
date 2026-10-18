@echo off
title Sistema de Orientacion Normativa - UdeG
cd /d "%~dp0"

echo ==============================================================================
echo Universidad de Guadalajara - Red Universitaria
echo Sistema de Orientacion y Consulta Normativa Institucional
echo Desarrollado por: Jose Manuel Espinoza Romero
echo ==============================================================================
echo.
echo Iniciando servicio local y abriendo interfaz grafica...
echo.

if exist ".\venv\Scripts\python.exe" (
    ".\venv\Scripts\python.exe" servidor.py
) else (
    python servidor.py
)

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Ocurrio un error al ejecutar el sistema.
    pause
)
