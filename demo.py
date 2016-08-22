"""minimal case pyTENMA demo"""
import pyTENMA # make sure pyTENMA.py is in the same folder
PT=pyTENMA.pyTenma("COM4","log.txt")
PT.readUntilBroken()
