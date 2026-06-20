@echo off
title Financa Simples - Iniciando...
color 1F

echo.
echo  ========================================
echo   FINANCA SIMPLES - Iniciando o sistema
echo  ========================================
echo.

:: Inicia o app Python em uma nova janela
echo  [1/2] Iniciando o aplicativo...
start "Financa Simples - APP" cmd /k "cd /d C:\Alexandre\ControleFinanceiro && set FLET_SECRET_KEY=financasimples2026 && python main.py"

:: Aguarda 3 segundos para o app subir
timeout /t 3 /nobreak > nul

:: Inicia o Ngrok em uma nova janela
echo  [2/2] Iniciando o tunel Ngrok...
start "Financa Simples - NGROK" cmd /k "ngrok http 8080"

timeout /t 3 /nobreak > nul

echo.
echo  ========================================
echo   Sistema iniciado com sucesso!
echo   Acesse: http://localhost:8080
echo  ========================================
echo.
pause