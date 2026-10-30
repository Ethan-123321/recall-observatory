param([string]$DatasetRoot=$PSScriptRoot,[string]$LedgerFile='review-image-ledger.json')
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null=[Windows.Storage.StorageFile,Windows.Storage,ContentType=WindowsRuntime]
$null=[Windows.Storage.Streams.IRandomAccessStream,Windows.Storage.Streams,ContentType=WindowsRuntime]
$null=[Windows.Graphics.Imaging.BitmapDecoder,Windows.Graphics.Imaging,ContentType=WindowsRuntime]
$null=[Windows.Graphics.Imaging.SoftwareBitmap,Windows.Graphics.Imaging,ContentType=WindowsRuntime]
$null=[Windows.Media.Ocr.OcrEngine,Windows.Foundation,ContentType=WindowsRuntime]
$null=[Windows.Media.Ocr.OcrResult,Windows.Foundation,ContentType=WindowsRuntime]
$null=[Windows.Globalization.Language,Windows.Globalization,ContentType=WindowsRuntime]
$asTask=([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {$_.Name -eq 'AsTask' -and $_.IsGenericMethod -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'})[0]
function Await($operation,[Type]$type){$t=$asTask.MakeGenericMethod($type).Invoke($null,@($operation));$t.Wait();$t.Result}
$engine=[Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage([Windows.Globalization.Language]::new('zh-Hans-CN'))
$out=Join-Path $DatasetRoot 'ocr-review';New-Item -ItemType Directory -Force -Path $out | Out-Null
$ledger=Get-Content -LiteralPath (Join-Path $DatasetRoot $LedgerFile) -Raw -Encoding UTF8 | ConvertFrom-Json
$i=0
foreach($r in $ledger){
 $i++;$target=Join-Path $out (([IO.Path]::GetFileName($r.file))+'.json')
 if(Test-Path -LiteralPath $target){continue}
 if($r.error){continue}
 try{
  $file=Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync((Join-Path $DatasetRoot $r.file))) ([Windows.Storage.StorageFile])
  $stream=Await ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
  $decoder=Await ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
  $bitmap=Await ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
  $result=Await ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])
  $value=@{id=$r.id;image=$r.file;sha256=$r.sha256;method='Windows local zh-Hans OCR; unreviewed transcription';text=$result.Text;lines=@($result.Lines | ForEach-Object {$_.Text})}
  $value | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $target -Encoding UTF8
  $bitmap.Dispose();$stream.Dispose()
 }catch{Write-Output ('ERROR '+$r.id+' '+$_.Exception.ToString());break}
 if($i%20 -eq 0){Write-Output ('OCR '+$i+'/'+$ledger.Count)}
}
