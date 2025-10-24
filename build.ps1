# Build script for creating standalone executable with PyInstaller

Write-Host "Building mcp-server-dash standalone executable..." -ForegroundColor Green

# Use the virtual environment Python
$pythonExe = ".\.venv\Scripts\python.exe"

# Check if virtual environment exists
if (-not (Test-Path $pythonExe)) {
    Write-Host "Virtual environment not found at $pythonExe" -ForegroundColor Red
    Write-Host "Please create a virtual environment first: python -m venv .venv" -ForegroundColor Yellow
    exit 1
}

# Check if pyinstaller is installed
try {
    $pyinstallerVersion = & $pythonExe -m PyInstaller --version 2>&1
    Write-Host "PyInstaller version: $pyinstallerVersion" -ForegroundColor Cyan
} catch {
    Write-Host "PyInstaller not found. Installing..." -ForegroundColor Yellow
    & $pythonExe -m pip install pyinstaller
}

# Clean previous builds
if (Test-Path "build") {
    Write-Host "Cleaning build directory..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force "build"
}

if (Test-Path "dist") {
    Write-Host "Cleaning dist directory..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force "dist"
}

# Run PyInstaller
Write-Host "Running PyInstaller..." -ForegroundColor Cyan
& $pythonExe -m PyInstaller mcp-server-dash.spec

# Check if build was successful
if (Test-Path "dist\mcp-server-dash.exe") {
    Write-Host "`nBuild successful!" -ForegroundColor Green
    Write-Host "Executable location: dist\mcp-server-dash.exe" -ForegroundColor Green
    
    # Display file size
    $fileSize = (Get-Item "dist\mcp-server-dash.exe").Length / 1MB
    Write-Host ("Executable size: {0:N2} MB" -f $fileSize) -ForegroundColor Cyan
    
    Write-Host "`nTo use the executable:" -ForegroundColor Yellow
    Write-Host "1. Set APP_KEY environment variable or create .env file"
    Write-Host "2. Run: .\dist\mcp-server-dash.exe"
} else {
    Write-Host "`nBuild failed. Check the output above for errors." -ForegroundColor Red
    exit 1
}
