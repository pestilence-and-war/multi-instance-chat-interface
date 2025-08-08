# my_tools/SafeExecutor.ps1

param(
    # <<< FIX: Added a mandatory parameter for the workspace path.
    [Parameter(Mandatory=$true)]
    [string]$WorkspacePath,

    [Parameter(Mandatory=$true)]
    [string]$CommandToRun
)

try {
    $AllowedCommands = @(
        'Get-ChildItem', 'Resolve-Path', 'Test-Path',
        'Get-Content',
        'Set-Content', 'Add-Content', 'New-Item',
        'Copy-Item', 'Move-Item', 'Remove-Item', 'Rename-Item',
        'Get-Command'
    )

    # <<< FIX: Force the starting location to the correct project workspace.
    Set-Location -Path $WorkspacePath -ErrorAction Stop

    $CommandVerb = ($CommandToRun.Split(' ')[0])

    if ($CommandVerb -in $AllowedCommands) {
        Invoke-Expression -Command $CommandToRun
    } else {
        throw "Security Error: The command '$CommandVerb' is not in the allowed list."
    }
}
catch {
    Write-Error -Message $_.Exception.Message
    exit 1
}