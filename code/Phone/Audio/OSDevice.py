# -*- coding: utf-8 -*-
from __init__ import SAMPLE_RATE, CHANNELS
import ossaudiodev as dev

class OsDev(object):
	
	def __init__(self):
		self.device = None

	def open(self):
		#Try to open device in read-write mode
		try:
			self.device = dev.open('rw')
			self.device.setparameters(dev.AFMT_S16_LE, CHANNELS, SAMPLE_RATE) 
			self.device.nonblock()
			self.isopen = True
  
		except IOError:
			print "Couldn't open device..."
			self.isopen = False
		return self.isopen
	
	def close(self):
		if self.isopen():
			self.device.close()

	def getfmt(self):
		return "AFMT_S16_LE"

	def read(self, samples):
		return self.device.read(samples)
	
	def write(self, data):
		self.device.writeall(data)
