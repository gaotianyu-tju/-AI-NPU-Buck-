$root='C:\Users\User\Desktop\ai'
$d=Join-Path $root (-join ([char[]](25968,25454,38598,95,33033,20914,36127,36733)))
$s=Join-Path $d 'support700'
$jobs=@()
for($first=1;$first -le 6;$first++){
 $p=Start-Process powershell.exe -ArgumentList ('-NoProfile -ExecutionPolicy Bypass -File "'+(Join-Path $s 'launch_fast.ps1')+'" -first '+$first) -WindowStyle Hidden -PassThru
 $jobs+=$p
}
$jobs|Select-Object Id|ConvertTo-Json|Set-Content -LiteralPath (Join-Path $s 'fast_launches.json')
foreach($job in $jobs){$job.WaitForExit()}
$env:TEMP=Join-Path $s 'final_temp';$env:TMP=$env:TEMP;$env:MATLAB_PREFDIR=Join-Path $s 'final_prefs'
New-Item -ItemType Directory -Path $env:TEMP,$env:MATLAB_PREFDIR -Force|Out-Null
$arg='-nosplash -nodesktop -singleCompThread -batch "cd(''C:\Users\User\Desktop\ai''); finish_ai700"'
Start-Process -FilePath 'C:\MATLAB\R2024b\bin\matlab.exe' -ArgumentList $arg -WindowStyle Hidden -RedirectStandardOutput (Join-Path $s 'final_console.log') -RedirectStandardError (Join-Path $s 'final_stderr.log') -Wait
$expected=(Get-Content -LiteralPath (Join-Path $s 'source_sha256.txt') -Raw).Trim();$actual=(Get-FileHash -LiteralPath (Join-Path $root 'buck_ADRC_fangzhen_AI_LADRC.slx')).Hash
('Original source hash unchanged: '+($expected -eq $actual))|Set-Content -LiteralPath (Join-Path $d 'source_integrity.txt')
