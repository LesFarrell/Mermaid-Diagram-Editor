param(
    [ValidateSet("standalone", "onefile")]
    [string]$Mode = "standalone",
    [string]$PythonExe = "python",
    [switch]$RunAfterBuild
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$mainScript = Join-Path $projectRoot "mermaid_diagram_tool.py"
$outputRoot = Join-Path $projectRoot "build\nuitka"
$configFile = Join-Path $projectRoot "mermaid_tool_config.txt"

if (-not (Test-Path $mainScript)) {
    throw "Could not find main script: $mainScript"
}

$nuitkaCheck = & $PythonExe -c "import importlib.util; raise SystemExit(0 if importlib.util.find_spec('nuitka') else 1)" 2>$null
if ($LASTEXITCODE -ne 0) {
    throw "Nuitka is not installed for '$PythonExe'. Install it with: $PythonExe -m pip install nuitka"
}

$nuitkaVersion = (& $PythonExe -m nuitka --version 2>&1 | Select-Object -First 1).ToString().Trim()

New-Item -ItemType Directory -Force -Path $outputRoot | Out-Null

$nuitkaArgs = @(
    "-m", "nuitka",
    "--assume-yes-for-downloads",
    "--enable-plugin=tk-inter",
    "--windows-console-mode=disable",
    "--remove-output",
    "--output-dir=$outputRoot",
    "--output-filename=MermaidDiagramEditor",
    "--include-data-dir=samples=samples",
    "--include-package=tksvg",
    "--include-package=PIL",
    "--mode=$Mode",
    $mainScript
)

if (Test-Path $configFile) {
    $nuitkaArgs += "--include-data-files=$configFile=mermaid_tool_config.txt"
}

Write-Host "Using Nuitka: $nuitkaVersion"
Write-Host "Building mode: $Mode"
Write-Host ""
Write-Host "$PythonExe $($nuitkaArgs -join ' ')"
Write-Host ""

& $PythonExe @nuitkaArgs
if ($LASTEXITCODE -ne 0) {
    throw "Nuitka build failed."
}

$artifactPath =
    if ($Mode -eq "onefile") {
        Join-Path $outputRoot "MermaidDiagramEditor.exe"
    } else {
        Join-Path $outputRoot "MermaidDiagramEditor.dist\MermaidDiagramEditor.exe"
    }

Write-Host ""
Write-Host "Build complete:"
Write-Host "  $artifactPath"

if ($RunAfterBuild -and (Test-Path $artifactPath)) {
    Write-Host ""
    Write-Host "Launching built executable..."
    Start-Process -FilePath $artifactPath -WorkingDirectory (Split-Path $artifactPath)
}
