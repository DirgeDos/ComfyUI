@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

set "COMFY_PYTHON=%~dp0..\python_embeded\python.exe"
set "COMFY_RUNTIME=%~dp0runtime\gpu0"

if not exist "%COMFY_PYTHON%" (
    echo [ERROR] Portable Python not found: "%COMFY_PYTHON%"
    pause
    exit /b 1
)

REM Keep the default custom_nodes directory even when plugins are external.
if not exist "custom_nodes" mkdir "custom_nodes"
if not exist "%COMFY_RUNTIME%\user" mkdir "%COMFY_RUNTIME%\user"
if not exist "%COMFY_RUNTIME%\temp_root" mkdir "%COMFY_RUNTIME%\temp_root"
if not exist "input" mkdir "input"
if not exist "output" mkdir "output"

"%COMFY_PYTHON%" -s "%~dp0main.py" ^
    --windows-standalone-build ^
    --listen 0.0.0.0 ^
    --port 8188 ^
    --enable-manager ^
    --preview-method auto ^
    --preview-size 512 ^
    --enable-cors-header "*" ^
    --disable-dynamic-vram ^
    --disable-cuda-malloc ^
    --cuda-device 0 ^
    --database-url "sqlite:///%COMFY_RUNTIME:\=/%/user/comfyui_gpu0.db" ^
    --user-directory "%COMFY_RUNTIME%\user" ^
    --temp-directory "%COMFY_RUNTIME%\temp_root" ^
    --input-directory "%~dp0input" ^
    --output-directory "%~dp0output" %* ^
    --models-directory "G:\data\pj_code\ai-aigc-models-asset-zhuji\models"

set "COMFY_EXIT_CODE=%ERRORLEVEL%"
if not "%COMFY_EXIT_CODE%"=="0" pause
exit /b %COMFY_EXIT_CODE%
