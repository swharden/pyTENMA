"""
Minimal case example how to pull values from a TENMA multimeter.
You can't just read values form the serial port. You have to set the RTS
pin low and the DTR pin high. I'm guessing this is what drives the transistor
used in the optical detection."""
import serial
import serial.tools.list_ports
import time

for potentialPort in list(serial.tools.list_ports.comports()):
        print(potentialPort.device,"-",potentialPort.description)

ser = serial.Serial()
ser.port = "COM4"
ser.baudrate = 19200
ser.bytesize = serial.SEVENBITS
ser.parity = serial.PARITY_ODD
ser.stopbits = serial.STOPBITS_ONE
ser.timeout = 1.5
ser.open()
try:
    ser.setRTS(False) # required for tenma meters
    t1=time.time()
    for i in range(10):
        print("%.03f"%(time.time()-t1),ser.readline())
except Exception as ER:
    print("EXCEPTION")
    print(ER)
ser.close()
print("DONE")