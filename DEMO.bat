@echo off
rem Doble clic para levantar la demo completa: firmware + app + dashboard.
cd /d "%~dp0"
python -m hsf_app.demo
pause
