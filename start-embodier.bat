@echo off
title Embodier Trader v3.2.0
color 0A
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File ".\start-embodier.ps1"
pause
