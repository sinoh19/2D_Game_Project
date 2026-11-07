$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
$cache=Join-Path $root '.tools/cache'
$target=Join-Path $root '.tools/tiled'
$exe=Join-Path $target 'PFiles/Tiled/tiled.exe'
if(Test-Path -LiteralPath $exe){Write-Host 'Tiled is ready.';exit 0}
New-Item -ItemType Directory -Force -Path $cache|Out-Null
$msi=Join-Path $cache 'Tiled-1.12.2-x64.msi'
$url='https://github.com/mapeditor/tiled/releases/download/v1.12.2/Tiled-1.12.2_Windows-10%2B_x86_64.msi'
if(!(Test-Path -LiteralPath $msi)){
    Write-Host 'Downloading official Tiled 1.12.2...'
    [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12
    Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $msi
}
$expected='11A0E6C97CC105E07A57EA9995F2704617986722DE4AB699D286DAB0D2BECC3F'
if((Get-FileHash -LiteralPath $msi -Algorithm SHA256).Hash -ne $expected){throw 'Tiled download checksum mismatch.'}
$process=Start-Process -FilePath 'msiexec.exe' -ArgumentList @('/a',('"'+$msi+'"'),'/qn',('TARGETDIR="'+$target+'"')) -WindowStyle Hidden -PassThru -Wait
if($process.ExitCode -ne 0 -or !(Test-Path -LiteralPath $exe)){throw 'Could not extract the Tiled editor.'}
Write-Host 'Tiled is ready in the project .tools folder.'
