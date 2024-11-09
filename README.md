# generator

## Description
This code runs in a Raspberry Pi Zero W. It communicates with a Pico via a
UART connection (see generatorPico.git). The Pico sends generator voltage
and frequency as well as battery voltage. This program gets temperature and
humidity information from a SHT30 device via I2C. All this information is
displayed in two web pages; index.html and mobile.html. The web page files
for the web server are updated by this program periodically.

## Setup
1. Run sudo raspi-config to enable I2C 1.
2. Install smbus: `pip3 install smbus`.

## SHT30 Test
SHT30.py was used to initially test the temperature/humidity sensor.
