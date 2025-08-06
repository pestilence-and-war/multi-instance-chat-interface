# =========================================================================
#  Utility Script: Fix-Project-Permissions.ps1 (Final Version)
# =========================================================================

try {
    if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw "This script must be run as an Administrator. Please right-click it and choose 'Run with PowerShell'."
    }

    $userName = "JeaToolUser"
    $projectRoot = (Get-Location).Path

    Write-Host "Attempting to grant '$userName' MODIFY permissions on this project folder:" -ForegroundColor Yellow
    Write-Host "  $projectRoot" -ForegroundColor Yellow
    Write-Host "-----------------------------------------------------------------"

    # This is the critical change.
    # We are granting 'M' (Modify) instead of just 'RX' (Read & Execute).
    # This allows JeaToolUser to create, write, and delete files (like logs)
    # within your project directory.
    icacls $projectRoot /grant "$userName`:(OI)(CI)M" /T

    Write-Host "[SUCCESS] Permissions have been applied." -ForegroundColor Green
    Write-Host "The 'run_app_as_jea_user.bat' script should now work correctly." -ForegroundColor Cyan
}
catch {
    Write-Host "[FATAL ERROR] An error occurred while setting permissions." -ForegroundColor Red
    Write-Host "Full Error Details: $($_.Exception.Message)"
}

Read-Host -Prompt "Press Enter to exit"