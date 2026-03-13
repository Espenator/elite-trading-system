@echo off
:: Embodier Trader — PC2 (ProfitTrader) 24/7 Auto-Launcher
:: Double-click this file to start all services with auto-restart and health monitoring.
title Embodier Trader - PC2 ProfitTrader 24/7
cd /d "%~dp0"
pwsh -NoExit -ExecutionPolicy Bypass -File "%~dp0start-pc2.ps1"
if errorlevel 1 pause
