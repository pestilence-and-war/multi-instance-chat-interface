# =========================================================================
#  SafeExecutor.ps1 (Final Corrected Version)
# =========================================================================

# The command to run is passed as the first argument.
param(
    [string]$CommandToRun
)

try {
    # Define the explicit list of allowed command verbs.
    $AllowedCommands = @(
        'Get-ChildItem', 'Resolve-Path', 'Test-Path',
        'Get-Content',
        'Set-Content', 'Add-Content', 'New-Item',
        'Copy-Item', 'Move-Item', 'Remove-Item', 'Rename-Item',
        'Get-Command'
    )

    # Force the starting location to be the sandbox root.
    # The JeaToolUser's OS permissions will prevent access outside of this.
    Set-Location -Path "C:\SandboxedWorkspaces" -ErrorAction Stop


    # --- THIS IS THE FIX ---
    # We now correctly parse the command string to get the command "verb".
    # We split the string by spaces and take the very first element.
    # This correctly isolates "New-Item" from the rest of the command.
    $CommandVerb = ($CommandToRun.Split(' ')[0])
    # --- END OF FIX ---


    # Check if the verb is in our whitelist.
    if ($CommandVerb -in $AllowedCommands) {
        # If it's allowed, execute the full command string and pass its output through.
        Invoke-Expression -Command $CommandToRun
    } else {
        # If not allowed, throw a clear security error.
        throw "Security Error: The command '$CommandVerb' is not in the allowed list."
    }
}
catch {
    # If anything goes wrong, write the error to the error stream and exit.
    Write-Error -Message $_.Exception.Message
    exit 1
}