#!/bin/bash

set -e

if [ ! -f flatpak/repo.tar ]; then
    echo "Cannot find flatpak/repo.tar!"
    exit 1
fi

mv /repo/flatpak/repo /repo/flatpak/repo.old
tar xf flatpak/repo.tar -C /repo/flatpak
