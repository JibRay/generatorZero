#!/usr/bin/env python3

import datetime
import serial
import smbus
import time
import numpy as np

#============================================================================
# Global variables

version = 4

BAUDRATE = 115200

# Receive states.
IDLE = 0
RECEIVING_READINGS = 1

# HTML layouts.
STANDARD = 0
MOBILE = 1

# I2C:
I2C_ADDRESS = 0x44
I2C_MEASURE = 0x2c
I2C_HIGH_REPEATABILITY = 0x06
I2C_REGISTER_ADDRESS = 0x00

#============================================================================
# Functions

def init_I2C():
    bus = smbus.SMBus(1)
    return bus

def write_log(message):
    t = datetime.datetime.utcnow()
    time_stamp = \
        f'{t.year}-{t.month:02d}-{t.day:02d}-{t.hour:02d}-{t.minute:02d}-{t.second:02d}.{t.microsecond:06d} utc: '
    entry = time_stamp + message + '\n'
    with open('/home/pi/Documents/generator.log', 'a') as log_file:
        log_file.write(entry)
    log_file.close()

def log_values(output_voltage, frequency, power, battery_voltage, temperature, humidity):
    message = \
        f'voltage = {output_voltage:0.2f} frequency = {frequency:0.2f} power(W) = {power:0.1f} battery voltage = {battery_voltage:0.2f} temperature(C) = {temperature:0.1f} humidity = {humidity:0.1f}'
    write_log(message)

# Return temperature in celcius and % relative humidity as a tuple.
def get_temperature(bus):
    bus.write_i2c_block_data(I2C_ADDRESS, I2C_MEASURE, [I2C_HIGH_REPEATABILITY])
    time.sleep(0.5)
    data = bus.read_i2c_block_data(I2C_ADDRESS, I2C_REGISTER_ADDRESS, 6)
    temperature = ((((data[0] * 256.0) + data[1]) * 175) / 65535.0) - 45
    humidity = 100 * (data[3] * 256 + data[4]) / 65535.0
    return (temperature, humidity)

# Write two HTML pages, one standard for viewing on laptops etc, and one mobile
# for phones etc. The difference is size. See path variable.
def write_html(output_voltage, frequency, power, battery_voltage, temperature, humidity):
    for layout in [STANDARD, MOBILE]:
        if layout == STANDARD:
            path = '/var/www/html/index.html'
        else:
            path = '/var/www/html/mobile.html'

        with open(path, 'w') as html:
            html.write( '<!DOCTYPE HTML>\n<html>\n')
            html.write( '<head>\n')
            html.write( '  <meta charset="UTF-8">\n')
            html.write( '  <title>Generator Monitor</title>\n')
            html.write( '  <style>\n')
            if layout == STANDARD:
                html.write( '    table { font-size: 30px; }\n')
                html.write( '    th, td { padding: 5px; }\n')
            else:
                html.write( '    table { font-size: 80px; }\n')
                html.write( '    th, td { padding: 12px; }\n')
            html.write( '  </style>\n')
            html.write( '</head>\n')
            html.write( '<body>\n')
            html.write( '  <table border="2">\n')
            html.write( '  <tr>\n')
            html.write( '    <th>Parameter</th>\n')
            html.write( '    <th>Value</th>\n')
            html.write( '  </tr>\n')
            html.write( '    <td>Output Voltage</td>\n')
            html.write(f'    <td>{output_voltage:0.2f}\n')
            html.write( '  <tr>\n')
            html.write( '    <td>Frequency</td>\n')
            html.write(f'    <td>{frequency:0.2f}\n')
            html.write( '  </tr>\n')
            html.write( '  <tr>\n')
            html.write( '    <td>Power, watts</td>\n')
            html.write(f'    <td>{power:0.2f}\n')
            html.write( '  </tr>\n')
            html.write( '  <tr>\n')
            html.write( '    <td>Battery Voltage</td>\n')
            html.write(f'    <td>{battery_voltage:0.2f}\n')
            html.write( '  </tr>\n')
            html.write( '  <tr>\n')
            html.write( '    <td>Temperature °C</td>\n')
            html.write(f'    <td>{temperature:0.1f}\n')
            html.write( '  </tr>\n')
            html.write( '  <tr>\n')
            html.write( '    <td>Humidity</td>\n')
            html.write(f'    <td>{humidity:0.1f}\n')
            html.write( '  </tr>\n')
            html.write( '  </table>\n')
            html.write( '</body>\n')
            html.write( '</html>\n')

#============================================================================
# Main program
# write_html('/var/www/html/index.html')

receive_state = IDLE

t = datetime.datetime.utcnow()
prev_hour = t.hour

print(f'generator version {version}')
write_log(f'generator version {version}')

try:
    serial_port = serial.Serial(port = "/dev/ttyAMA0", baudrate = BAUDRATE, timeout = 0)
except serial.SerialException as e:
    print('Serial port open failed: {e}')

i2c_bus = init_I2C()
line = ''

while(True):
    try:
        c = serial_port.read().decode()
    except UnicodeDecodeError:
        receive_state = IDLE
    else:
        if (c != ''):
            if receive_state == IDLE:
                if c == '!':
                    line = ''
                    receive_state = RECEIVING_READINGS
            elif receive_state == RECEIVING_READINGS:
                line += c
                if c == '\n':
                    receive_state = IDLE
                    (temperature, humidity) = get_temperature(i2c_bus)
                    parameter_text = line.split(' ')
                    try:
                        output_voltage = float(parameter_text[0])
                        frequency = float(parameter_text[1])
                        current = float(parameter_text[2])
                        if output_voltage < 2.0:
                            output_voltage = 0.0
                        if current < 0.5:
                            current = 0.0
                        power = output_voltage * current
                        battery_voltage = float(parameter_text[3])

                        write_html(output_voltage, frequency, power, battery_voltage, temperature, humidity)

                        print(f'voltage = {output_voltage:0.2f} ', end = '')
                        print(f'current = {current:0.2f} ', end = '')
                        print(f'frequency = {frequency:0.2f} ', end = '')
                        print(f'power = {power:0.2f} ', end = '')
                        print(f'battery voltage = {battery_voltage:0.2f} ', end = '')
                        print(f'temperature = {temperature:0.1f} humidity = {humidity:0.1f}')

                        t = datetime.datetime.utcnow()
                        if output_voltage > 100.0:
                            log_values(output_voltage, frequency, power, battery_voltage, temperature, humidity)
                            prev_hour = t.hour
                        elif t.hour != prev_hour:
                            log_values(output_voltage, frequency, power, battery_voltage, temperature, humidity)
                            prev_hour = t.hour

                    except:
                        pass

