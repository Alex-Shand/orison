from orison import sh

# Install VirtIO Drivers
sh.run('F:\\virtio-gt-x64.msi', capture=False, check=False)
sh.run('F:\\virtio-win-guest-tools.exe', capture=False, check=False)

# Install WinFuse
sh.run('E:\\_orison\\winsfp.msi', capture=False, check=False)

# Ensure Virt-FS service starts on boot
