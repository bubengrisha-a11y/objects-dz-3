<#
Загружает расширение СчетаМагазина из исходников репозитория в базу, обновляет его
в базе данных и выгружает в СчетаМагазина.cfe в корне репозитория.
Запускать на компьютере с платформой 1С; Конфигуратор этой базы должен быть закрыт.

  tools\load-extension.cmd -InfoBase C:\1C\bsp-demo
  tools\load-extension.cmd -InfoBase C:\1C\bsp-demo -User Администратор -Password ""
  tools\load-extension.cmd -InfoBase C:\1C\bsp-demo -Platform "C:\Program Files\1cv8\8.5.1.960\bin\1cv8.exe"
#>
param(
    [string]$InfoBase = "C:\1C\bsp-demo",
    [string]$User = "Администратор",
    [string]$Password = "",
    [string]$Platform = ""
)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Extension = "СчетаМагазина"
$Source = Join-Path $Root "src\extensions\$Extension"
$Cfe = Join-Path $Root "$Extension.cfe"
$Log = Join-Path $PSScriptRoot "load-extension.log"

if (-not $Platform) {
    $Platform = Get-ChildItem "$env:ProgramFiles\1cv8\8.*\bin\1cv8.exe" -ErrorAction SilentlyContinue |
        Sort-Object { [version]$_.Directory.Parent.Name } |
        Select-Object -Last 1 -ExpandProperty FullName
}
if (-not $Platform -or -not (Test-Path $Platform)) {
    throw "Не найден 1cv8.exe: укажите путь параметром -Platform"
}

function Invoke-Designer([string]$Step, [string[]]$Arguments) {
    $all = @("DESIGNER", "/F", $InfoBase, "/N", $User, "/P", $Password,
        "/DisableStartupDialogs", "/DisableStartupMessages", "/Out", $Log) + $Arguments
    $line = ($all | ForEach-Object { '"' + $_ + '"' }) -join " "
    Write-Host "== $Step"
    $process = Start-Process -FilePath $Platform -ArgumentList $line -Wait -PassThru -NoNewWindow
    if (Test-Path $Log) { Get-Content $Log | Write-Host }
    if ($process.ExitCode -ne 0) {
        throw "${Step}: Конфигуратор завершился с кодом $($process.ExitCode), подробности — в $Log"
    }
}

Write-Host "Платформа: $Platform"
Write-Host "База: $InfoBase"
Invoke-Designer "Загрузка исходников и обновление расширения в базе" @(
    "/LoadConfigFromFiles", $Source, "-Extension", $Extension, "/UpdateDBCfg", "-Extension", $Extension)
Invoke-Designer "Выгрузка расширения в $Cfe" @("/DumpCfg", $Cfe, "-Extension", $Extension)
Write-Host "Готово: расширение загружено и выгружено в $Cfe. Отправьте запросы из src\tests\objects.http."
