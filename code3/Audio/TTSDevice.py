# -*- coding: utf-8 -*-
import google_tts
from Audio import SAMPLE_RATE, CHANNELS
from Audio.FileDevice import FileDev
#from gtts import gTTS

class TTSDev(FileDev):
	def __init__(self):
		FileDev.__init__(self) 


	def open(self, text, lang = 'en',rmtts = True):
		#Processing text to speech
		self.text = text
		self.lang = lang
		tts = google_tts.TTS(self.text)
		#tts = gTTS(self.text, self.lang)
		tts.save('tmp.mp3')
		isopen = self.FileProcess(rm=rmtts)
		return isopen

	def gettext(self):
		return self.text

	def getlang(self):
		return self.lang

	def getparams(self):
		return (self.text, self.lang)

