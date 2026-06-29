<#
.SYNOPSIS
    Configure, build, and test the SysML-nodes Blender fork (BSML / SCRUM-430+).

.DESCRIPTION
    Wraps the dev-build flow we use for the SysML node feature. Unlike the stock
    make.bat this:
      * fetches the lib/windows_x64 precompiled-deps submodule if missing,
      * configures with WITH_USD/WITH_HYDRA OFF by default (faster dev builds;
        USD's PCH is memory-hungry and not needed to validate SysML nodes),
      * builds via `cmake --build` (so it does NOT silently re-enable USD the
        way `make.bat` does on every invocation),
      * caps parallelism for low-RAM machines (default 4 projects x 2 cl each),
      * optionally runs the bl_sysml_nodetree bpy test.

    Run from an ordinary PowerShell prompt (no admin needed for the build).

.PARAMETER Jobs          Parallel msbuild projects (/m). Keep low on <=16 GB RAM.
.PARAMETER ClPerProject  cl.exe processes per project (/MP via CL_MPCount).
.PARAMETER WithUsd       Build with USD + Hydra enabled (slower, more memory).
.PARAMETER Reconfigure   Force a fresh cmake configure even if Blender.sln exists.
.PARAMETER NoBuild       Configure only (validate CMake), don't compile.
.PARAMETER Test          After a successful build, run the SysML bpy test.
.PARAMETER Config        Release (default) | Debug | RelWithDebInfo.

.EXAMPLE
    # First build on a 16 GB machine, then run the test:
    pwsh tools/sysml/build_sysml.ps1 -Jobs 4 -ClPerProject 2 -Test

.EXAMPLE
    # Just validate the CMake wiring (fast):
    pwsh tools/sysml/build_sysml.ps1 -NoBuild -Reconfigure
#>
[CmdletBinding()]
param(
    [int]$Jobs = 4,
    [int]$ClPerProject = 2,
    [switch]$WithUsd,
    [switch]$Reconfigure,
    [switch]$NoBuild,
    [switch]$Test,
    [ValidateSet("Release", "Debug", "RelWithDebInfo")]
    [string]$Config = "Release"
)

$ErrorActionPreference = "Stop"

# Resolve the repo root from this script's location, then the *provider* path so
# a subst'd drive (e.g. M: -> C:\...) doesn't trip up detached child processes.
$RepoRoot = (Resolve-Path "$PSScriptRoot\..\..").ProviderPath
$BuildDir = Join-Path (Split-Path $RepoRoot -Parent) "build_windows_x64_vc17_Release"
$Cmake = (Get-Command cmake -ErrorAction SilentlyContinue).Source
if (-not $Cmake) { throw "cmake not found on PATH (install CMake or add it to PATH)." }

Write-Host "Repo:  $RepoRoot"
Write-Host "Build: $BuildDir"

# 1. Precompiled dependency libraries (large submodule; update=none by default).
if (-not (Test-Path (Join-Path $RepoRoot "lib\windows_x64\.gitattributes"))) {
    Write-Host "==> Fetching lib/windows_x64 submodule (multi-GB, one-time)..."
    git -C $RepoRoot -c submodule.lib/windows_x64.update=checkout `
        submodule update --init --depth 1 -- lib/windows_x64
    if ($LASTEXITCODE -ne 0) { throw "lib submodule fetch failed." }
}

# 2. Configure.
$usd = if ($WithUsd) { "ON" } else { "OFF" }
if ($Reconfigure -or -not (Test-Path (Join-Path $BuildDir "Blender.sln"))) {
    Write-Host "==> Configuring (WITH_USD=$usd, WITH_HYDRA=$usd)..."
    & $Cmake -S $RepoRoot -B $BuildDir -DWITH_USD=$usd -DWITH_HYDRA=$usd
    if ($LASTEXITCODE -ne 0) { throw "CMake configure failed." }
}
if ($NoBuild) { Write-Host "==> NoBuild: configure complete."; return }

# 3. Build (capped parallelism). INSTALL target => runnable bin\$Config\blender.exe.
Write-Host "==> Building INSTALL ($Config) with $Jobs projects x $ClPerProject cl..."
& $Cmake --build $BuildDir --config $Config --target INSTALL `
    --parallel $Jobs -- "/p:CL_MPCount=$ClPerProject" /nologo
if ($LASTEXITCODE -ne 0) { throw "Build failed (exit $LASTEXITCODE). See output above." }

$Blender = Join-Path $BuildDir "bin\$Config\blender.exe"
Write-Host "==> Built: $Blender"

# 4. Optional: SysML node-tree bpy test (one pass + one expected-fail until SCRUM-433).
if ($Test) {
    Write-Host "==> Running bl_sysml_nodetree..."
    & $Blender --background --factory-startup `
        --python (Join-Path $RepoRoot "tests\python\bl_sysml_nodetree.py")
}
