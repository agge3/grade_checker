# Check if winget is installed. If not, install.
$winget = Get-Command winget -ErrorAction SilentlyContinue
if (-not $winget) {
    Write-Host "winget is not installed. Installing winget..."
    Add-AppxPackage -RegisterByFamilyName -MainPackage Microsoft.DesktopAppInstaller_8wekyb3d8bbwe
}

# Check if git bash is installed. If not, install.
$git = Get-Command git -ErrorAction SilentlyContinue
if (-not $git) {
    Write-Host "git bash is not installed. Installing git bash..."
    winget install --id Git.Git -e --source winget
}

# Get the current user's profile directory.
$userProfile = $Env:USERPROFILE
$pythonPath = Join-Path $userProfile 'AppData\Local\Programs\Python\Python311\python.exe'

# Check if python3.11 is installed. If not, install.
$python = Get-Command $pythonPath -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Host "python3.11 is not installed. Installing python3.11..."
    winget install -e --id Python.Python.3.11
}

# Set up the virtual environment.
$projectPath = Get-Location  # Get the current directory path.
$venvPath = "$projectPath\.win-venv"

if (-not (Test-Path -Path $venvPath)) {
    Write-Host "Creating virtual environment at $venvPath"
    & $pythonPath -m venv $venvPath
} else {
    Write-Host "Virtual environment already exists at $venvPath"
}

# Get the virtual environment `Activate.ps1` script.
$activateScript = Join-Path $venvPath 'Scripts\Activate.ps1'

if (Test-Path -Path $activateScript) {
    Write-Host "Activating virtual environment..."
    . $activateScript
} else {
    Write-Host "Failed to find activation script for the virtual environment"
    exit 1
}

# Install dependencies (if any requirements file exists).
$requirementsFile = "$projectPath\requirements.txt"
if (Test-Path -Path $requirementsFile) {
    Write-Host "Installing dependencies from requirements.txt..."
    pip install -r $requirementsFile
}

# Run the Python script (main.py)/
$pythonScript = "$projectPath\main.py"
if (Test-Path -Path $pythonScript) {
    Write-Host "Running the Python script..."
    python $pythonScript
} else {
    Write-Host "main.py not found in the current directory."
    exit 1
}
