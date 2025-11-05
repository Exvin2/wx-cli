<#
.SYNOPSIS
    Sets up Windows Task Scheduler tasks for automated weather checks

.DESCRIPTION
    Creates scheduled tasks for wx-cli:
    - Morning weather briefing (daily at 7:00 AM)
    - Severe weather monitoring (every 30 minutes)
    - Custom schedules

    Requires Administrator privileges to create scheduled tasks.

.PARAMETER TaskType
    Type of task to create: "morning", "severe", "custom", or "all"

.PARAMETER Location
    Default location for weather checks

.EXAMPLE
    .\setup-scheduled-task.ps1 -TaskType morning -Location "Seattle, WA"

.EXAMPLE
    .\setup-scheduled-task.ps1 -TaskType all
#>

[CmdletBinding()]
param(
    [Parameter()]
    [ValidateSet("morning", "severe", "custom", "all")]
    [string]$TaskType = "interactive",

    [Parameter()]
    [string]$Location = "",

    [Parameter()]
    [switch]$Remove
)

$ErrorActionPreference = "Stop"

# Colors
function Write-Success { param($Message) Write-Host $Message -ForegroundColor Green }
function Write-Error { param($Message) Write-Host $Message -ForegroundColor Red }
function Write-Info { param($Message) Write-Host $Message -ForegroundColor Cyan }
function Write-Warning { param($Message) Write-Host $Message -ForegroundColor Yellow }

# Check if running as Administrator
function Test-Administrator {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

Write-Info "================================================"
Write-Info "  wx-cli Task Scheduler Setup"
Write-Info "================================================"
Write-Host ""

if (-not (Test-Administrator)) {
    Write-Error "This script requires Administrator privileges."
    Write-Info "Please run PowerShell as Administrator and try again."
    Write-Host ""
    Write-Info "To run as Administrator:"
    Write-Info "  1. Right-click PowerShell in Start Menu"
    Write-Info "  2. Select 'Run as Administrator'"
    Write-Info "  3. Navigate to wx-cli directory"
    Write-Info "  4. Run: .\scripts\setup-scheduled-task.ps1"
    exit 1
}

# Get wx-cli installation path
$wxCliPath = Get-Location
$pythonPath = Join-Path $wxCliPath "venv\Scripts\python.exe"
$wxExePath = Join-Path $wxCliPath "venv\Scripts\wx.exe"

# Verify installation
if (-not (Test-Path $pythonPath) -and -not (Test-Path $wxExePath)) {
    Write-Error "wx-cli installation not found."
    Write-Info "Please run install.ps1 first to set up wx-cli."
    exit 1
}

# Use wx.exe if available, otherwise use python -m wx
if (Test-Path $wxExePath) {
    $wxCommand = $wxExePath
} else {
    $wxCommand = $pythonPath
    $wxCommandArgs = "-m wx"
}

# Interactive mode
if ($TaskType -eq "interactive") {
    Write-Info "What type of scheduled task would you like to create?"
    Write-Host ""
    Write-Host "  1. Morning weather briefing (daily at 7:00 AM)"
    Write-Host "  2. Severe weather monitoring (every 30 minutes)"
    Write-Host "  3. Custom schedule"
    Write-Host "  4. All of the above"
    Write-Host "  5. Remove existing tasks"
    Write-Host ""

    $choice = Read-Host "Enter your choice (1-5)"

    switch ($choice) {
        "1" { $TaskType = "morning" }
        "2" { $TaskType = "severe" }
        "3" { $TaskType = "custom" }
        "4" { $TaskType = "all" }
        "5" {
            $Remove = $true
            $TaskType = "all"
        }
        default {
            Write-Error "Invalid choice. Exiting."
            exit 1
        }
    }
}

# Get location if not provided
if ([string]::IsNullOrWhiteSpace($Location) -and -not $Remove) {
    Write-Host ""
    $Location = Read-Host "Enter your default location (e.g., 'Seattle, WA', or press Enter for 'Current Location')"
    if ([string]::IsNullOrWhiteSpace($Location)) {
        $Location = "Current Location"
    }
}

# Remove tasks
if ($Remove) {
    Write-Info "Removing existing wx-cli scheduled tasks..."
    Write-Host ""

    $tasks = @(
        "wx Morning Weather Briefing",
        "wx Severe Weather Monitor",
        "wx Custom Weather Check"
    )

    foreach ($taskName in $tasks) {
        try {
            $task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
            if ($task) {
                Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
                Write-Success "  Removed: $taskName"
            }
        } catch {
            Write-Warning "  Could not remove: $taskName"
        }
    }

    Write-Host ""
    Write-Success "Task removal complete."
    exit 0
}

# Create Morning Weather Briefing task
function New-MorningBriefingTask {
    Write-Info "Creating morning weather briefing task..."

    $taskName = "wx Morning Weather Briefing"
    $taskDescription = "Daily weather briefing for $Location at 7:00 AM"

    # Task action
    if ($wxCommand -match "wx.exe") {
        $action = New-ScheduledTaskAction -Execute $wxCommand `
            -Argument "forecast `"$Location`" --trust-tools" `
            -WorkingDirectory $wxCliPath
    } else {
        $action = New-ScheduledTaskAction -Execute $wxCommand `
            -Argument "$wxCommandArgs forecast `"$Location`" --trust-tools" `
            -WorkingDirectory $wxCliPath
    }

    # Trigger: Daily at 7:00 AM
    $trigger = New-ScheduledTaskTrigger -Daily -At 7:00AM

    # Settings
    $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd

    # Register task
    try {
        Register-ScheduledTask -TaskName $taskName `
            -Description $taskDescription `
            -Action $action `
            -Trigger $trigger `
            -Settings $settings `
            -User $env:USERNAME `
            -Force | Out-Null

        Write-Success "  ✓ Morning briefing task created (runs daily at 7:00 AM)"
    } catch {
        Write-Error "  ✗ Failed to create morning briefing task: $_"
    }
}

# Create Severe Weather Monitor task
function New-SevereWeatherMonitorTask {
    Write-Info "Creating severe weather monitor task..."

    $taskName = "wx Severe Weather Monitor"
    $taskDescription = "Monitor severe weather alerts every 30 minutes"

    # Task action
    if ($wxCommand -match "wx.exe") {
        $action = New-ScheduledTaskAction -Execute $wxCommand `
            -Argument "alerts `"$Location`" --severe --ai" `
            -WorkingDirectory $wxCliPath
    } else {
        $action = New-ScheduledTaskAction -Execute $wxCommand `
            -Argument "$wxCommandArgs alerts `"$Location`" --severe --ai" `
            -WorkingDirectory $wxCliPath
    }

    # Trigger: Every 30 minutes
    $trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 30)

    # Settings
    $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd

    # Register task
    try {
        Register-ScheduledTask -TaskName $taskName `
            -Description $taskDescription `
            -Action $action `
            -Trigger $trigger `
            -Settings $settings `
            -User $env:USERNAME `
            -Force | Out-Null

        Write-Success "  ✓ Severe weather monitor created (runs every 30 minutes)"
    } catch {
        Write-Error "  ✗ Failed to create severe weather monitor: $_"
    }
}

# Create Custom task
function New-CustomTask {
    Write-Info "Creating custom weather check task..."
    Write-Host ""

    # Get custom settings
    $taskName = Read-Host "Task name (default: 'wx Custom Weather Check')"
    if ([string]::IsNullOrWhiteSpace($taskName)) {
        $taskName = "wx Custom Weather Check"
    }

    Write-Host ""
    Write-Info "Select schedule type:"
    Write-Host "  1. Daily"
    Write-Host "  2. Weekly"
    Write-Host "  3. Hourly"
    $scheduleChoice = Read-Host "Enter choice (1-3)"

    switch ($scheduleChoice) {
        "1" {
            $time = Read-Host "Enter time (e.g., 9:00AM)"
            $trigger = New-ScheduledTaskTrigger -Daily -At $time
        }
        "2" {
            $time = Read-Host "Enter time (e.g., 9:00AM)"
            $day = Read-Host "Enter day (Monday, Tuesday, etc.)"
            $trigger = New-ScheduledTaskTrigger -Weekly -At $time -DaysOfWeek $day
        }
        "3" {
            $hours = Read-Host "Enter interval in hours (e.g., 2)"
            $trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Hours $hours)
        }
        default {
            Write-Error "Invalid choice."
            return
        }
    }

    Write-Host ""
    $command = Read-Host "Enter wx command (e.g., 'forecast Seattle' or 'risk Miami --hazards wind')"

    # Task action
    if ($wxCommand -match "wx.exe") {
        $action = New-ScheduledTaskAction -Execute $wxCommand `
            -Argument $command `
            -WorkingDirectory $wxCliPath
    } else {
        $action = New-ScheduledTaskAction -Execute $wxCommand `
            -Argument "$wxCommandArgs $command" `
            -WorkingDirectory $wxCliPath
    }

    # Settings
    $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd

    # Register task
    try {
        Register-ScheduledTask -TaskName $taskName `
            -Description "Custom wx weather check: $command" `
            -Action $action `
            -Trigger $trigger `
            -Settings $settings `
            -User $env:USERNAME `
            -Force | Out-Null

        Write-Success "  ✓ Custom task created: $taskName"
    } catch {
        Write-Error "  ✗ Failed to create custom task: $_"
    }
}

# Create tasks based on selection
Write-Host ""

if ($TaskType -eq "morning" -or $TaskType -eq "all") {
    New-MorningBriefingTask
    Write-Host ""
}

if ($TaskType -eq "severe" -or $TaskType -eq "all") {
    New-SevereWeatherMonitorTask
    Write-Host ""
}

if ($TaskType -eq "custom") {
    New-CustomTask
    Write-Host ""
}

# Success summary
Write-Success "================================================"
Write-Success "  Task Scheduler setup complete!"
Write-Success "================================================"
Write-Host ""
Write-Info "Your scheduled tasks have been created."
Write-Host ""
Write-Info "To manage your tasks:"
Write-Host "  1. Open Task Scheduler (taskschd.msc)"
Write-Host "  2. Navigate to Task Scheduler Library"
Write-Host "  3. Find tasks starting with 'wx'"
Write-Host ""
Write-Info "To test a task immediately:"
Write-Host "  Run: " -NoNewline
Write-Host "Start-ScheduledTask -TaskName 'wx Morning Weather Briefing'" -ForegroundColor Yellow
Write-Host ""
Write-Info "To remove tasks later:"
Write-Host "  Run: " -NoNewline
Write-Host ".\scripts\setup-scheduled-task.ps1 -Remove" -ForegroundColor Yellow
Write-Host ""

# Offer to enable notifications
Write-Host ""
$enableNotifications = Read-Host "Would you like to enable desktop notifications for these tasks? (y/n)"
if ($enableNotifications -match "^[Yy]") {
    if (Test-Path ".env") {
        $envContent = Get-Content ".env"
        if ($envContent -notmatch "WX_NOTIFICATIONS=") {
            Add-Content -Path ".env" -Value "`nWX_NOTIFICATIONS=1"
            Write-Success "  ✓ Notifications enabled in .env"
        } else {
            $envContent = $envContent -replace "WX_NOTIFICATIONS=0", "WX_NOTIFICATIONS=1"
            $envContent | Set-Content ".env"
            Write-Success "  ✓ Notifications enabled in .env"
        }

        Write-Info ""
        Write-Info "To install notification support:"
        Write-Host "  pip install win10toast"
    }
}

Write-Host ""
