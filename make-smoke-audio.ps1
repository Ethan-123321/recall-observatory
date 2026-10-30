$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Speech
$taskSynth = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
    $taskVoice = $taskSynth.GetInstalledVoices() | Where-Object { $_.Enabled -and $_.VoiceInfo.Culture.Name -eq 'zh-CN' } | Select-Object -First 1
    if (-not $taskVoice) { throw 'No enabled zh-CN speech synthesis voice is available.' }
    $taskSynth.SelectVoice($taskVoice.VoiceInfo.Name)
    $taskOutput = Join-Path $PSScriptRoot 'tmp'
    New-Item -ItemType Directory -Path $taskOutput -Force | Out-Null
    $taskFormat = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(16000, [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, [System.Speech.AudioFormat.AudioChannel]::Mono)
    $taskSynth.SetOutputToWaveFile((Join-Path $taskOutput 'asr-smoke.wav'), $taskFormat)
    $taskSynth.Speak('只看二零二五年的玩具')
} finally { $taskSynth.Dispose() }
