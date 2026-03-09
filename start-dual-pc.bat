@echo off
REM Elite Trading System - Dual-PC Launcher
REM Wrapper for start-dual-pc.ps1 to allow double-click execution

powershell.exe -ExecutionPolicy Bypass -File "%~dp0start-dual-pc.ps1" %*
