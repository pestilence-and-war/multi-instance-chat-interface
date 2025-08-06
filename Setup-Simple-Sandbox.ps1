# =========================================================================
#  Simple Sandbox Setup Script (Final Version)
#
#  This script sets up the minimal, robust environment needed for the
#  sandboxed tools. It does NOT use JEA or WinRM.
#
#  It performs three essential actions:
#  1. Creates the dedicated, low-privilege 'JeaToolUser' account.
#  2. Creates the 'C:\SandboxedWorkspaces' directory.
#  3. Applies strict file system permissions to that directory,
#     isolating it from the rest of the system.
#
#  USAGE: Right-click this file and select "Run with PowerShell".
# =========================================================================

try {
    # --- Configuration ---
    $userName       = "JeaToolUser"
    $sandboxRootDir = "C:\SandboxedWorkspaces"

    # Step 1: Verify Administrator Privileges
    Write-Host "Step 1: Checking for Administrator privileges..." -ForegroundColor Gray
    if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw "This script must be run as an Administrator. Please right-click it and choose 'Run with PowerShell'."
    }
    Write-Host "  [SUCCESS] Running as Administrator." -ForegroundColor Green

    # Step 2: Create the Dedicated User Account
    Write-Host "Step 2: Setting up user account '$userName'..." -ForegroundColor Gray
    if (Get-LocalUser -Name $userName -ErrorAction SilentlyContinue) {
        Write-Host "  [INFO] User '$userName' already exists. Skipping creation." -ForegroundColor Yellow
        Write-Host "  To reset the password, use the 'Reset-JeaPassword.ps1' utility." -ForegroundColor Yellow
    } else {
        $password = Read-Host -AsSecureString "Please enter a new, strong password for the '$userName' account"
        New-LocalUser -Name $userName -Password $password -PasswordNeverExpires -FullName "Sandboxed Tool User" -Description "Service account for the sandboxed file system tools."
        Write-Host "  [SUCCESS] User '$userName' created successfully." -ForegroundColor Green
    }

    # Step 3: Create the Sandbox Directory
    Write-Host "Step 3: Creating sandbox directory at '$sandboxRootDir'..." -ForegroundColor Gray
    if (-not (Test-Path -Path $sandboxRootDir)) {
        New-Item -Path $sandboxRootDir -ItemType Directory -Force | Out-Null
        Write-Host "  [SUCCESS] Directory created." -ForegroundColor Green
    } else {
        Write-Host "  [INFO] Directory already exists." -ForegroundColor Yellow
    }

    # Step 4: Set Strict File System Permissions
    Write-Host "Step 4: Applying strict permissions to '$sandboxRootDir'..." -ForegroundColor Gray
    $userObject = Get-LocalUser -Name $userName
    $rule = New-Object System.Security.AccessControl.FileSystemAccessRule($userObject.Name, "FullControl", "ContainerInherit, ObjectInherit", "None", "Allow")
    $acl = Get-Acl -Path $sandboxRootDir
    # This is the most critical security step: it isolates the folder.
    $acl.SetAccessRuleProtection($true, $false)
    $acl.AddAccessRule($rule)
    Set-Acl -Path $sandboxRootDir -AclObject $acl
    Write-Host "  [SUCCESS] Permissions applied. '$userName' has full control inside the sandbox and nowhere else." -ForegroundColor Green

    # --- Final Confirmation ---
    Write-Host "-----------------------------------------------------------------" -ForegroundColor Cyan
    Write-Host "SIMPLE SANDBOX SETUP COMPLETE!" -ForegroundColor Cyan
    Write-Host "-----------------------------------------------------------------" -ForegroundColor Cyan
    Write-Host "The system is now configured. To run your application, use the"
    Write-Host "'run_app_as_jea_user.bat' script in your project's root directory." -ForegroundColor Yellow
    Write-Host "-----------------------------------------------------------------" -ForegroundColor Cyan
}
catch {
    Write-Host "[FATAL ERROR] An error occurred during setup:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}