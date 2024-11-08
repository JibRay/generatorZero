#!/usr/bin/env python3

import datetime
import serial
import smbus
import time
import numpy as np

#============================================================================
# Global variables

version = 1

BAUDRATE = 115200

# Receive states.
IDLE = 0
RECEIVING_READINGS = 1

# I2C:
I2C_ADDRESS = 0x44
I2C_MEASURE = 0x2c
I2C_HIGH_REPEATABILITY = 0x06
I2C_REGISTER_ADDRESS = 0x00

battery_voltage = np.array([ \
    (datetime.datetime(2024, 10, 28, 13, 0, 0), 12.1), \
    (datetime.datetime(2024, 10, 29, 13, 1, 0), 12.5)  \
    ])


#============================================================================
# Functions

def init_I2C():
    bus = smbus.SMBus(1)
    return bus

# Return temperature in celcius and relative humidity as a tuple.
def get_temperature(bus):
    bus.write_i2c_block_data(I2C_ADDRESS, I2C_MEASURE, [I2C_HIGH_REPEATABILITY])
    time.sleep(0.5)
    data = bus.read_i2c_block_data(I2C_ADDRESS, I2C_REGISTER_ADDRESS, 6)
    temperature = ((((data[0] * 256.0) + data[1]) * 175) / 65535.0) - 45
    humidity = 100 * (data[3] * 256 + data[4]) / 65535.0
    return (temperature, humidity)

def write_html(path):
    with open(path, 'w') as html:
        html.write('<!DOCTYPE HTML>\n<html>\n<head>\n')
        html.write('  <script type="text/javascript">\n')
        html.write('  window.onload = function () {\n')
        html.write('    var chart = new CanvasJS.Chart("chartContainer",\n')
        html.write('    {\n')
        html.write('      title:{\n')
        html.write('      text: "Battery Voltage"\n')
        html.write('      },\n')
        html.write('      data: [\n')
        html.write('      {\n')
        html.write('        type: "line",\n')
        html.write('        dataPoints: [\n')
        for d in battery_voltage:
            html.write('        {{ x: new Date({}, {}, {}), y: {} }},\n'.format(d[0].year, d[0].month, d[0].day, d[1]))
        html.write('        ]\n')
        html.write('      }\n')
        html.write('      ]\n')
        html.write('    });\n')
        html.write('    chart.render();\n')
        html.write('  }\n')
        html.write('  </script>\n')
        html.write('  <script type="text/javascript" src="https://cdn.canvasjs.com/canvasjs.min.js"></script></head>\n')
        html.write('<body>\n')
        html.write('  <div id="chartContainer" style="height: 300px; width: 100%;">\n')
        html.write('  </div>\n')
        html.write('</body>\n')
        html.write('</html>\n')

#============================================================================
# Main program
# write_html('/var/www/html/index.html')

receive_state = IDLE

try:
    serial_port = serial.Serial(port = "/dev/ttyAMA0", baudrate = BAUDRATE, timeout = 0)
except serial.SerialException as e:
    print('Serial port open failed; {e}')

i2c_bus = init_I2C()

while(True):
    try:
        c = serial_port.read().decode()
    except UnicodeDecodeError:
        receive_state = IDLE
    else:
        if (c != ''):
            if receive_state == IDLE:
                if c == '!':
                    receive_state = RECEIVING_READINGS
            elif receive_state == RECEIVING_READINGS:
                print(c, end = '')
                if c == '\n':
                    receive_state = IDLE
                    (temperature, humidity) = get_temperature(i2c_bus)
                    print(f"temperature = {temperature:0.1f}, humidity = {humidity:0.1f}")
