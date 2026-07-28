#!/usr/bin/env bash

set -eux

## Required to run check.py ##

if ! command -v uv >/dev/null 2>&1; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
fi

## The actual software ##

cd "$(dirname "$(realpath "$0")")"
PYTHONPATH=src uv run check.py

BIN=$HOME/.local/bin
mkdir -p "$BIN"
cd src
python -m zipapp . \
    --python="/usr/bin/env python" \
    --compress \
    --output="$BIN/orison"

## Virtualization Stuff ##

sudo rpm-ostree install --idempotent qemu-kvm libvirt virt-install
ujust setup-virtualization virt-on

## For GPU passthrough ##

if ! command -v ls-iommu >/dev/null 2>&1; then
    curl -LsSf https://github.com/HikariKnight/ls-iommu/releases/download/2.3.0/ls-iommu_Linux_x86_64.tar.gz -o /tmp/ls-iommu.tar.gz
    tar zxvf /tmp/ls-iommu.tar.gz -C /tmp
    mv /tmp/ls-iommu $BIN/ls-iommu
fi

VENDOR=$(lscpu | perl -ne 'print $1 if /Vendor ID:\s+(.*)/')
case "$VENDOR" in
    GenuineIntel) CPU=intel ;;
    AuthenticAMD) CPU=amd ;;
    *)            echo "Unknown vendor: $VENDOR"; exit 1 ;;
esac

sudo rpm-ostree kargs --append-if-missing=${CPU}_iommu=on --append-if-missing=iommu=pt

if ! rpm-ostree status --json | jq -e '.deployments[0].booted' >/dev/null; then
    sudo systemctl reboot
fi