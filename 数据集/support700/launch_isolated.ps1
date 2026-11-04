param([int]$worker,[int]$first)
$root='C:\Users\User\Desktop\ai'
$d=Join-Path $root (-join ([char[]](25968,25454,38598,95,33033,20914,36127,36733)))
$s=Join-Path $d 'support700'
$env:TEMP=Join-Path $s ('worker_'+$worker+'\temp')
$env:TMP=$env:TEMP
$env:MATLAB_PREFDIR=Join-Path $s ('worker_'+$worker+'\prefs')
New-Item -ItemType Directory -Path $env:TEMP,$env:MATLAB_PREFDIR -Force | Out-Null
$arg='-nosplash -nodesktop -singleCompThread -batch "cd(''C:\Users\User\Desktop\ai''); run_ai700_worker('+$worker+',1,'+$first+':12:700,''accelerator'')"'
Start-Process -FilePath 'C:\MATLAB\R2024b\bin\matlab.exe' -ArgumentList $arg -WindowStyle Hidden -RedirectStandardOutput (Join-Path $s ('isolated_'+$worker+'.log')) -RedirectStandardError (Join-Path $s ('isolated_'+$worker+'_stderr.log')) -Wait
