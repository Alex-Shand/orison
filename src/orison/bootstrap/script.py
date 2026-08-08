from orison import sh

# Permanently set ExecutionPolicy Bypass
sh.pwsh("Set-ExecutionPolicy -ExecutionPolicy Bypass -Force")

# Disable UAC
sh.pwsh(
    "Set-ItemProperty "
    "-Path 'HKLM:SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System' "
    "-Name ConsentPromptBehaviorAdmin "
    "-Type DWord "
    "-Value 0"
)

# Disable standby
sh.run_audit("powercfg", "/change", "monitor-timeout-ac", "0")
sh.run_audit("powercfg", "/change", "monitor-timeout-dc", "0")
sh.run_audit("powercfg", "/change", "standby-timeout-ac", "0")
sh.run_audit("powercfg", "/change", "standby-timeout-dc", "0")

# Delete the password from the user account to enable auto-login
sh.pwsh("Set-LocalUser -Name 'Admin' -Password ([securestring]::new())")

# Install VirtIO Drivers
sh.msiexec("F:\\virtio-win-gt-x64.msi")
sh.run_audit("F:\\virtio-win-guest-tools.exe", "/passive", "/norestart")

# Install WinFuse
sh.msiexec("E:\\winsfp.msi")

# Ensure Virt-FS service starts on boot
sh.pwsh("Set-Service -Name VirtioFsSvc -StartupType Automatic -Status Running")

# Shutdown
sh.run_audit("shutdown", "/s", "/f", "/t", "10")
