param([string]$MapFile='maps/dungeon_01.tmj')
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
$candidates=@((Join-Path $root '.tools/tiled/PFiles/Tiled/tiled.exe'),
    (Join-Path $env:ProgramFiles 'Tiled/tiled.exe'))
$command=Get-Command tiled.exe -ErrorAction SilentlyContinue
if($command){$candidates+= $command.Source}
$editor=$candidates|Where-Object{Test-Path -LiteralPath $_}|Select-Object -First 1
if(!$editor){& (Join-Path $PSScriptRoot 'setup_tiled.ps1');$editor=Join-Path $root '.tools/tiled/PFiles/Tiled/tiled.exe'}
$map=if([IO.Path]::IsPathRooted($MapFile)){$MapFile}else{Join-Path $root $MapFile}
if(!(Test-Path -LiteralPath $map)){throw ('Map not found: '+$map)}
$project=Join-Path $root 'maps/mercenary.tiled-project'
# This launches the interactive editor that the user will edit maps in.
Start-Process -FilePath $editor -ArgumentList @(('"'+$project+'"'),('"'+$map+'"')) -WorkingDirectory $root
