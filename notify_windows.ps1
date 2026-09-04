# Fires a Windows toast notification. Called by driver.py (subprocess) when
# evolve commits a real change - not required for simulate/evolve to work,
# just a convenience so activity reaches you without opening the viewer.
# Uses the WinRT toast API directly (no BurntToast module / extra dependency),
# borrowing PowerShell's own AppUserModelID so Windows attributes the toast
# to something it recognizes instead of failing silently.
param(
    [Parameter(Mandatory = $true)][string]$Title,
    [Parameter(Mandatory = $true)][string]$Message
)

try {
    [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
    [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] > $null

    $escapedTitle = [System.Security.SecurityElement]::Escape($Title)
    $escapedMessage = [System.Security.SecurityElement]::Escape($Message)

    $template = @"
<toast>
  <visual>
    <binding template="ToastGeneric">
      <text>$escapedTitle</text>
      <text>$escapedMessage</text>
    </binding>
  </visual>
</toast>
"@

    $xml = New-Object Windows.Data.Xml.Dom.XmlDocument
    $xml.LoadXml($template)
    $toast = New-Object Windows.UI.Notifications.ToastNotification $xml
    $appId = '{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\WindowsPowerShell\v1.0\powershell.exe'
    [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($appId).Show($toast)
} catch {
    # Never let a notification failure break an evolve run - this is a nice-
    # to-have, not part of the guardrail chain.
    Write-Error "notify_windows.ps1 failed: $_"
    exit 1
}
