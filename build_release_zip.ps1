$ErrorActionPreference = "Stop"

$version = "1.0.0"
$appName = "ControleDeAcesso"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$workspaceRoot = Split-Path -Parent $root
$landingDir = Join-Path $workspaceRoot "Landing Page"
$releaseRoot = Join-Path $root "public-release"
$packageName = "$appName-v$version"
$packageDir = Join-Path $releaseRoot $packageName
$zipPath = Join-Path $releaseRoot "$packageName.zip"

if (Test-Path $packageDir) {
    Remove-Item -LiteralPath $packageDir -Recurse -Force
}

if (Test-Path $zipPath) {
    Remove-Item -LiteralPath $zipPath -Force
}

New-Item -ItemType Directory -Path $packageDir | Out-Null

$files = @(
    "main.py",
    "run_prod.py",
    "launcher.py",
    "requirements.txt",
    "config.env.example",
    "install_dependencies.bat",
    "README.md"
)

foreach ($file in $files) {
    Copy-Item -LiteralPath (Join-Path $root $file) -Destination $packageDir -Force
}

Copy-Item -LiteralPath (Join-Path $root "templates") -Destination $packageDir -Recurse -Force
Copy-Item -LiteralPath (Join-Path $root "static") -Destination $packageDir -Recurse -Force

$launcherExe = Join-Path $root "release\ControleDeAcesso.exe"
if (-not (Test-Path $launcherExe)) {
    throw "Nao encontrei release\ControleDeAcesso.exe. Rode build_launcher.bat antes."
}

Copy-Item -LiteralPath $launcherExe -Destination (Join-Path $packageDir "ControleDeAcesso.exe") -Force

$packageReadme = Join-Path $packageDir "LEIA-ME.txt"
@"
Controle de Acesso - Instalação

1. Extraia este ZIP em uma pasta fixa do computador.
2. Execute install_dependencies.bat uma vez para criar o ambiente Python local.
3. Abra ControleDeAcesso.exe.
4. No primeiro acesso, crie o usuario e senha administrativos.
5. Cadastre o equipamento ControlID pela tela Gerenciar equipamentos.

Este pacote nao inclui credenciais reais, banco SQLite ou logs.
"@ | Set-Content -LiteralPath $packageReadme -Encoding UTF8

Compress-Archive -LiteralPath $packageDir -DestinationPath $zipPath -Force
Remove-Item -LiteralPath $packageDir -Recurse -Force

if (Test-Path $landingDir) {
    $landingDownloads = Join-Path $landingDir "downloads"
    New-Item -ItemType Directory -Path $landingDownloads -Force | Out-Null
    Copy-Item -LiteralPath $zipPath -Destination (Join-Path $landingDownloads "$packageName.zip") -Force
}

Write-Host "ZIP criado em: $zipPath"
