$root='C:\Users\User\Desktop\ai'
$d=Join-Path $root (-join ([char[]](25968,25454,38598,95,33033,20914,36127,36733)))
$s=Join-Path $d 'support700'
$started111=$false;$started112=$false
while(-not($started111 -and $started112)){
 foreach($pair in @(@(205,211,11),@(106,212,12))){
  $already=if($pair[1] -eq 211){$started111}else{$started112};if($already){continue}
  try{$st=Get-Content -LiteralPath (Join-Path $s ('worker_'+$pair[0]+'\status.json')) -Raw|ConvertFrom-Json
   if($st.completed_or_skipped -ge 58){
    $arg='-NoProfile -ExecutionPolicy Bypass -File "'+(Join-Path $s 'launch_memory.ps1')+'" -worker '+$pair[1]+' -first '+$pair[2]
    Start-Process powershell.exe -ArgumentList $arg -WindowStyle Hidden
    if($pair[1] -eq 211){$started111=$true}else{$started112=$true}
   }
  }catch{}
 }
 Start-Sleep -Seconds 20
}

