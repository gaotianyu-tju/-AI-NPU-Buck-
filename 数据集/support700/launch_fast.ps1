param([int]$first)
$root='C:\Users\User\Desktop\ai'
$d=Join-Path $root (-join ([char[]](25968,25454,38598,95,33033,20914,36127,36733)))
$s=Join-Path $d 'support700'
for($attempt=1;$attempt -le 2;$attempt++){
 $worker=300+$first+10*($attempt-1)
 $env:TEMP=Join-Path $s ('worker_'+$worker+'\temp');$env:TMP=$env:TEMP
 $env:MATLAB_PREFDIR=Join-Path $s ('worker_'+$worker+'\prefs')
 New-Item -ItemType Directory -Path $env:TEMP,$env:MATLAB_PREFDIR -Force|Out-Null
 $arg='-nosplash -nodesktop -singleCompThread -batch "cd(''C:\Users\User\Desktop\ai''); run_ai700_worker('+$worker+',1,'+$first+':6:700,''accelerator'')"'
 Start-Process -FilePath 'C:\MATLAB\R2024b\bin\matlab.exe' -ArgumentList $arg -WindowStyle Hidden -RedirectStandardOutput (Join-Path $s ('fast_'+$worker+'.log')) -RedirectStandardError (Join-Path $s ('fast_'+$worker+'_stderr.log')) -Wait
 try{$st=Get-Content -LiteralPath (Join-Path $s ('worker_'+$worker+'\status.json')) -Raw|ConvertFrom-Json;if($st.last_id -ge (700-5)){break}}catch{}
}
