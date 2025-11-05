<#
.SYNOPSIS
    Windows installation script for wx-cli (NWS AI Weather Bot)

.DESCRIPTION
    This script automates the setup process for wx-cli on Windows:
    - Checks Python version (requires 3.11+)
    - Creates a virtual environment
    - Installs dependencies
    - Sets up .env configuration file
    - Optionally adds wx to PATH

.EXAMPLE
    .\install.ps1

.EXAMPLE
    .\install.ps1 -SkipVenv
#>

[CmdletBinding()]
param(
    [switch]$SkipVenv,
    [switch]$DevMode,
    [switch]$Quiet
)

$ErrorActionPreference = "Stop"

# Colors for output
function Write-Success { param($Message) Write-Host $Message -ForegroundColor Green }
function Write-Error { param($Message) Write-Host $Message -ForegroundColor Red }
function Write-Info { param($Message) Write-Host $Message -ForegroundColor Cyan }
function Write-Warning { param($Message) Write-Host $Message -ForegroundColor Yellow }

Write-Info "================================================"
Write-Info "  wx-cli (NWS AI Weather Bot) - Windows Setup"
Write-Info "================================================"
Write-Host ""

# Check if running in the correct directory
if (-not (Test-Path "pyproject.toml")) {
    Write-Error "Error: pyproject.toml not found. Please run this script from the wx-cli root directory."
    exit 1
}

# Step 1: Check Python version
Write-Info "[1/6] Checking Python installation..."
try {
    $pythonVersion = & python --version 2>&1
    if ($pythonVersion -match "Python (\d+)\.(\d+)\.(\d+)") {
        $major = [int]$matches[1]
        $minor = [int]$matches[2]

        if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 11)) {
            Write-Error "Python 3.11+ is required. Found: $pythonVersion"
            Write-Info "Download Python from: https://www.python.org/downloads/"
            exit 1
        }
        Write-Success "  Found: $pythonVersion"
    }
} catch {
    Write-Error "Python not found in PATH."
    Write-Info "Download Python from: https://www.python.org/downloads/"
    Write-Info "Make sure to check 'Add Python to PATH' during installation."
    exit 1
}

# Step 2: Create virtual environment (unless skipped)
if (-not $SkipVenv) {
    Write-Info "[2/6] Creating virtual environment..."
    if (Test-Path "venv") {
        Write-Warning "  Virtual environment already exists. Skipping creation."
    } else {
        & python -m venv venv
        Write-Success "  Virtual environment created."
    }

    # Activate virtual environment
    Write-Info "  Activating virtual environment..."
    $activateScript = ".\venv\Scripts\Activate.ps1"

    if (Test-Path $activateScript) {
        try {
            & $activateScript
            Write-Success "  Virtual environment activated."
        } catch {
            Write-Warning "  Could not activate venv automatically. You may need to run:"
            Write-Warning "  Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser"
            Write-Info "  Then manually activate: .\venv\Scripts\Activate.ps1"
        }
    }
} else {
    Write-Info "[2/6] Skipping virtual environment creation (--SkipVenv)"
}

# Step 3: Upgrade pip
Write-Info "[3/6] Upgrading pip..."
& python -m pip install --upgrade pip --quiet
Write-Success "  pip upgraded."

# Step 4: Install dependencies
Write-Info "[4/6] Installing dependencies..."
if ($DevMode) {
    Write-Info "  Installing with dev dependencies..."
    & python -m pip install -e ".[dev]" --quiet
} else {
    & python -m pip install -e . --quiet
}
Write-Success "  Dependencies installed."

# Step 5: Configure .env file
Write-Info "[5/6] Setting up .env configuration..."
if (Test-Path ".env") {
    Write-Warning "  .env file already exists. Skipping configuration."
} else {
    if ($Quiet) {
        # Just copy the example without prompting
        Copy-Item ".env.example" ".env"
        Write-Success "  Created .env from template. Please edit it with your API keys."
    } else {
        Write-Host ""
        Write-Info "  Let's set up your API keys..."
        Write-Host ""

        $setupEnv = Read-Host "  Do you want to set up your API keys now? (y/n)"

        if ($setupEnv -match "^[Yy]") {
            Write-Host ""
            Write-Info "  OpenRouter API Key (primary - for Grok/ChatGPT routing):"
            Write-Info "  Get your key at: https://openrouter.ai/keys"
            $openrouterKey = Read-Host "  Enter your OpenRouter API key (or press Enter to skip)"

            Write-Host ""
            Write-Info "  Gemini API Key (optional fallback):"
            Write-Info "  Get your key at: https://aistudio.google.com/app/apikey"
            $geminiKey = Read-Host "  Enter your Gemini API key (or press Enter to skip)"

            Write-Host ""
            $units = Read-Host "  Preferred units (imperial/metric) [imperial]"
            if ([string]::IsNullOrWhiteSpace($units)) { $units = "imperial" }

            # Create .env file
            $envContent = Get-Content ".env.example"
            $envContent = $envContent -replace "OPENROUTER_API_KEY=replace-with-your-openrouter-key", "OPENROUTER_API_KEY=$openrouterKey"
            $envContent = $envContent -replace "GEMINI_API_KEY=", "GEMINI_API_KEY=$geminiKey"
            $envContent = $envContent -replace "UNITS=imperial", "UNITS=$units"

            $envContent | Out-File -FilePath ".env" -Encoding utf8
            Write-Success "  .env file created with your settings."
        } else {
            Copy-Item ".env.example" ".env"
            Write-Success "  Created .env from template. Please edit it with your API keys later."
        }
    }
}

# Step 6: Test installation
Write-Info "[6/6] Testing installation..."
try {
    & wx --help > $null 2>&1
    Write-Success "  wx command is working!"
} catch {
    Write-Warning "  wx command not found in PATH."
    Write-Info "  You may need to activate the virtual environment first:"
    Write-Info "    .\venv\Scripts\Activate.ps1"
}

# Success message
Write-Host ""
Write-Success "================================================"
Write-Success "  Installation complete!"
Write-Success "================================================"
Write-Host ""
Write-Info "Quick Start:"
Write-Host "  1. Activate virtual environment: " -NoNewline
Write-Host ".\venv\Scripts\Activate.ps1" -ForegroundColor Yellow
Write-Host "  2. Edit your .env file with API keys (if not done already)"
Write-Host "  3. Start interactive chat: " -NoNewline
Write-Host "wx chat" -ForegroundColor Yellow
Write-Host "  4. Or ask a question: " -NoNewline
Write-Host 'wx "What is the weather in Seattle?"' -ForegroundColor Yellow
Write-Host ""
Write-Info "For Windows-specific features:"
Write-Host "  - Run " -NoNewline
Write-Host ".\setup-notifications.ps1" -ForegroundColor Yellow -NoNewline
Write-Host " for desktop notifications"
Write-Host "  - Run " -NoNewline
Write-Host ".\setup-scheduled-task.ps1" -ForegroundColor Yellow -NoNewline
Write-Host " for automated weather checks"
Write-Host "  - Run " -NoNewline
Write-Host "python wx\config_wizard.py" -ForegroundColor Yellow -NoNewline
Write-Host " for GUI configuration"
Write-Host ""
Write-Info "Documentation: README.md and docs/WINDOWS_SETUP.md"
Write-Host ""
