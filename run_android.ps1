param (
    [string]$AvdName = ""
)

$ErrorActionPreference = "Stop"

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "   AirKu Android Build & Run Script" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

# 1. Start Emulator (Jika diminta)
if ($AvdName -ne "") {
    Write-Host "`n[1/3] Menjalankan Emulator ($AvdName)..." -ForegroundColor Yellow
    # Menjalankan emulator di background
    Start-Process -NoNewWindow -FilePath "emulator" -ArgumentList "@$AvdName"
    
    Write-Host "Menunggu emulator siap (ini mungkin memakan waktu)..."
    # Looping tunggu emulator sampai 'bootanim' selesai
    do {
        Start-Sleep -Seconds 3
        $bootAnim = (adb shell getprop init.svc.bootanim 2>$null).Trim()
    } while ($bootAnim -ne "stopped")
    Write-Host "Emulator siap!" -ForegroundColor Green
} else {
    Write-Host "`n[1/3] Melewati peluncuran emulator (pastikan Anda sudah menyalakan emulator secara manual)." -ForegroundColor Yellow
}

# 2. Build APK
Write-Host "`n[2/3] Membangun APK (assembleDebug)..." -ForegroundColor Yellow
Push-Location android
try {
    .\gradlew assembleDebug
    Write-Host "Build Berhasil!" -ForegroundColor Green
} catch {
    Write-Host "Build gagal. Pastikan JAVA_HOME sudah dikonfigurasi dengan benar." -ForegroundColor Red
    Pop-Location
    exit
}
Pop-Location

# 3. Install dan Jalankan Aplikasi
Write-Host "`n[3/3] Menginstal APK ke Emulator..." -ForegroundColor Yellow
# Path default APK hasil build
$apkPath = "android\app\build\outputs\apk\debug\app-debug.apk"

if (Test-Path $apkPath) {
    # Install APK (-r untuk replace/update jika sudah ada)
    adb install -r $apkPath
    Write-Host "Install Berhasil!" -ForegroundColor Green
    
    Write-Host "`nMembuka Aplikasi AirKu di Emulator..." -ForegroundColor Yellow
    # Menjalankan aplikasi secara otomatis (Package: com.airkuapp)
    adb shell monkey -p com.airkuapp -c android.intent.category.LAUNCHER 1 > $null
    Write-Host "Selesai! Silakan cek emulator Anda." -ForegroundColor Green
} else {
    Write-Host "Gagal menemukan APK di $apkPath. Periksa kembali log build." -ForegroundColor Red
}
