# FFmpeg 自動下載和安裝腳本
# 適用於 Windows

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  FFmpeg 自動安裝程式" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 設定路徑
$ffmpegDir = "$PSScriptRoot\ffmpeg"
$ffmpegBinDir = "$ffmpegDir\bin"
$downloadUrl = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
$zipFile = "$PSScriptRoot\ffmpeg.zip"

# 檢查是否已安裝
if (Test-Path "$ffmpegBinDir\ffmpeg.exe") {
    Write-Host "✅ FFmpeg 已經安裝在: $ffmpegBinDir" -ForegroundColor Green
    Write-Host ""
    & "$ffmpegBinDir\ffmpeg.exe" -version | Select-Object -First 1
    Write-Host ""
    
    $response = Read-Host "是否要重新安裝？(y/N)"
    if ($response -ne "y" -and $response -ne "Y") {
        Write-Host "保持現有安裝。" -ForegroundColor Yellow
        exit 0
    }
}

Write-Host "📥 開始下載 FFmpeg..." -ForegroundColor Yellow
Write-Host "來源: $downloadUrl" -ForegroundColor Gray
Write-Host ""

try {
    # 下載 FFmpeg
    Invoke-WebRequest -Uri $downloadUrl -OutFile $zipFile -UseBasicParsing
    Write-Host "✅ 下載完成！" -ForegroundColor Green
    
    # 解壓縮
    Write-Host "📦 正在解壓縮..." -ForegroundColor Yellow
    
    # 刪除舊的資料夾
    if (Test-Path $ffmpegDir) {
        Remove-Item -Path $ffmpegDir -Recurse -Force
    }
    
    # 解壓縮
    Expand-Archive -Path $zipFile -DestinationPath $PSScriptRoot -Force
    
    # 重新命名資料夾
    $extractedFolder = Get-ChildItem -Path $PSScriptRoot -Directory -Filter "ffmpeg-*" | Select-Object -First 1
    if ($extractedFolder) {
        Rename-Item -Path $extractedFolder.FullName -NewName "ffmpeg"
    }
    
    Write-Host "✅ 解壓縮完成！" -ForegroundColor Green
    
    # 清理 zip 檔案
    Remove-Item -Path $zipFile -Force
    
    # 驗證安裝
    if (Test-Path "$ffmpegBinDir\ffmpeg.exe") {
        Write-Host ""
        Write-Host "✅ FFmpeg 安裝成功！" -ForegroundColor Green
        Write-Host "📁 安裝位置: $ffmpegBinDir" -ForegroundColor Cyan
        Write-Host ""
        
        # 顯示版本
        & "$ffmpegBinDir\ffmpeg.exe" -version | Select-Object -First 1
        Write-Host ""
        
        Write-Host "========================================" -ForegroundColor Cyan
        Write-Host "✨ 安裝完成！" -ForegroundColor Green
        Write-Host ""
        Write-Host "下一步：執行音檔生成" -ForegroundColor Yellow
        Write-Host "  python tools/generate_audio.py" -ForegroundColor White
        Write-Host "========================================" -ForegroundColor Cyan
        
    } else {
        throw "無法找到 ffmpeg.exe"
    }
    
} catch {
    Write-Host ""
    Write-Host "❌ 安裝失敗: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "請手動下載 FFmpeg：" -ForegroundColor Yellow
    Write-Host "1. 前往: https://www.gyan.dev/ffmpeg/builds/" -ForegroundColor White
    Write-Host "2. 下載: ffmpeg-release-essentials.zip" -ForegroundColor White
    Write-Host "3. 解壓到專案資料夾並命名為 'ffmpeg'" -ForegroundColor White
    exit 1
}



