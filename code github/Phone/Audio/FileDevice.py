# -*- coding: utf-8 -*-
import os, wave
from __init__ import SAMPLE_RATE, CHANNELS

class FileDev(object):

	def __init__(self):
		self.start_sample = 0

	def FileProcess(self, audiofile='tmp.mp3', filenum = 0, rm=True):
		isopen = True
		if audiofile.endswith('.wav'):
			try:
				print 'text already processed...'
				wavfile = wave.open(audiofile)
				self.filename = audiofile
			except IOError:
				print 'Error opening the file...'
				isopen = False

		else:
			if os.system('lame --decode ' + audiofile + ' tmp.wav && sox -q tmp.wav -r ' + str(SAMPLE_RATE) + ' -c ' + str(CHANNELS) + ' -e signed-integer /home/fmadmin/Softphone/code/Phone/Audio/saved/AUD_' + str(filenum) + '.wav') != 0:
				print "Can't process audio file... Check its a valid format"
			try:
				self.filename = '/home/fmadmin/Softphone/code/Phone/Audio/saved/AUD_' + str(filenum) + '.wav'
				wavfile = wave.open(self.filename)
				#Removing temporarely audio files
				if rm:
					os.system('rm tmp*')

			except IOError:
				print 'Error opening the file...'
				isopen = False
		
		self.wav_samples = wavfile.getnframes()*2
		self.wav_data = wavfile.readframes(self.wav_samples)
		wavfile.close()


		return isopen 

	def read(self, samples):
		#Reads the amount of samples in the audiofile
		last_sample = self.start_sample + samples * 2	
		if last_sample < self.wav_samples:
			read_data = self.wav_data[self.start_sample:last_sample]	
			self.start_sample = last_sample
			eof = False
		else:
			read_data = self.wav_data[self.start_sample:self.wav_samples] + chr(0) * (last_sample - self.wav_samples)
			eof = True

		return read_data, eof 

	def rewind(self):
		self.start_sample = 0

	def getfulldata(self):
		return self.wav_data

	def getsamples(self):
		return self.wav_samples

	def getname(self):
		return self.filename

	def close(self):
		self.wav_data = ''
		self.wav_samples = 0
		self.start_sample = 0

