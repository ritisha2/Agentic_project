@echo off
title ESP APM ? Local CUDA GPU LLM Server (RTX 3050)
color 0B

echo ===============================================================================
echo   ESP APM ? LOCAL CUDA GPU LLM INFERENCE SERVER (llama.cpp)
echo ===============================================================================
echo   - Device  : NVIDIA GeForce RTX 3050 Laptop GPU (6GB VRAM)
echo   - Model   : Qwen2.5-Coder-3B-Instruct-Q4_K_M.gguf
echo   - Port    : http://127.0.0.1:8080/v1
echo   - Speed   : ~58 tokens/sec (CUDA backend)
echo ===============================================================================
echo.

cd /d "%~dp0"

if not exist "bin\llama-cpp\llama-server.exe" (
    echo [ERROR] bin\llama-cpp\llama-server.exe not found!
    pause
    exit /b 1
)

if not exist "models\Qwen2.5-Coder-3B-Instruct-Q4_K_M.gguf" (
    echo [ERROR] Model models\Qwen2.5-Coder-3B-Instruct-Q4_K_M.gguf not found!
    pause
    exit /b 1
)

echo Starting GPU llama-server with 100%% layer offloading (-ngl 99)...
bin\llama-cpp\llama-server.exe -m models\Qwen2.5-Coder-3B-Instruct-Q4_K_M.gguf -ngl 99 -c 4096 --host 0.0.0.0 --port 8080
