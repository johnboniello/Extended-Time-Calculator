@echo off
setlocal enabledelayedexpansion

REM This script lives in packaging\windows\. The source file it builds
REM lives two levels up, in src\. All output (build_log.txt, the dist\
REM and build\ folders PyInstaller creates, and the installer exe) is kept
REM right here in packaging\windows\, out of the way of the repo's source
REM tree, and is excluded from git via .gitignore.
cd /d "%~dp0"
set REPO_ROOT=%~dp0..\..
set SRC=%REPO_ROOT%\src\extended_time_calculator.py

set LOG=build_log.txt
echo ===================================================== > "%LOG%"
echo  Extended Time Calculator - build started %DATE% %TIME% >> "%LOG%"
echo ===================================================== >> "%LOG%"

REM --- Find a working Python launcher -----------------------------------
set PYCMD=
where python >nul 2>&1
if %ERRORLEVEL%==0 (
    set PYCMD=python
) else (
    where py >nul 2>&1
    if %ERRORLEVEL%==0 (
        set PYCMD=py -3
    )
)

if "%PYCMD%"=="" (
    echo ERROR: No Python installation found on PATH ^(tried "python" and "py"^). >> "%LOG%"
    echo ERROR: No Python installation found on PATH. See build_log.txt.
    goto :end
)

echo Using Python command: %PYCMD% >> "%LOG%"
echo Building from: %SRC% >> "%LOG%"
%PYCMD% --version >> "%LOG%" 2>&1

echo. >> "%LOG%"
echo --- Installing/upgrading build dependencies (PyQt5, pyinstaller) --- >> "%LOG%"
%PYCMD% -m pip install --upgrade pip >> "%LOG%" 2>&1
%PYCMD% -m pip install --upgrade -r "%REPO_ROOT%\requirements.txt" pyinstaller Pillow >> "%LOG%" 2>&1
if not %ERRORLEVEL%==0 (
    echo ERROR: pip install failed. See build_log.txt for details. >> "%LOG%"
    echo ERROR: pip install failed. See build_log.txt for details.
    goto :end
)

echo. >> "%LOG%"
echo --- Building the executable with PyInstaller --- >> "%LOG%"

set ICONARG=
if exist "appicon.ico" set ICONARG=--icon "appicon.ico"

%PYCMD% -m PyInstaller --noconfirm --onefile --windowed --name "Extended Time Calculator" %ICONARG% --distpath "dist" --workpath "build" --specpath "." "%SRC%" >> "%LOG%" 2>&1
set PYIRC=%ERRORLEVEL%

if not %PYIRC%==0 (
    if not "%ICONARG%"=="" (
        echo. >> "%LOG%"
        echo WARNING: build with icon failed ^(exit code %PYIRC%^), retrying without an icon... >> "%LOG%"
        %PYCMD% -m PyInstaller --noconfirm --onefile --windowed --name "Extended Time Calculator" --distpath "dist" --workpath "build" --specpath "." "%SRC%" >> "%LOG%" 2>&1
        set PYIRC=%ERRORLEVEL%
    )
)

if not %PYIRC%==0 (
    echo ERROR: PyInstaller exited with code %PYIRC%. See build_log.txt. >> "%LOG%"
    echo ERROR: build failed - see build_log.txt
    goto :end
)

if not exist "dist\Extended Time Calculator.exe" (
    echo ERROR: PyInstaller reported success but dist\Extended Time Calculator.exe is missing. See build_log.txt. >> "%LOG%"
    echo ERROR: build failed - see build_log.txt
    goto :end
)

echo. >> "%LOG%"
echo SUCCESS: dist\Extended Time Calculator.exe was created ^(exit code %PYIRC%^). >> "%LOG%"

REM --- Optionally build the Inno Setup installer, if Inno Setup is installed --------
set ISCC=
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" set ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe
if exist "C:\Program Files\Inno Setup 6\ISCC.exe" set ISCC=C:\Program Files\Inno Setup 6\ISCC.exe
if exist "C:\Program Files (x86)\Inno Setup 5\ISCC.exe" set ISCC=C:\Program Files (x86)\Inno Setup 5\ISCC.exe

if not "%ISCC%"=="" (
    echo. >> "%LOG%"
    echo --- Found Inno Setup, building the installer too --- >> "%LOG%"
    "%ISCC%" "extended_time_calculator.iss" >> "%LOG%" 2>&1
    if exist "extended_time_calculator_setup.exe" (
        echo SUCCESS: extended_time_calculator_setup.exe was created. >> "%LOG%"
    ) else (
        echo NOTE: Inno Setup ran but the installer exe was not found - check build_log.txt. >> "%LOG%"
    )
) else (
    echo. >> "%LOG%"
    echo NOTE: Inno Setup ^(ISCC.exe^) was not found in the usual install locations, >> "%LOG%"
    echo NOTE: so only the plain .exe was built, not a Setup installer. >> "%LOG%"
    echo NOTE: Install Inno Setup from https://jrsoftware.org/isdl.php and re-run this >> "%LOG%"
    echo NOTE: script if you want the installer too. >> "%LOG%"
)

echo DONE > BUILD_DONE.txt
echo.
echo Build finished. Opening the folder now - check build_log.txt for full details.
start "" explorer.exe "%~dp0"
goto :eof

:end
echo DONE_WITH_ERRORS > BUILD_DONE.txt
echo.
echo Something went wrong - opening the folder so you can check build_log.txt.
start "" explorer.exe "%~dp0"

:eof
