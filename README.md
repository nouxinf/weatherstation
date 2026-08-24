# Weatherstation

![MicroPython](https://img.shields.io/badge/micropython-%232B2728.svg?style=for-the-badge&logo=micropython&logoColor=white)![](https://custom-icon-badges.demolab.com/badge/Tufty2350-e08920.svg?logo=tufty2350&logoColor=e08920&style=for-the-badge)[![Visitors](https://api.visitorbadge.io/api/visitors?path=nouxinf%2Fweatherstation&label=Views&countColor=%23263759&style=for-the-badge)](https://visitorbadge.io/status?path=nouxinf%2Fweatherstation)

**Weatherstation** is an app for the Badgeware Tufty that shows information either from a multisensor stick or the internet through Openmeteo. It runs fully on the badge, you just need to configure it on your computer and you're set.

## Screenshots

<div align="center">
  <img src="img/scr1.png"/>
  <br/>
  <em>Local sensor data</em>
  <br/>
  <img src="img/scr2.png"/>
  <br/>
  <em>Weather data from the internet</em>
</div>

## How it works

Its a Micropython app for the Badgeware Tufty 2350. That means you don't need to reflash firmware or anything to run the app, and it can run alongside other Micropython apps like the pre-installed ones.

It uses two online APIs:
- **OpenStreetMap Nominatim** - This is for geocoding coordinates into place names
- **Openmeteo** - This actually gets the weather data for places set

Both do not require API keys.

The code loads options from `options.json`, currently only for which unit of measurement temperature should use (either Celsius, Fahrenheit or Kelvin) and for location coordinates. You can set several locations, and optionally set nicknames to override the names OSM Nominatim generates.

## How to install

Currently you can install the app by adjusting the settings in `options.json`, putting the badge in disk mode, and either:
- Running `load.py` and adjusting the `INSTALL_PATH` variable (easy if you have python)
- Copying the `assets` folder, `__init__.py`, `icon.png` and `options.json` (easy if you don't have python)

I will later update this with a web based tool to configure and install the app to make it easier. If you have any problems then make an issue and I'll help.

## Attribution

Jerry Gamblin/jgamblin made the original version of `screenshot.py` which is licensed under the Apache License version 2.0. Extra modifications were added to it.

### AI usage

I used AI to get me started with using the multisensor strip and for general debugging. I also used it to modify screenshot.py to have better windows support and add some extra options.
