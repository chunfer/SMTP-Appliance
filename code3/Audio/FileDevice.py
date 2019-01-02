# -*- coding: utf-8 -*-
import os, wave
from Audio import SAMPLE_RATE, CHANNELS

class FileDev(object):

	def __init__(self):
		self.start_sample = 0

	def FileProcess(self, audiofile='tmp.mp3', rm=True):
		isopen = False
		if os.system('lame --decode ' + audiofile + ' tmp.wav && sox -q tmp.wav -r ' + str(SAMPLE_RATE) + ' -c ' + str(CHANNELS) + ' -e signed-integer tmp-payload.wav') != 0:
			print("Can't process audio file... Check its a valid format")
		try:
			wavfile = wave.open('tmp-payload.wav')
			self.wav_samples = wavfile.getnframes()
			self.wav_data = wavfile.readframes(self.wav_samples)
			wavfile.close()

			#Removing temporarely audio files
			if rm:
				os.system('rm ' + audiofile)
				os.system('rm tmp*')
			isopen = True
		except IOError:
			isopen = False
		
		return isopen 

	def read(self, samples):
		#Reads the amount of samples in the audiofile
		last_sample = self.start_sample + samples * 2
		if last_sample < self.wav_samples:
			read_data = self.wav_data[self.start_sample:last_sample]
			self.start_sample = last_sample
			eof = False
		else:
			read_data = self.wav_data[self.start_sample:self.wav_samples] + (chr(0) * (last_sample - self.wav_samples)).encode()
			eof = True

		return read_data, eof 

	def rewind(self):
		self.start_sample = 0

	def getfulldata(self):
		return self.wav_data

	def getsamples(self):
		return self.wav_samples

	def close(self):
		self.wav_data = ''
		self.wav_samples = 0
		self.start_sample = 0

