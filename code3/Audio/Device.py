# -*- coding: utf-8 -*-
import gsm, audioop
from Audio import TTSMODE, OSMODE, FILEMODE, GSMMODE, PCMUMODE, PCMAMODE
from Audio.OSDevice import OsDev
from Audio.TTSDevice import TTSDev
from Audio.FileDevice import FileDev

class AudioDev(object):
	def __init__(self):
		self.osdevice = OsDev()
		self.ttsdevice = TTSDev()
		self.filedevice = FileDev()
		#For future implementation of GSM EFR
	#	self.gsm_encoder = gsm.gsm(gsm.LITTLE)
	#	self.gsm_decoder = gsm.gsm(gsm.LITTLE)

	def open(self, AUDIO_MODE = TTSMODE, text = 'sample text', lang = 'en', audiofile = "tmp.mp3", rmtmps = True):
		#Choose a mode to open this device
		isopen = False
		if AUDIO_MODE == TTSMODE:
			isopen = self.ttsdevice.open(text,lang,rmtmps)
		elif AUDIO_MODE == OSMODE:
			isopen = self.osdevice.open()
		elif AUDIO_MODE == FILEMODE:
			isopen = self.filedevice.FileProcess(audiofile, rmtmps)

		self.mode = AUDIO_MODE
		self.isopen = isopen
		return isopen

	def read(self, samples, CODING_MODE = PCMUMODE):
		#Encode data using mu-law or a-law
		data, eod = ('', False) 
		if self.isopen:

			if self.mode == TTSMODE:
				data, eod = self.ttsdevice.read(samples)

			elif self.mode == OSMODE:
				data = self.osdevice.read(samples)
	
			elif self.mode == FILEMODE:
				data, eod = self.filedevice.read(samples)

			if CODING_MODE == PCMUMODE:
				data = audioop.lin2ulaw(data, 2)

			elif CODING_MODE == PCMAMODE:
				data = audioop.lin2alaw(data, 2)

			#For future implementation of GSM EFR
		#	elif CODING_MODE == GSMMODE:
		#		data = self.gsm_encoder.encode(data)

			#Else the data is going to be sent as RAW data			

			return data, eod

		else:
			print("Error reading data... please check if the device is opened...")
			return data, eod
		
	def close(self):
		if self.isopen:

			if self.mode == TTSMODE:
				self.ttsdevice.close()

			elif self.mode == OSMODE:
				self.osdevice.close()

			elif self.mode == FILEMODE:
				self.filedevice.close()
		

	def rewind(self):
		if self.isopen:

			if self.mode == TTSMODE:
				self.ttsdevice.rewind()

			elif self.mode == FILEMODE:
				self.filedevice.rewind()

