@echo off
REM phone_intel TUI launcher. Examples:
REM   scan +14155552671
REM   scan "+63 917 123 4567" --qr
REM   scan --batch numbers.txt --export out
cd /d "%~dp0"
python -m phone_intel %*
