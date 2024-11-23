#!/usr/bin/env bash

set -e

echo \#\#\# Setting up AnyKernel3

git submodule init
git submodule update

echo \#\#\# Setting up toolchain

mkdir -p toolchain
cd toolchain
bash <(curl -s "https://raw.githubusercontent.com/Neutron-Toolchains/antman/main/antman") -S
cd ..

exit