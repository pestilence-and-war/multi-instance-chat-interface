# =========================================================================
#  Utility Script: Fix-Project-Permissions.ps1 (Comprehensive Version)
# =========================================================================
#
# This script configures all necessary permissions for the JeaToolUser account.
# It MUST be run from the project's root directory with Administrator privileges.
#
# It performs two critical operations:
#   1. Grants MODIFY access to the project folder itself, allowing the user
#      to run the application code and write necessary log files.
#   2. Grants FULL CONTROL over the sandboxed workspace directory, allowing
#      the sandboxed tools to freely create, edit, and delete files/folders.
#
# =========================================================================

try {
    # --- Configuration ---
    $userName = "JeaToolUser"
    $projectRoot = (Get-Location).Path
    $sandboxedWorkspacePath = "C:\SandboxedWorkspaces" # This path MUST match the one created by Setup-Simple-Sandbox.ps1

    # --- Verification ---
    if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw "This script must be run as an Administrator. Please right-click the PowerShell icon and choose 'Run as Administrator', then navigate to the project directory and re-run this script."
    }

    # --- STEP 1: Set Permissions for the Project/Application Directory ---
    Write-Host "STEP 1: Applying permissions for the application directory..." -ForegroundColor Yellow
    Write-Host "  Target User:   $userName"
    Write-Host "  Project Path:  $projectRoot"
    Write-Host "  Permissions:   Modify (Read, Write, Execute, Delete)"
    
    # Granting Modify (M) with Object Inherit (OI) and Container Inherit (CI).
    # The /T flag traverses all subdirectories. /Q suppresses verbose output for each file.
    icacls $projectRoot /grant "$userName`:(OI)(CI)M" /T /Q

    Write-Host "[SUCCESS] Project folder permissions applied." -ForegroundColor Green
    Write-Host ("-"*70)


    # --- STEP 2: Set Permissions for the Sandboxed Workspace Directory ---
    Write-Host "STEP 2: Applying permissions for the Sandboxed Workspace..." -ForegroundColor Yellow
    
    # Verify the sandbox directory exists before attempting to set permissions.
    if (Test-Path $sandboxedWorkspacePath -PathType Container) {
        Write-Host "  Target User:    $userName"
        Write-Host "  Sandbox Path:   $sandboxedWorkspacePath"
        Write-Host "  Permissions:    Full Control"

        # Granting Full Control (F) with Object Inherit (OI) and Container Inherit (CI).
        # This gives the user complete and unrestricted control over everything inside this folder.
        icacls $sandboxedWorkspacePath /grant "$userName`:(OI)(CI)F" /T /Q

        Write-Host "[SUCCESS] Sandboxed Workspace permissions applied." -ForegroundColor Green
    } else {
        throw "The directory '$sandboxedWorkspacePath' was not found! Please run the 'Setup-Simple-Sandbox.ps1' script first to create the user and the jailed directory."
    }
    
    Write-Host ("-"*70)
    Write-Host "All permissions have been successfully set." -ForegroundColor Cyan
    Write-Host "You may now run the application using 'run_app_as_jea_user.bat'." -ForegroundColor Cyan

}
catch {
    Write-Host "[FATAL ERROR] An error occurred during the setup." -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
}

Read-Host -Prompt "Press Enter to exit"