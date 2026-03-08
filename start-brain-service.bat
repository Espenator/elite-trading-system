@echo off
REM Brain Service Launcher
REM Starts the gRPC brain service for LLM inference
powershell.exe -ExecutionPolicy Bypass -File "%~dp0start-brain-service.ps1" %*
