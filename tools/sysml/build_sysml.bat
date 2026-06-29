@echo off
REM ============================================================================
REM  build_sysml.bat - SysML-nodes Blender fork dev build (BSML / SCRUM-430+)
REM
REM  Run from a "x64 Native Tools Command Prompt for VS 2022" (Developer Prompt),
REM  where cl/msbuild/cmake are already on PATH.
REM
REM  Usage:
REM     build_sysml.bat [nobuild] [reconfigure] [withusd] [test]
REM
REM     nobuild      Configure only (validate CMake), do not compile.
REM     reconfigure  Force a fresh cmake configure even if Blender.sln exists.
REM     withusd      Build with USD + Hydra ON (default: OFF - faster, less RAM).
REM     test         After a successful build, run the bl_sysml_nodetree bpy test.
REM
REM  Tunables (set before calling, or edit defaults below):
REM     set JOBS=4     parallel msbuild projects   (keep low on <=16 GB RAM)
REM     set CLMP=2     cl.exe per project (/MP)     (JOBS*CLMP = peak compilers)
REM ============================================================================
setlocal EnableDelayedExpansion

REM --- resolve paths (script lives in tools\sysml) ---
for %%I in ("%~dp0..\..") do set "ROOT=%%~fI"
for %%I in ("%ROOT%\..") do set "PARENT=%%~fI"
set "BUILD=%PARENT%\build_windows_x64_vc17_Release"

REM --- defaults ---
if not defined JOBS set JOBS=4
if not defined CLMP set CLMP=2
set "USD=OFF"
set "RUNTEST=0"
set "DOBUILD=1"
set "RECONF=0"

REM --- parse args ---
:parse
if "%~1"=="" goto endparse
if /I "%~1"=="test"        set "RUNTEST=1"
if /I "%~1"=="nobuild"     set "DOBUILD=0"
if /I "%~1"=="reconfigure" set "RECONF=1"
if /I "%~1"=="withusd"     set "USD=ON"
shift
goto parse
:endparse

REM --- locate cmake ---
where cmake >nul 2>nul
if %errorlevel%==0 (set "CMAKE=cmake") else (set "CMAKE=C:\Program Files\CMake\bin\cmake.exe")

echo Repo:  %ROOT%
echo Build: %BUILD%
echo Jobs:  %JOBS% projects x %CLMP% cl   USD=%USD%

REM --- fetch precompiled libs if missing ---
if not exist "%ROOT%\lib\windows_x64\.gitattributes" (
  echo ==^> Fetching lib/windows_x64 submodule ^(multi-GB, one-time^)...
  git -C "%ROOT%" -c submodule.lib/windows_x64.update=checkout submodule update --init --depth 1 -- lib/windows_x64
  if errorlevel 1 (echo lib submodule fetch failed & exit /b 1)
)

REM --- configure ---
set "DOCONF=0"
if "%RECONF%"=="1" set "DOCONF=1"
if not exist "%BUILD%\Blender.sln" set "DOCONF=1"
if "%DOCONF%"=="1" (
  echo ==^> Configuring ^(WITH_USD=%USD%, WITH_HYDRA=%USD%^)...
  "%CMAKE%" -S "%ROOT%" -B "%BUILD%" -DWITH_USD=%USD% -DWITH_HYDRA=%USD%
  if errorlevel 1 (echo Configure failed & exit /b 1)
)
if "%DOBUILD%"=="0" (echo ==^> NoBuild: configure complete. & exit /b 0)

REM --- build (capped parallelism); INSTALL => runnable bin\Release\blender.exe ---
echo ==^> Building INSTALL ^(Release^)...
"%CMAKE%" --build "%BUILD%" --config Release --target INSTALL --parallel %JOBS% -- /p:CL_MPCount=%CLMP% /nologo
if errorlevel 1 (echo Build failed & exit /b 1)

set "BLENDER=%BUILD%\bin\Release\blender.exe"
echo ==^> Built: %BLENDER%

REM --- optional SysML bpy test ---
if "%RUNTEST%"=="1" (
  echo ==^> Running bl_sysml_nodetree...
  "%BLENDER%" --background --factory-startup --python "%ROOT%\tests\python\bl_sysml_nodetree.py"
)

endlocal
