@echo off
REM ---------------------------------------------------------------------------
REM  Sheet metal forming automation - student installer.
REM
REM  Double-click this file. It downloads the current version from GitHub and
REM  installs the ANSA and META macros for the logged-in user. ANSA 25.1.1 must
REM  already be installed. No administrator rights are needed.
REM
REM  The line below deliberately does NOT use the usual "irm URL | iex" form.
REM  Measured on the class machine 2026-09-14: piping into iex exits with code 5
REM  and prints only "Access is denied", before PowerShell produces any output at
REM  all. Wrapping it as "iex (irm URL)" does exactly the same work and runs
REM  normally. Do not change it back.
REM
REM  Everything it does is in download.ps1 and install.ps1 in the repository:
REM  https://github.com/JonssonLogic/SheetMetalSim
REM ---------------------------------------------------------------------------
title Sheet metal forming automation - install

echo.
echo  Sheet metal forming automation
echo  ------------------------------
echo.
echo  This installs the ANSA and META teaching macros for your user account.
echo.
echo  Close ANSA and META before continuing. Both rewrite their own settings
echo  when they exit, which would undo the install.
echo.
pause

powershell -NoProfile -ExecutionPolicy Bypass -Command "iex (irm https://raw.githubusercontent.com/JonssonLogic/SheetMetalSim/main/download.ps1)"

if errorlevel 1 (
    echo.
    echo  The install did not finish. The messages above say why.
) else (
    echo.
    echo  Done. Start ANSA to use it.
)

echo.
pause
