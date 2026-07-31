from orison import sh

# Install VirtIO Drivers
sh.msiexec("F:\\virtio-win-gt-x64.msi")
sh.run_audit("F:\\virtio-win-guest-tools.exe")

# Install WinFuse
sh.msiexec("E:\\_orison\\winsfp.msi")

# Ensure Virt-FS service starts on boot
sh.pwsh('Set-Service -Name VirtioFsSvc -StartupType Automatic -Status Running')
