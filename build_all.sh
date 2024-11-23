#!/usr/bin/env bash

set -e

devs=("a51" "f41" "gta4xl" "gta4xlwifi" "m21" "m31" "m31s")

for dev in "${devs[@]}"; do
    echo "### Building for: $dev"
    echo "\n### $dev AOSP\n"
    python3 ./build_kernel.py --target=$dev
    echo "\n### $dev ONEUI\n"
    python3 ./build_kernel.py --target=$dev --oneui
done

exit