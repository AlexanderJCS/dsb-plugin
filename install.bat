@echo off
setlocal

:: Check for admin rights
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Requesting administrator privileges...
    powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -WorkingDirectory '%~dp0' -Verb RunAs"
    exit /b
)

set "SCRIPT_DIR=%~dp0"

set "DRAGONFLY_INSTALL_PATH=C:\ProgramData\ORS\Dragonfly2024.1"

:: Copy files
echo Copying files...
xcopy "%SCRIPT_DIR%*.*" "%DRAGONFLY_INSTALL_PATH%\pythonAllUsersExtensions\Plugins\DSB_efd060071a1711f0b40cf83441a96bd5" /E /I /Y >nul

:: Install Python dependencies
echo Installing Python dependencies...
"%DRAGONFLY_INSTALL_PATH%\Anaconda3\python.exe" -m pip install -r "%DRAGONFLY_INSTALL_PATH%\pythonAllUsersExtensions\Plugins\DSB_efd060071a1711f0b40cf83441a96bd5\requirements.txt"

:: echo( is a newline
echo(
echo Complete. Please restart Dragonfly to apply changes.
pause