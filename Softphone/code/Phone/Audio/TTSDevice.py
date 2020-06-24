# -*- coding: utf-8 -*-
"""
Library that transforms any text into a readable 'wav' file. 
The wav file can be used played in:

	- RTP protocol
	- Audio devices

gTTS License:
The MIT License (MIT) Copyright © 2014-2020 Pierre Nicolas Durette
"""

import os

from __init__ import SAMPLE_RATE, CHANNELS
from FileDevice import FileDev
from gtts import gTTS


class TTSDev(FileDev):	
	def __init__(self):
		FileDev.__init__(self) 


	def open(self, text, lang = 'en', rmtts = True):
		#Processing text to speech
		self.text = text.rstrip()
		self.lang = lang
		Audio_Path = os.path.dirname(os.path.realpath(__file__))
		text_num = 1
		was_processed = False
		processed_text = open(Audio_Path + '/processed_text.txt')
		for line in processed_text.readlines():
			if self.text + '\n' == line:
				was_processed = True
				break
			text_num += 1

		processed_text.close()

		if was_processed:
			isopen = self.FileProcess(Audio_Path + '/saved/AUD_' + str(text_num) + '.wav')

		else:
			processed_text = open(Audio_Path + '/processed_text.txt', 'a')
			processed_text.write(self.text + '\n')
			processed_text.close()
			if self.lang != 'en':
				tts = gTTS(self.text, self.lang)
			else:
				tts = gTTS(self.text)

			tts.save('tmp.mp3')
			isopen = self.FileProcess(filenum = text_num,rm = rmtts)

		return isopen

	def gettext(self):
		return self.text

	def getlang(self):
		return self.lang

	def getparams(self):
		return (self.text, self.lang)

