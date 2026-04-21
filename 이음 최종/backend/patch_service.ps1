$content = Get-Content -Path 'D:\service\index.html' -Encoding utf8 -Raw
$content = $content -replace "fetch\('/api/", "fetch('/maeum/api/"
$content = $content -replace "fetch\('/chat", "fetch('/maeum/chat"
$content = $content -replace "fetch\('/analyze_sentiment", "fetch('/maeum/analyze_sentiment"
Set-Content -Path 'D:\service\index.html' -Value $content -Encoding utf8
Write-Host "Done - API paths updated to /maeum/ prefix"
