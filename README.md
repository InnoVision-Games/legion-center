# Legion Center - Decky Plugin

[![](https://img.shields.io/github/downloads/InnoVision-Games/legion-center/total.svg)](https://github.com/InnoVision-Games/legion-center/releases)

A Decky Loader plugin from InnoVision Games that brings controller remapping, fan control, power LED, and charge limit management for the original Legion Go (Z1E) to SteamOS/Linux -- functionality otherwise only available through Lenovo's Windows-only Legion Space app.

- [Functionality](#functionality)
- [Install Instructions](#install-instructions)
  - [Prerequisites](#prerequisites)
  - [Quick Install / Update](#quick-install--update)
  - [Manual Install](#manual-install)
- [Manual Build](#manual-build)
- [Experimental Features](#experimental-features)
  - [Custom Fan Curves](#custom-fan-curves)
    - [Setup Instructions](#fan-curve-setup-instructions)
- [Troubleshooting/FAQ](#troubleshooting--frequently-asked-questions)
  - [LED management seems to work temporarily](#led-management-seems-to-work-temporarily)
  - [Can I turn off the power LED light while the device is asleep?](#can-i-turn-off-the-power-led-while-the-device-is-asleep)
- [Attribution](#attribution)

![fan-control image](./images/fan-control.png)

![remap buttons image](./images/remap-buttons.png)

# Functionality

### This plugin uses the Lenovo-built remapping + bios functionality that's used for Legion Space, which means that this plugin can only do what Legion Space is capable of

This remapping plugin also only covers remapping for the X-input mode of the controller, it does NOT support FPS mode or D-input modes.

Included Functionality in this plugin:

- Power LED on/off control
- Back Button Remapping for Y1, Y2, Y3, M2, M3 (M1 is not supported)
- Enabling/Disabling the touchpad
- Gyro remapping to Left or Right Control Stick
- allow any of these settings on a per-game basis
- (requires acpi_call) 80% charge limit toggle and custom fan curves

# Install Instructions

### Prerequisites

Decky Loader must already be installed.

### Quick Install / Update

Run the following in terminal, then reboot. Note that this works both for installing or updating the plugin

```
curl -L https://github.com/InnoVision-Games/legion-center/raw/main/install.sh | sh
```

### Manual Install

add Udev rules to your device.

Create a file at `/etc/udev/rules.d/90-legion-center.rules`, and add the following to the file:

```
# allow r/w access by all local/physical sessions (seats)
# https://github.com/systemd/systemd/issues/4288
SUBSYSTEMS=="usb", ATTRS{idVendor}=="17ef", TAG+="uaccess"

# allow r/w access by users of the plugdev group
SUBSYSTEMS=="usb", ATTRS{idVendor}=="17ef", GROUP="plugdev", MODE="0660"

# allow r/w access by all users
SUBSYSTEMS=="usb", ATTRS{idVendor}=="17ef", MODE="0666"
```

After saving the file, then run `sudo udevadm control --reload` in terminal.

Download the latest release from the [releases page](https://github.com/InnoVision-Games/legion-center/releases)

Unzip the `tar.gz` file, and move the `LegionCenter` folder to your `$HOME/homebrew/plugins` directory

then run:

```
sudo systemctl restart plugin_loader.service
```

then reboot your machine.

# Manual Build

- Node.js v16.14+ and pnpm installed

```bash
git clone https://github.com/InnoVision-Games/legion-center.git

cd legion-center

# if pnpm not already installed
npm install -g pnpm

pnpm install
pnpm run build
```

Afterwards, you can place the entire built plugin folder (renamed `LegionCenter`) in the `~/homebrew/plugins` directly, then restart your plugin service

```bash
sudo systemctl restart plugin_loader.service

sudo systemctl reboot
```

# Custom Fan Curves

## WARNING: If you don't properly cool your device, it can go into thermal shutdown! Make sure you set proper fan curves to keep your device cool!

Note that this is using the fan curve implementation in the Legion Go's bios. This may require additional bios update from Lenovo to become fully functional.

This method must be manually enabled. The plugin gives you the ability to `acpi_call` directly from the plugin UI.

run `sudo modprobe acpi_call` in terminal, if this errors out, you need to install `acpi_call`

# Troubleshooting / Frequently Asked Questions

## The Plugin isn't working

First try reinstalling or updating the plugin to the latest version, there's an update button at the bottom of the plugin. You can also re-run the installer to update:

```
curl -L https://github.com/InnoVision-Games/legion-center/raw/main/install.sh | sh
```

If this doesn't fix your issue, next try deleting your `$HOME/homebrew/settings/Legion Center/settings.json` file, and rebooting.

If neither works, please create a github issue.

# Attribution

Legion Center builds on the hardware protocol research and prior plugin work of others in the SteamOS/handheld Linux community. See `THIRD_PARTY_NOTICES.md` for full license details on everything referenced below.

Special thanks to [antheas](https://github.com/antheas) for [reverse engineering and documenting the HID protocols](https://github.com/antheas/hwinfo/tree/master/devices/legion_go) for the Legion Go Controllers, etc.

Also special thanks to [corando98](https://github.com/corando98) for writing + testing the backend functions for talking to the HID devices, investigating fan curves, as well as contributing to the RGB light management code on the frontend.

The `\_SB.GZFD` ACPI/WMI calls used for fan curve, TDP mode, charge limit, and power LED control are documented by the [hhd-dev/adjustor](https://github.com/hhd-dev/adjustor) project (GPLv3).

This plugin originated as a fork of Aarron Lee's `LegionGoRemapper` (BSD 3-Clause); its HID and ACPI backend modules have since been reimplemented by InnoVision Games. See `LICENSE` and `THIRD_PARTY_NOTICES.md` for the full license chain.

Icon and controller button SVG files generated from PromptFont using FontForge.

> PromptFont by Yukari "Shinmera" Hafner, available at https://shinmera.com/promptfont
