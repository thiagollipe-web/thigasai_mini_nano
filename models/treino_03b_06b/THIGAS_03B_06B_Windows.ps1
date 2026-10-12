# Script PowerShell — THIGAS AI Nano e Mini, Windows.
param(
  [ValidateSet("Baixar","Verificar","Iniciar")]
  [string]$Acao = "Baixar",
  [string]$Diretorio = "$env:USERPROFILE\THIGAS_MODELOS"
)
$ErrorActionPreference = "Stop"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$release = "https://github.com/thiagollipe-web/thigasai_mini_nano/releases/download"
$models = @(
 @{ id="nano"; tag="thigas-nano-03b-v1"; file="THIGAS_AI_nano_03B_Q4_K_M.gguf"; alias="THIGAS_AI_nano_03B"; context=2048; port=8091 },
 @{ id="mini"; tag="thigas-mini-06b-v1"; file="THIGAS_AI_mini_06B_Q4_K_M.gguf"; alias="THIGAS_AI_mini_06B"; context=4096; port=8092 }
)
New-Item -ItemType Directory -Path $Diretorio -Force | Out-Null
foreach($m in $models) {
 $root = "$release/$($m.tag)"
 $path = Join-Path $Diretorio $m.file
 $reportPath = Join-Path $Diretorio "train_report_$($m.id).json"
 Write-Host "Verificando modelo $($m.id)..." -ForegroundColor Cyan
 Invoke-WebRequest -Uri "$root/train_report_$($m.id).json" -OutFile $reportPath -UseBasicParsing
 $report = Get-Content $reportPath -Raw -Encoding UTF8 | ConvertFrom-Json
 if($report.filename -ne $m.file -or -not $report.sha256) { throw "Relatorio ausente ou incorreto." }
 $download = -not(Test-Path -LiteralPath $path)
 if(-not $download) {
  $hash = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
  $download = ($hash -ne $report.sha256.ToLowerInvariant())
 }
 if($download) {
  if($Acao -eq "Verificar") { throw "Modelo nao encontrado ou hash errado: $path" }
  Write-Host "Baixando $($m.file)..."
  Invoke-WebRequest -Uri "$root/$($m.file)" -OutFile $path -UseBasicParsing
 }
 $hash = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
 if($hash -ne $report.sha256.ToLowerInvariant()) {
  Remove-Item -LiteralPath $path -Force
  throw "SHA-256 divergente: arquivo excluido por seguranca"
 }
 Write-Host "Verificado: $path" -ForegroundColor Green
}
if($Acao -ne "Iniciar") {
 Write-Host "Para iniciar execute: .\THIGAS_03B_06B_Windows.ps1 -Acao Iniciar"
 exit 0
}
$llama = Get-Command llama-server -ErrorAction SilentlyContinue
if(-not $llama) { throw "llama-server indisponivel. Instale llama.cpp e reabra o PowerShell." }
$key = Read-Host "Informe token privado (minimo 16 caracteres) para as duas APIs"
if($key.Length -lt 16) { throw "Token demasiado curto." }
foreach($m in $models) {
 $path = Join-Path $Diretorio $m.file
 $arg = @("-m","$([char]34)$path$([char]34)","-c",[string]$m.context,"--host","127.0.0.1","--port",[string]$m.port,"--alias",$m.alias,"--api-key",$key,"-ngl","0","-t","4")
 $p = Start-Process -FilePath $llama.Source -ArgumentList $arg -PassThru -WorkingDirectory (Split-Path $llama.Source) -RedirectStandardOutput (Join-Path $Diretorio "$($m.id)-stdout.log") -RedirectStandardError (Join-Path $Diretorio "$($m.id)-stderr.log")
 Write-Host "Iniciado $($m.alias), porta $($m.port), PID $($p.Id)"
}
$key = $null
Write-Host "Modelos acessiveis somente no localhost. Para o site Render, configure tunel HTTPS autenticado."
