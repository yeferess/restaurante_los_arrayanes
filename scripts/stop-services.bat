@echo off
rem Envoltorio para poder correr stop-services.ps1 aunque la politica de ejecucion bloquee scripts.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0stop-services.ps1" %*
