@echo off
title Embodier Trader v4.1.0
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File start-embodier.ps1
pause
