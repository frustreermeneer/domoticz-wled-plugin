# WLED - Domoticz Python Plugin
Python plugin for Domoticz to add integration with [WLED](https://github.com/Aircoookie/WLED) project

## Installation

1. Clone repository into your domoticz plugins folder
```
cd domoticz/plugins
git clone https://github.com/frustreermeneer/domoticz-wled-plugin.git wled
```
2. Restart domoticz
3. Make sure that "Accept new Hardware Devices" is enabled in Domoticz settings
4. Go to "Hardware" page and add new item with type "WLED"

Once plugin is started it will create appropriate domoticz devices. You will find these devices on `Setup -> Devices` page.

## Plugin update

1. Go to plugin folder and pull new version
```
cd domoticz/plugins/wled
git pull
```
2. Restart domoticz