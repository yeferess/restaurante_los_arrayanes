@echo off
cd /d "C:/Users/ACER/Documents/Software_LA/restaurante_los_arrayanes/backend"
call venv\Scripts\activate.bat
python -m daphne -b 127.0.0.1 -p 8000 config.asgi:application
