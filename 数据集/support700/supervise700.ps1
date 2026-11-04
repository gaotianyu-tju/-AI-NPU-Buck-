$root='C:\Users\User\Desktop\ai'
$d=Join-Path $root (-join ([char[]](25968,25454,38598,95,33033,20914,36127,36733)))
$s=Join-Path $d 'support700'
$deadline=(Get-Date).AddHours(12)
while((Get-Date) -lt $deadline){
 try{$st=Get-Content -LiteralPath (Join-Path $s 'worker_91\status.json') -Raw|ConvertFrom-Json;if($st.failures -gt 0){'Pilot failed; bulk launch withheld.'|Set-Content -LiteralPath (Join-Path $s 'blocked.txt');exit};if($st.completed_or_skipped -eq 3){break}}catch{}
 Start-Sleep -Seconds 10
}
$jobs=@()
for($w=1;$w -le 6;$w++){
 $arg='-nosplash -nodesktop -singleCompThread -batch "cd(''C:\Users\User\Desktop\ai''); run_ai700_worker('+$w+',6,[],''accelerator'')"'
 $p=Start-Process -FilePath 'C:\MATLAB\R2024b\bin\matlab.exe' -ArgumentList $arg -WindowStyle Hidden -RedirectStandardOutput (Join-Path $s ('console_'+$w+'.log')) -RedirectStandardError (Join-Path $s ('stderr_'+$w+'.log')) -PassThru
 $jobs+=[pscustomobject]@{worker=$w;pid=$p.Id}
}
$jobs|ConvertTo-Json|Set-Content -LiteralPath (Join-Path $s 'launched_processes.json')
while((Get-Date) -lt $deadline){
 $count=@(Get-ChildItem -LiteralPath $d -Filter 'P*.mat').Count
 if($count -eq 700){
  $arg='-nosplash -nodesktop -singleCompThread -batch "cd(''C:\Users\User\Desktop\ai''); audit_ai700"'
  Start-Process -FilePath 'C:\MATLAB\R2024b\bin\matlab.exe' -ArgumentList $arg -WindowStyle Hidden -RedirectStandardOutput (Join-Path $s 'audit_console.log') -RedirectStandardError (Join-Path $s 'audit_stderr.log') -Wait
  $expected=(Get-Content -LiteralPath (Join-Path $s 'source_sha256.txt') -Raw).Trim()
  $actual=(Get-FileHash -LiteralPath (Join-Path $root 'buck_ADRC_fangzhen_AI_LADRC.slx') -Algorithm SHA256).Hash
  ('Original source hash unchanged: '+($expected -eq $actual))|Set-Content -LiteralPath (Join-Path $d 'source_integrity.txt')
  exit
 }
 Start-Sleep -Seconds 30
}
'Batch incomplete after 12 hours; inspect logs.'|Set-Content -LiteralPath (Join-Path $s 'incomplete.txt')
