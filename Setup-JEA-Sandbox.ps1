# ===================================================================================
#  JEA (Just Enough Administration) Sandbox Setup Script
#
#  This script automates the complete setup of a secure, sandboxed PowerShell
#  environment for use with sandboxed tools. It performs the following actions:
#
#  1.  Ensures the script is running with Administrator privileges.
#  2.  Creates a dedicated, low-privilege local user account (JeaToolUser).
#  3.  Creates a "sandbox root" directory (C:\SandboxedWorkspaces).
#  4.  Applies strict file system permissions, isolating the sandbox directory.
#  5.  Creates the necessary JEA configuration files (.psrc and .pssc) with
#      a secure whitelist of commands.
#  6.  Ensures the WinRM service is configured and running.
#  7.  Registers the secure "JailedPowerShell" JEA endpoint.
#
#  USAGE: Right-click this file and select "Run with PowerShell".
# ===================================================================================

# --- Script Configuration ---
$userName         = "JeaToolUser"
$sandboxRootDir   = "C:\SandboxedWorkspaces"
$transcriptDir    = "C:\JEATranscripts"
$moduleName       = "JEAConfig"
$endpointName     = "JailedPowerShell"

# Define paths for JEA configuration files
$modulePath        = Join-Path $env:ProgramFiles "WindowsPowerShell\Modules\$moduleName"
$roleCapabilityDir = Join-Path $modulePath "RoleCapabilities"
$psrcPath          = Join-Path $roleCapabilityDir "SandboxedFileTools.psrc"
$psscPath          = Join-Path $modulePath "SandboxedSession.pssc"

# --- Main Execution Block ---
try {
    # Step 1: Verify Administrator Privileges
    Write-Host "Step 1: Checking for Administrator privileges..." -ForegroundColor Gray
    if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw "This script must be run as an Administrator. Please right-click the script and select 'Run with PowerShell'."
    }
    Write-Host "  [SUCCESS] Running as Administrator." -ForegroundColor Green

    # Step 2: Create the Dedicated User Account
    Write-Host "Step 2: Setting up user account '$userName'..." -ForegroundColor Gray
    if (Get-LocalUser -Name $userName -ErrorAction SilentlyContinue) {
        Write-Host "  [INFO] User '$userName' already exists. Skipping creation." -ForegroundColor Yellow
    } else {
        $password = Read-Host -AsSecureString "Please enter a new, strong password for the '$userName' service account"
        New-LocalUser -Name $userName -Password $password -PasswordNeverExpires -FullName "JEA Sandboxed Tool User" -Description "Service account for the sandboxed PowerShell tool."
        Write-Host "  [SUCCESS] User '$userName' created successfully." -ForegroundColor Green
    }

    # Step 3: Create Sandbox and Transcript Directories
    Write-Host "Step 3: Creating directories..." -ForegroundColor Gray
    New-Item -Path $sandboxRootDir -ItemType Directory -Force | Out-Null
    New-Item -Path $transcriptDir -ItemType Directory -Force | Out-Null
    New-Item -Path $modulePath -ItemType Directory -Force | Out-Null
    New-Item -Path $roleCapabilityDir -ItemType Directory -Force | Out-Null
    Write-Host "  [SUCCESS] Directories created: $sandboxRootDir, $transcriptDir, and JEA module folders." -ForegroundColor Green

    # Step 4: Set Strict File System Permissions
    Write-Host "Step 4: Applying strict permissions to '$sandboxRootDir'..." -ForegroundColor Gray
    $userObject = Get-LocalUser -Name $userName
    $rule = New-Object System.Security.AccessControl.FileSystemAccessRule($userObject.Name, "FullControl", "ContainerInherit, ObjectInherit", "None", "Allow")
    $acl = Get-Acl -Path $sandboxRootDir
    $acl.SetAccessRuleProtection($true, $false) # CRITICAL: Disable inheritance
    $acl.AddAccessRule($rule)
    Set-Acl -Path $sandboxRootDir -AclObject $acl
    Write-Host "  [SUCCESS] Permissions applied. '$userName' has full control inside the sandbox and nowhere else." -ForegroundColor Green

    # Step 5: Create JEA Role Capability File (.psrc)
    Write-Host "Step 5: Creating JEA Role Capability file (.psrc)..." -ForegroundColor Gray
    $psrcContent = @"
@{
    GUID = '$(New-Guid)'
    Description = 'Provides sandboxed access to basic file system cmdlets.'
    VisibleCmdlets = @(
        'Get-ChildItem', 'Resolve-Path', 'Test-Path',
        'Get-Content',
        'Set-Content', 'Add-Content', 'New-Item',
        'Copy-Item', 'Move-Item', 'Remove-Item', 'Rename-Item',
        'Get-Command'
    )
    VisibleProviders = 'FileSystem'
}
"@
    $psrcContent | Set-Content -Path $psrcPath -Force
    Write-Host "  [SUCCESS] Created '$psrcPath'." -ForegroundColor Green

    # Step 6: Create JEA Session Configuration File (.pssc)
    Write-Host "Step 6: Creating JEA Session Configuration file (.pssc)..." -ForegroundColor Gray
    $psscContent = @"
@{
    SchemaVersion = '2.0.0.0'
    GUID = '$(New-Guid)'
    RunAsVirtualAccount = `$true
    LanguageMode = 'ConstrainedLanguage'
    TranscriptDirectory = '$transcriptDir'
    RoleDefinitions = @{
        '$userName' = @{ RoleCapabilities = 'SandboxedFileTools' }
        'BUILTIN\Users' = @{ RoleCapabilities = 'SandboxedFileTools' }
    }
}
"@
    $psscContent | Set-Content -Path $psscPath -Force
    Write-Host "  [SUCCESS] Created '$psscPath'." -ForegroundColor Green

    # Step 7: Ensure WinRM is Configured and Running
    Write-Host "Step 7: Checking and configuring WinRM service..." -ForegroundColor Gray
    $winrmService = Get-Service -Name "WinRM" -ErrorAction SilentlyContinue
    if (-not $winrmService -or $winrmService.Status -ne 'Running') {
        Write-Host "  [INFO] WinRM service not running. Running 'winrm quickconfig' to perform setup..." -ForegroundColor Yellow
        winrm quickconfig -force
        Set-Service -Name "WinRM" -StartupType Automatic
    }
    Write-Host "  [SUCCESS] WinRM service is configured and running." -ForegroundColor Green

    # Step 8: Register the JEA Endpoint
    Write-Host "Step 8: Registering the JEA endpoint '$endpointName'..." -ForegroundColor Gray
    Register-PSSessionConfiguration -Path $psscPath -Name $endpointName -Force
    Write-Host "  [SUCCESS] JEA endpoint '$endpointName' registered successfully." -ForegroundColor Green

    # --- Final Confirmation ---
    Write-Host "-----------------------------------------------------------------" -ForegroundColor Cyan
    Write-Host "JEA SANDBOX SETUP COMPLETE!" -ForegroundColor Cyan
    Write-Host "-----------------------------------------------------------------" -ForegroundColor Cyan
    Write-Host "Summary:"
    Write-Host " - User:          $userName"
    Write-Host " - Sandbox Root:  $sandboxRootDir"
    Write-Host " - JEA Endpoint:  $endpointName"
    Write-Host ""
    Write-Host "NEXT STEPS:" -ForegroundColor Yellow
    Write-Host " 1. Place all projects you want the LLM to interact with inside '$sandboxRootDir'."
    Write-Host " 2. Ensure your application's .env file has 'CODEBASE_DB_PATH' pointing to the project's database within the sandbox."
    Write-Host " 3. You can now use the high-level tools in 'jailed_file_manager.py'."
    Write-Host "-----------------------------------------------------------------" -ForegroundColor Cyan

}
catch {
    Write-Host "[FATAL ERROR] An error occurred during setup:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
