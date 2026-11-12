# Offline Windows text-to-speech (System.Speech, the built-in "SAPI" voices). Free, no internet.
# Input: a JSON file [{ "path": "...wav", "text": "..." }, ...]. Output: one WAV file per item.
param([Parameter(Mandatory = $true)][string]$JsonPath)

Add-Type -AssemblyName System.Speech
$items = Get-Content -Raw -Encoding UTF8 $JsonPath | ConvertFrom-Json   # (PS 5.1 gives the whole list; foreach walks it)
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$synth.Rate = 1          # -10 slow ... 10 fast
foreach ($it in $items) {
    $synth.SetOutputToWaveFile($it.path)
    $synth.Speak($it.text)
    $synth.SetOutputToNull()
}
$synth.Dispose()
Write-Output ("TTS wrote {0} files" -f $items.Count)
