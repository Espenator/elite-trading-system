@echo off
:: Embodier Trader — PC2 (ProfitTrader) One-Click Launcher
:: Double-click this file to start all PC2 services with auto-restart.
title Embodier Trader - PC2 ProfitTrader
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File "%~dp0start-pc2.ps1"
pause
