$files = git diff --name-only origin/main...HEAD

foreach ($file in $files) {
    if (Test-Path $file) {
        $bytes = [System.IO.File]::ReadAllBytes("$($PWD)\$file")
        if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
            $newBytes = New-Object byte[] ($bytes.Length - 3)
            [System.Array]::Copy($bytes, 3, $newBytes, 0, $newBytes.Length)
            [System.IO.File]::WriteAllBytes("$($PWD)\$file", $newBytes)
            Write-Host "Safely stripped BOM from $file without touching line endings."
        }
    }
}
Write-Host "Safe BOM cleanup complete."
