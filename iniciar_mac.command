#!/bin/bash
cd "$(dirname "$0")"

echo "=============================================================================="
echo "Universidad de Guadalajara - Red Universitaria"
echo "Sistema de Orientacion y Consulta Normativa Institucional"
echo "Desarrollado por: Jose Manuel Espinoza Romero"
echo "=============================================================================="
echo ""
echo "Iniciando servicio local y abriendo interfaz grafica..."
echo ""

if [ -f "./venv/bin/python" ]; then
    ./venv/bin/python servidor.py
elif [ -f "./venv/bin/python3" ]; then
    ./venv/bin/python3 servidor.py
elif command -v python3 &>/dev/null; then
    python3 servidor.py
elif command -v python &>/dev/null; then
    python servidor.py
else
    echo "Error: No se encontro ninguna instalacion de Python en este equipo."
    read -p "Presione Enter para salir..."
fi
