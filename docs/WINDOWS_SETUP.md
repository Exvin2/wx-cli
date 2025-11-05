# Windows Setup Guide for wx-cli

Complete guide for installing and using wx-cli (NWS AI Weather Bot) on Windows 10/11.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Windows-Specific Features](#windows-specific-features)
- [Configuration](#configuration)
- [Terminal Setup](#terminal-setup)
- [Troubleshooting](#troubleshooting)
- [Uninstallation](#uninstallation)

## Prerequisites

### Required
- **Windows 10** (version 1809+) or **Windows 11**
- **Python 3.11+** ([Download](https://www.python.org/downloads/))
  - During installation, check "Add Python to PATH"
  - Enable "Install pip" option
- **Windows Terminal** (recommended) or PowerShell 5.1+
  - Windows 11: Pre-installed
  - Windows 10: [Download from Microsoft Store](https://aka.ms/terminal)

### Recommended
- **Windows Terminal** for best experience with Rich formatting
- **Git for Windows** if cloning from repository
- Administrator privileges for scheduled tasks and system-wide features

## Installation

### Method 1: Automated PowerShell Installation (Recommended)

1. **Open PowerShell** (or Windows Terminal)
   - Press `Win + X` → Select "Windows Terminal" or "PowerShell"

2. **Navigate to wx-cli directory**
   ```powershell
   cd path\to\wx-cli
   ```

3. **Run installation script**
   ```powershell
   .\install.ps1
   ```

   The script will:
   - Check Python version (requires 3.11+)
   - Create a virtual environment
   - Install all dependencies
   - Set up your `.env` configuration file
   - Test the installation

4. **Activate virtual environment**
   ```powershell
   .\venv\Scripts\Activate.ps1
   ```

   **Note**: If you get an execution policy error, run:
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```

### Method 2: Manual Installation

1. **Create virtual environment**
   ```powershell
   python -m venv venv
   ```

2. **Activate virtual environment**
   ```powershell
   .\venv\Scripts\Activate.ps1
   ```

3. **Upgrade pip**
   ```powershell
   python -m pip install --upgrade pip
   ```

4. **Install wx-cli**
   ```powershell
   # For normal use
   pip install -e .

   # For development
   pip install -e .[dev]
   ```

5. **Configure environment**
   ```powershell
   Copy-Item .env.example .env
   notepad .env  # Edit with your API keys
   ```

### Verify Installation

```powershell
wx --help
wx "What's the weather in Seattle?"
```

## Windows-Specific Features

### 1. Desktop Toast Notifications

Get desktop notifications for severe weather alerts.

**Setup:**
```powershell
# Install notification dependencies
pip install win10toast plyer

# Enable notifications in your .env
echo "WX_NOTIFICATIONS=1" >> .env

# Test notifications
python -c "from wx.notifications_windows import test_notification; test_notification()"
```

**Usage:**
```powershell
# Monitor for severe weather with notifications
wx alerts "Oklahoma" --ai --notify

# Background monitoring (in Task Scheduler)
wx monitor --severe --notify
```

### 2. Task Scheduler Integration

Automate weather checks with Windows Task Scheduler.

**Setup:**
```powershell
# Run the setup script (requires Administrator)
.\scripts\setup-scheduled-task.ps1
```

**Options during setup:**
- Morning weather briefing (7:00 AM daily)
- Severe weather monitoring (every 30 minutes)
- Custom schedule

**Manual Task Creation:**
1. Open Task Scheduler (`taskschd.msc`)
2. Create Basic Task → Name it "wx Morning Weather"
3. Trigger: Daily at 7:00 AM
4. Action: Start a program
   - Program: `path\to\wx-cli\venv\Scripts\python.exe`
   - Arguments: `-m wx forecast "Your City" --notify`
   - Start in: `path\to\wx-cli`

### 3. Configuration GUI Wizard

User-friendly graphical interface for configuration (no command-line needed).

**Launch:**
```powershell
python wx\config_wizard.py
```

**Features:**
- Visual API key input with validation
- Unit selection (Imperial/Metric)
- Privacy mode toggle
- Test connection button
- Auto-saves to `.env` file

### 4. System Tray Integration

Keep wx running in the system tray for instant weather updates.

**Setup:**
```powershell
# Install tray dependencies
pip install pystray pillow

# Run in system tray mode
python wx\tray_app.py
```

**Features:**
- Right-click for quick weather check
- Severe weather popup alerts
- Exit option in tray menu

## Configuration

### Environment Variables

Edit your `.env` file:

```env
# Required: API Keys
OPENROUTER_API_KEY=sk-or-v1-your-key-here
GEMINI_API_KEY=your-gemini-key-here

# Optional: Preferences
UNITS=imperial                 # or metric
PRIVACY_MODE=1                 # 1 = no history, 0 = enable history
WX_NOTIFICATIONS=1             # Enable Windows notifications
AI_TEMPERATURE=0.2
AI_MAX_TOKENS=900

# NWS API (free, no key needed - uses User-Agent header)
NWS_CONTACT_EMAIL=your@email.com   # Optional: for NWS User-Agent identification

# Windows-specific
WX_STATE_DIR=%USERPROFILE%\.cache\wx
```

### File Locations on Windows

| Purpose | Location |
|---------|----------|
| Configuration | `%USERPROFILE%\.cache\wx\` |
| Virtual environment | `.\venv\` |
| Environment file | `.\.env` |
| Logs (if enabled) | `%TEMP%\wx-cli\logs\` |

### Permissions

wx-cli automatically handles Windows file permissions:
- Cache files use Windows ACLs (Access Control Lists)
- Only your user account has read/write access
- No special permissions needed for basic usage
- Administrator rights required only for Task Scheduler setup

## Terminal Setup

### Windows Terminal (Recommended)

**Install:**
```powershell
# From Microsoft Store
winget install Microsoft.WindowsTerminal
```

**Configure for wx-cli:**

1. Open Windows Terminal Settings (`Ctrl + ,`)
2. Add a new profile:

```json
{
    "name": "wx Weather Bot",
    "commandline": "powershell.exe -NoExit -Command \"cd '%USERPROFILE%\\wx-cli'; .\\venv\\Scripts\\Activate.ps1\"",
    "icon": "🌤️",
    "colorScheme": "One Half Dark",
    "startingDirectory": "%USERPROFILE%\\wx-cli"
}
```

3. Save and select the new profile from the dropdown

**Custom Color Scheme:**

Add to `settings.json` under `schemes`:

```json
{
    "name": "wx Weather",
    "background": "#1a1a2e",
    "foreground": "#eaeaea",
    "black": "#1a1a2e",
    "blue": "#5eb3f6",
    "cyan": "#73e0ff",
    "green": "#a5e075",
    "purple": "#c47fd5",
    "red": "#f06c62",
    "white": "#eaeaea",
    "yellow": "#f0ce85",
    "brightBlack": "#686868",
    "brightBlue": "#5eb3f6",
    "brightCyan": "#73e0ff",
    "brightGreen": "#a5e075",
    "brightPurple": "#c47fd5",
    "brightRed": "#f06c62",
    "brightWhite": "#ffffff",
    "brightYellow": "#f0ce85"
}
```

### PowerShell Configuration

Add to your PowerShell profile for quick access:

```powershell
# Open profile
notepad $PROFILE

# Add these lines:
function wx-activate {
    Set-Location "C:\path\to\wx-cli"
    .\venv\Scripts\Activate.ps1
}

Set-Alias weather wx-activate
```

Then reload: `. $PROFILE`

## Troubleshooting

### Common Issues

#### "wx command not found"

**Solution:**
```powershell
# Activate virtual environment first
.\venv\Scripts\Activate.ps1

# Or use full path
.\venv\Scripts\wx.exe
```

#### "Execution Policy" Error

**Problem:**
```
.\install.ps1 : File cannot be loaded because running scripts is disabled
```

**Solution:**
```powershell
# Allow scripts for current user
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Or run with bypass (one-time)
PowerShell -ExecutionPolicy Bypass -File .\install.ps1
```

#### "Python not found"

**Solution:**
1. Download Python from [python.org](https://www.python.org/downloads/)
2. During install, check "Add Python to PATH"
3. Restart PowerShell
4. Verify: `python --version`

#### Rich Formatting Issues in CMD.exe

**Problem:** Garbled output or missing colors in legacy Command Prompt

**Solution:**
- Use Windows Terminal instead of CMD.exe
- Or use PowerShell 5.1+
- Legacy CMD.exe is not fully supported

#### Toast Notifications Not Working

**Solution:**
```powershell
# Check notification settings
ms-settings:notifications

# Ensure Python is allowed to show notifications
# Settings → System → Notifications → Python

# Test notifications
python -c "from win10toast import ToastNotifier; ToastNotifier().show_toast('Test', 'Working!')"
```

#### API Key Validation Warnings

**Problem:**
```
Warning: OPENROUTER_API_KEY appears to be too short
```

**Solution:**
- Ensure you copied the complete API key
- Check for extra spaces or line breaks
- Keys should be 20+ characters
- Avoid placeholder values like "your_api_key_here"

#### Virtual Environment Not Activating

**Solution:**
```powershell
# Recreate virtual environment
Remove-Item -Recurse -Force venv
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -e .
```

### Windows Defender / Antivirus Issues

If Windows Defender blocks `wx.exe`:

1. Open Windows Security
2. Virus & threat protection → Manage settings
3. Add exclusion → Folder
4. Add: `C:\path\to\wx-cli\venv\Scripts\`

### Firewall Configuration

wx-cli needs internet access for weather data:

1. Windows Firewall → Allow an app
2. Browse to: `venv\Scripts\python.exe`
3. Allow Private and Public networks

## Uninstallation

### Remove wx-cli

```powershell
# Deactivate virtual environment
deactivate

# Remove virtual environment
Remove-Item -Recurse -Force venv

# Remove configuration
Remove-Item -Recurse -Force $env:USERPROFILE\.cache\wx
Remove-Item .env

# Remove scheduled tasks (if created)
schtasks /delete /tn "wx Morning Weather" /f
schtasks /delete /tn "wx Severe Weather Monitor" /f
```

### Clean Uninstall

```powershell
# Run uninstall script
.\scripts\uninstall.ps1
```

## Advanced Usage

### Running as Windows Service

For continuous severe weather monitoring:

```powershell
# Install pywin32
pip install pywin32

# Install service
python wx\service.py install

# Start service
sc start wxWeatherService

# Stop service
sc stop wxWeatherService

# Uninstall service
python wx\service.py remove
```

### Integration with Windows Context Menu

Add "Check Weather Here" to right-click menu:

```powershell
# Run as Administrator
.\scripts\add-context-menu.ps1

# Now right-click any location in a text document or browser
# Select "Check Weather Here" → wx opens with that location
```

### Desktop Widgets

Pin wx output to desktop using PowerShell widgets or Rainmeter:

See: `docs\DESKTOP_WIDGET.md` (coming soon)

## Performance Tips

### Faster Startup

Add to `.env`:
```env
# Skip unnecessary checks
WX_FAST_START=1

# Use Gemini instead of OpenRouter (faster for some users)
PREFER_GEMINI=1
```

### Reduce Network Usage

```env
# Cache weather data longer (seconds)
WX_CACHE_TTL=1800

# Disable non-essential fetchers
WX_TRUST_TOOLS=0
```

## Getting Help

- **Documentation:** [README.md](../README.md)
- **Issues:** Report Windows-specific issues on GitHub
- **Discord/Slack:** (if available - add link)

## Credits

wx-cli is built with:
- Python 3.11+
- Typer (CLI framework)
- Rich (terminal formatting)
- httpx (HTTP client)
- OpenRouter API (AI routing)
- Google Gemini (AI fallback)
- NWS/NOAA (weather data)

Windows-specific features use:
- win10toast (desktop notifications)
- pywin32 (Windows services)
- pystray (system tray integration)

---

**Last Updated:** 2025-11-05
**wx-cli Version:** 0.1.0
**Windows Support:** Windows 10 (1809+), Windows 11
