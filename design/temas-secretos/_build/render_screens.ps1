# Rasteriza as 8 telas + a galeria para exports/.
# Uso: powershell -ExecutionPolicy Bypass -File _build/render_screens.ps1
param([int]$Port = 8765)

$root = Split-Path -Parent $PSScriptRoot
$out = Join-Path $root 'exports'
New-Item -ItemType Directory -Path $out -Force | Out-Null

$edgeCandidates = @(
  'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
  'C:\Program Files\Microsoft\Edge\Application\msedge.exe',
  'C:\Program Files\Google\Chrome\Application\chrome.exe',
  'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe'
)
$browser = $edgeCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $browser) { throw 'Edge/Chrome não encontrado.' }

$profileDir = Join-Path $env:TEMP ("pagflow-theme-render-" + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $profileDir -Force | Out-Null

$server = Start-Process python -ArgumentList '-m', 'http.server', "$Port", '--bind', '127.0.0.1', '--directory', $root -PassThru -WindowStyle Hidden
Start-Sleep -Milliseconds 900

$files = @(
  '01-graduation-principal', '01-graduation-configuracoes',
  '02-ozzy-principal', '02-ozzy-configuracoes',
  '03-lana-principal', '03-lana-configuracoes',
  '04-acai-principal', '04-acai-configuracoes'
)

try {
  foreach ($file in $files) {
    $png = Join-Path $out "$file.png"
    & $browser --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=1 `
      --window-size=1280,960 --virtual-time-budget=8000 `
      --run-all-compositor-stages-before-draw `
      --user-data-dir="$profileDir" `
      --screenshot="$png" "http://127.0.0.1:$Port/screens/$file.html" 2>$null | Out-Null
    if (Test-Path $png) { Write-Output "ok $file" } else { Write-Output "FALHOU $file" }
  }

  $index = Join-Path $out 'index.png'
  & $browser --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=1 `
    --window-size=1280,1900 --virtual-time-budget=10000 `
    --run-all-compositor-stages-before-draw `
    --user-data-dir="$profileDir" `
    --screenshot="$index" "http://127.0.0.1:$Port/screens/index.html" 2>$null | Out-Null
  if (Test-Path $index) { Write-Output 'ok index' } else { Write-Output 'FALHOU index' }
}
finally {
  Stop-Process -Id $server.Id -Force -ErrorAction SilentlyContinue
  Remove-Item -LiteralPath $profileDir -Recurse -Force -ErrorAction SilentlyContinue
}
