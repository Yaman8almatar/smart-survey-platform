# PostToolUse hook: format an edited .dart file. Never blocks the edit.
$ErrorActionPreference = 'SilentlyContinue'

$payload = [Console]::In.ReadToEnd() | ConvertFrom-Json
$file = $payload.tool_input.file_path

if ($file -and $file.EndsWith('.dart')) {
    dart format $file *> $null
}

exit 0
