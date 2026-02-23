#! /usr/bin/python3

import sys, time, serial

serialPort = '/dev/ttyUSB0'
baudRate = 9600

RED_ON = 0x11
RED_OFF = 0x21
RED_BLINK = 0x41

YELLOW_ON= 0x12
YELLOW_OFF = 0x22
YELLOW_BLINK = 0x42

GREEN_ON = 0x14
GREEN_OFF = 0x24
GREEN_BLINK = 0x44

BUZZER_ON = 0x18
BUZZER_OFF = 0x28
BUZZER_BLINK = 0x48

def sendCommand(serialport, cmd):
    serialport.write(bytes([cmd]))


def do(seq):
    mSerial = serial.Serial(serialPort, baudRate)

    for action in seq.split(','):
        if 'r' in action:
            sendCommand(mSerial, RED_ON)
        elif 'R' in action:
            sendCommand(mSerial, RED_BLINK)
        else:
            sendCommand(mSerial, RED_OFF)
        if 'y' in action:
            sendCommand(mSerial, YELLOW_ON)
        elif 'Y' in action:
            sendCommand(mSerial, YELLOW_BLINK)
        else:
            sendCommand(mSerial, YELLOW_OFF)
        if 'g' in action:
            sendCommand(mSerial, GREEN_ON)
        elif 'G' in action:
            sendCommand(mSerial, GREEN_BLINK)
        else:
            sendCommand(mSerial, GREEN_OFF)
        if 'B' in action:
            sendCommand(mSerial, BUZZER_ON)
            time.sleep(0.02)
            sendCommand(mSerial, BUZZER_OFF)

        if ':' in action:
            duration = action.split(':')[1]
            try:
                time.sleep(float(duration))
            except:
                pass
            
    mSerial.close()


import cgi
form = cgi.FieldStorage()
sequence = form.getfirst('seq', default='')

sys.stdout.write('Content-type: text/plain\n')
sys.stdout.write('\n')
sys.stdout.flush()
sys.stdout.write('seq: %s\n' % sequence)
sys.stdout.flush()
sys.stdout.close()

do(sequence)


# Sequence: chain of actions, separated by ','
# Action:
#   - 'r','y','g': turn on
#   - 'R','Y','G': blink
#   - 'B': beep for a moment
#   - 'n': off
# Action can be followed by ':DURATION'
# Example:
#    - "g" : turn green on
#    - "r:3,n": turn red on for 3 sec
#    - "r:3,y:1,g": red for 3 sec, yellow for 1 sec, then green
