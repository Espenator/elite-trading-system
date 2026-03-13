@echo off
:: Embodier Trader — PC1 (ESPENMAIN) One-Click Launcher
:: Double-click this file to start all PC1 services with auto-restart.
title Embodier Trader - PC1 ESPENMAIN
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File "%~dp0start-pc1.ps1"
pause
