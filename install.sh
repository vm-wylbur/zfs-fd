#!/bin/bash
#
# Author: PB and Claude
# Date: 2025-07-20
# License: (c) HRDAG, 2025, GPL-2 or newer
#
# ------
# zfs-fd/install.sh
#
# Installer for zfs-fd tool

set -euo pipefail

# Get the absolute path to this directory
INSTALL_FROM="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Installing zfs-fd from $INSTALL_FROM"

# Create wrapper script
cat > /tmp/zfs-fd-wrapper << EOW
#!/bin/bash
# Auto-generated wrapper for zfs-fd
exec "$INSTALL_FROM/zfs-fd" "\$@"
EOW

# Install wrapper
echo "Installing wrapper to /usr/local/bin/zfs-fd"
sudo install -m 755 /tmp/zfs-fd-wrapper /usr/local/bin/zfs-fd
rm /tmp/zfs-fd-wrapper

# Create required directories

sudo groupadd -f zfs-fd
sudo usermod -aG zfs-fd "$USER"

echo "Creating required directories..."
sudo mkdir -p /var/lib/zfs-fd
sudo chown root:zfs-fd /var/lib/zfs-fd
sudo chmod 2775 /var/lib/zfs-fd
sudo mkdir -p /var/log/zfs-fd
sudo chown root:zfs-fd /var/log/zfs-fd
sudo chmod 2775 /var/log/zfs-fd

echo "✅ Installation complete!"
echo "⚠️  Note: If this is your first install, you may need to log out and back in"
echo "   for the zfs-fd group membership to take effect."
echo ""
echo "You can now run 'zfs-fd' from anywhere."
echo "The actual scripts remain in: $INSTALL_FROM"
echo ""
echo "To uninstall: sudo rm /usr/local/bin/zfs-fd"
