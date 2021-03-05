#!/usr/bin/python

import RPi.GPIO as GPIO
import serial
import time
import datetime

ser = serial.Serial('/dev/ttyS0',115200)
ser.flushInput()

power_key = 4
rec_buff = ''
server = 'routechoices.com'
port = '2002'
pin = '0000'


def power_on(power_key):
    print('SIM7080X is starting:')
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(power_key,GPIO.OUT)
    time.sleep(0.1)
    GPIO.output(power_key,GPIO.HIGH)
    time.sleep(2)
    GPIO.output(power_key,GPIO.LOW)
    time.sleep(2)
    ser.flushInput()
    print('SIM7080X is ready')


def power_down(power_key):
    print('SIM7080X is loging off:')
    GPIO.output(power_key,GPIO.HIGH)
    time.sleep(1)
    GPIO.output(power_key,GPIO.LOW)
    time.sleep(2)
    print('Good bye')


def send_at(command, back, timeout):
    rec_buff = ''
    ser.write((command+'\r\n').encode())
    time.sleep(timeout)
    if ser.inWaiting():
        time.sleep(0.1 )
        rec_buff = ser.read(ser.inWaiting())
    if rec_buff != '':
        if back not in rec_buff.decode():
            print(command + ' ERROR')
            print(command + ' back:\t' + rec_buff.decode())
            return 0
        else:
            print(rec_buff.decode())
            return 1
    else:
        print(command + ' no responce')


def parse_gps_data(data):
    parts = data.split(',')
    return {
        'timestamp': int(parts[2]),
        'latitude': float(parts[4]),
        'longitude': float(parts[5]),
    }


def parse_imei_data(data):
    return data[:16]

def generate_message(imei, position):
    return f"+RESP:GTFRI,0,{imei},,,,,,,,,{position['longitude']},{position['latitude']},{position['timestamp']},$"

def get_gps_position():
    rec_null = True
    answer = 0

    print('Get IMEI...')
    rec_buff = ''
    answer = send_at('AT+GSN', 'OK', 1)
    if not answer:
        return False
    imei = parseIMEI(rec_buff)
    print('Start GPS session...')
    rec_buff = ''
    send_at('AT+CGNSPWR=1','OK',1)
    time.sleep(2)
    last_gps_query_ts = 0
    position_buffer = []
    while rec_null:
        if time.time() - last_gps_query_ts > 1:
            last_gps_query_ts = time.time()
            answer = send_at('AT+CGNSINF','+CGNSINF: ', 1)
            if answer:
                answer = 0
                if ',,,,,,' in rec_buff:
                    print('GPS is not ready')
                else:
                    print('GPS data received:')
                    print(rec_buff)
                    position = parse_gps_data(rec_buff)
                    message = generate_message(imei, position)
                    send_at('AT+CNACT=0,1', 'OK', 1)
                    send_at('AT+CACID=0', 'OK', 5)
                    send_at('AT+CAOPEN=0,\"TCP\",\"' + server + '\",' + port, '+CAOPEN: 0,0', 5)
                    send_at('AT+CASEND=0,'+str(len(message))+',100', '>', 2)
                    ser.write(message.encode())
                    time.sleep(0.1)
                    print('Message sent successfully!')
                    send_at('AT+CACLOSE=0','OK',15)
                    send_at('AT+CNACT=0,0', 'OK', 1)
            else:
                print('error %d' % answer)
                send_at('AT+CGNSPWR=0', 'OK', 1)
                return False
        time.sleep(0.1)

try:
    power_on(power_key)
    send_at('AT+CPIN=' + pin, 'OK', 1)
    send_at('AT+CSQ', 'OK', 1)
    send_at('AT+CPSI?', 'OK', 1)
    send_at('AT+CGREG?', '+CGREG: 0,1', 0.5)
    send_at('AT')
    try:
        get_gps_position()
    except KeyboardInterrupt:
        send_at('AT+CGNSPWR=0', 'OK', 1)
        pass
    power_down(power_key)
except:
    if ser != None:
        ser.close()
        GPIO.cleanup()

if ser != None:
    ser.close()
    GPIO.cleanup()