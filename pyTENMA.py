"""
pyTENMA - a simple python script to access data from TENMA multimeters through
their supplied optical serial cable. The pyTenma class provides basic access
to this device, and can be built upon to create more advanced data loggers
and/or graphical interfaces. 

This is very much a work in progress written by Scott Harden 
Feel free to contact me: www.SWHarden.com and SWHarden@gmail.com

This meter outputs serial data in two-line bursts every second.
Each line contains a 9 character ASCII string (followed by a line break)
Each burst contains an old value and a new value.
One new value will always match the old value of the next burst.

I'm brute-force-guessing how this works, and this code won't be complete.
I'm concentrating on things I intend to use (voltage, current, frequency)
but if you add functionality feel free to email me (or use the github)

  OUTPUT DATA FORMAT:

   209493802 <-- this is a demo string for 09.49 kOhms
   11643;80: <-- this is a demo string for 16.43 Volts
   000252802 <-- this is a demo string for 0025 Hz
   428702802 <-- this is a demo string for 28.70 MHz  
   012345678 <-- index values
   ABBBBCDEF
   ||   ||||
   ||   |||`some type of config I don't really care about
   ||   ||`some type of config I don't really care about
   ||   |`sign (positive, negative, zero)
   ||   `mode select.
   |`4 digit meter
   `decimal indicator

   A: decimal indicator.
   B: the value. A abd B combine so value = BBBB*(10^A)
       if B is 5, I think it's overload
   C: mode select
       3=resistance
       ;=voltage
       6=capacitance
       2=frequency
       ?=current (mA range)
       9=current (A range)
       4=temperature
   D: sign select
       <=negative
       8=positive
       9=zero(I think?)

More examples:
    '209523802' is 09.52 kOhm
    '04954;80:' is 4.954 V
    '206486802' is 064.8 nF
    '428702802' is 28.70 MHz
    '00844?80:' is 08.44 mA
    '000264800' is 0026. C
       
I realized that if the display shows "dSC" such as when you apply voltage
when in capacitance mode (oops) no serial data is transmitted and the reader
times out (with an exception). It's fine for now. This softawre is for simple
logging and stuff like that, so I won't worry about it.      

Currently, if timeouts >3 sec are detected, the program exists (!) 
"""

import serial
import serial.tools.list_ports
import time
import os

MODES={"3":"R", # these modes dont have k, M, etc
       ";":"V",
       "6":"uF",
       "2":"Hz",
       "?":"mA",
       "9":"A",
       "4":"C",
       }

          
def formatVal(line,showToo=True,returnUnits=False):
    """
    Return the value (float) of a serial string from the TENMA meter.
    If an overload is detected, the value returned is False.
    This funciton does the string parsing/math to correct for multipliers.
        If showToo is True, print a pretty message to the console.
        If returnUnits is True, returs [value, units]
    """
    val=float(line[1:5])*10**int(line[0])
    mode="unknown mode"
    if line[5] in MODES:
        mode = MODES[line[5]]
    units = mode #TODO: this might be k, M, etc
    sign = "+"
    if line[6]=="<":
        sign="-"
        val*=-1
    if val==0:
        sign=" "
        
    # some modes have different multipliers
    if mode=="V":
        val/=1000.0
    elif mode in ["mA","A"]:
        val/=100.0
    elif mode=="uF":
        val/=1000000.0
    elif mode=="R":
        val/=10.0
        units="Ohm"
        if 10**3<val<10**6:
            val/=10**3
            units="KOhm"
        elif val>=10**6:
            val/=10**6
            units="MOhm"
    
    # do some string magic to make values display prettily
    sVal=str("%.04f"%val) #TODO: max is 4 sig figs I think
    sVal=sign+sVal.replace("-","")
    while sVal[-1]=="0" and len(sVal)>7:
        sVal=sVal[:-1]
    
    # create a nice string with spaces in it
    line2=list(line)
    line2.insert(1," ")
    line2.insert(6," ")
    line2.insert(9," ")
    line2="".join(line2)
    
    # show it and return it    
    msg="%s %s"%(sVal,units)
    if line[0]=="5":
        msg+=" <-- OVERLOAD"
    if showToo:
        print("[%s]\t%s"%(line2,msg))
    if "OVERLOAD" in msg:
        return False
    if returnUnits:
        return val,units
    return val
       
class pyTenma:
    def __init__(self,port=None,logFileName=False):
        print("\n### TENMA MULTIMETER INTERFACE ###")
        devList=self.device_list()
        self.port=port
        self.logFileName=logFileName
        if self.logFileName:
            self.log_init()
        if port is None:
            self.port=self.guessPort
        if not self.port in devList:
            print("!!!  %s isn't in the list of serial ports !!!"%self.port)
        print("Preparing to use",self.port)
        self.ser = serial.Serial()
        self.ser.port = self.port
        self.ser.baudrate = 19230
        self.ser.bytesize = serial.SEVENBITS
        self.ser.parity = serial.PARITY_ODD
        self.ser.stopbits = serial.STOPBITS_ONE
        self.ser.timeout = 3
        self.ser.xonxoff = False
        self.ser.rtscts = False
        self.ser.dsrdtr = False
        self.ser.writeTimeout = 3
        
    def connect(self):
        """open the serial port device"""
        if self.ser.is_open:
            print("serial port already open")
            return
        print("connecting to",self.port,"...")
        self.ser.open()
        self.ser.setRTS(False) # required for tenma meters!
        self.ser.readline() # make sure we can read (may be incomplete)
        print("  connected!")
        self.startTime=time.time()
        
    def disconnect(self):
        """
        Run this before the python script terminates. This will disconnect
        from the serial port and make it easy to reconnect in the future.
        """
        print("disconnecting from",self.port,"...")
        self.ser.close()
        print("  all clear!")
        
    def getValue(self):
        """
        Perform a single reading with error checking.
        The multimeter sends an identical string twice so make sure it matches.
        It seems this thing waits ~1 sec then rapidly sends 2 values, one old
        and one new. The rapid values don't match, but each should match the
        values before and after it.
        """
        times,vals=[],[]
        while True:
            times.append(time.time())
            vals.append(self.ser.readline().decode('ascii').strip())
            if len(times)<2:
                continue
            if abs(times[-1]-times[-2])>.1:
                if vals[-1]==vals[-1]:
                    break
                else:
                    print("values did not match! repeating measurement.")
        return vals[-1]
            
    def device_list(self):
        """return a list of potential com ports"""
        print("Scanning system for serial devices...")
        coms=[]
        for potentialPort in list(serial.tools.list_ports.comports()):
                print(" --",potentialPort.description)
                coms.append(potentialPort.device)
        if len(coms)==0:
            print("ERROR: I don't see any serial devices I can use.")
        else:
            print(" -- devices you could use:",coms)
        return coms
        
    def readUntilBroken(self):
        """
        Keep pulling values until an exception (intended to be a keyboard
        exception). Return values as a list.
        """
        print("I'm going to record values until you CTRL+C me!")
        values=[]
        try:
            PT.connect()
            while True:
                values.append(formatVal(self.getValue()))
                if self.logFileName and len(values)>=10: # logging frequency
                    self.log(str(values)[1:-1].replace(", ","\n")+"\n")
                    values=[]
        except:
            print("Exception ... I got %d values though."%len(values))
            self.log(str(values)[1:-1].replace(", ","\n")+"\n")
        return values
        
    def log(self,text):
        """add text to the log file."""
        with open(self.logFileName,'a') as f:
            f.write(text)
        print(" -- wrote %d lines to %s"%(text.count("\n")+1,
                                          os.path.basename(self.logFileName)))
        
    def log_init(self):
        """
        Add a timestamp to the log file to indicate when it was started.
        This is also an easy to way to crash if the log file path is wrong.
        """
        out="# %d - starting new log - %s\n"%(time.time(),
                        time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
        self.log(out)
           
if __name__=="__main__":
    PT=pyTenma("COM4","log.txt")
    PT.readUntilBroken()
    print("DONE")
