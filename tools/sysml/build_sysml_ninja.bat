@echo off
REM Build Blender-SML with the pinned MSVC 19.44.35216 toolset (avoids the
REM 19.44.35228 ICE in BLI_normalized_int_types.hh). Uses Ninja so we can
REM point at a specific cl.exe regardless of VS-installer registration.
REM
REM Usage (from any cmd prompt):
REM   build_sysml_ninja.bat            -> configure (if needed) + build INSTALL
REM   build_sysml_ninja.bat configure -> configure only
REM   build_sysml_ninja.bat test      -> run the SysML python test after build
setlocal ENABLEEXTENSIONS

set "VCROOT=C:\BuildTools_17.14.14\VC\Tools\MSVC\14.44.35207"
set "VCBIN=%VCROOT%\bin\Hostx64\x64"
set "CLEXE=%VCBIN%\cl.exe"
set "NINJA=C:\Program Files\Microsoft Visual Studio\2022\Community\Common7\IDE\CommonExtensions\Microsoft\CMake\Ninja"
set "SRC=C:\Users\ysevi\mbse-tools\blender-sml"
set "BLD=C:\Users\ysevi\mbse-tools\build_sysml_vc1714_ninja"

REM Base environment (Windows SDK + linker + mt/rc) from the registered install.
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat" || goto :err

REM Make the pinned 35216 toolset win over the 35228 one set up by vcvars.
set "PATH=%VCBIN%;%NINJA%;%PATH%"
set "INCLUDE=%VCROOT%\include;%INCLUDE%"
set "LIB=%VCROOT%\lib\x64;%LIB%"

echo === Compiler in use ===
"%CLEXE%" 2>&1 | findstr /C:"Version"

if /I "%~1"=="configure" goto :configure
if not exist "%BLD%\build.ninja" goto :configure
goto :build

:configure
echo === Configuring (Ninja, cl 35216) ===
cmake -S "%SRC%" -B "%BLD%" -G Ninja ^
  -DCMAKE_BUILD_TYPE=Release ^
  -DCMAKE_C_COMPILER="%CLEXE%" ^
  -DCMAKE_CXX_COMPILER="%CLEXE%" ^
  -DWITH_USD=OFF -DWITH_HYDRA=OFF || goto :err
if /I "%~1"=="configure" goto :done

:build
if "%JOBS%"=="" set "JOBS=6"
echo === Building INSTALL (jobs=%JOBS%) ===
cmake --build "%BLD%" --target install -- -j %JOBS% || goto :err

if /I "%~1"=="test" (
  echo === Running SysML node test ===
  "%BLD%\bin\blender.exe" --background --factory-startup --python "%SRC%\tests\python\bl_sysml_nodetree.py" || goto :err
)

:done
echo === DONE ===
endlocal & exit /b 0

:err
echo === FAILED (errorlevel %errorlevel%) ===
endlocal & exit /b 1
