$code = @'
[DllImport("kernel32.dll", CharSet = CharSet.Auto, SetLastError = true)]
public static extern uint SetThreadExecutionState(uint esFlags);
'@
$type = Add-Type -MemberDefinition $code -Name "SleepUtil" -Namespace "Win32" -PassThru
$flags = 0x80000000 -bor 0x00000002 -bor 0x00000001
[Win32.SleepUtil]::SetThreadExecutionState($flags)

[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

Install-PackageProvider -Name NuGet -MinimumVersion 2.8.5.201 -Force
Set-PSRepository -Name PSGallery -InstallationPolicy Trusted
Install-Module PSwindowsUpdate -Force

Import-Module PSWindowsUpdate

Add-WUServiceManager -MicrosoftUpdate -Confirm:$false

Install-WindowsUpdate -MicrosoftUpdate -AcceptAll -AutoReboot -Verbose

if (Test-Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate\Auto Update\RebootRequired") {
       Restart-Computer -Force
}