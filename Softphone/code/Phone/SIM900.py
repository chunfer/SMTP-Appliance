# -*- coding: utf-8 -*-
import serial, time, threading, os
from Audio.TTSDevice import TTSDev

#Device characteristics
DEVICE = '/dev/ttyUSB0'
BAUDRATE = 9600
TIMEOUT = 1

#Set sleep times
IDLE_SLEEP = 0.2
SERIAL_SLEEP = 0.35
BEFORE_PLAY_SLEEP = 2
AFTER_PLAY_SLEEP = 1.5

#Gap in seconds to detect a not answered call
ANSWER_GAP = 24.5

#SMS control variables
SMS_MAX_LENGTH = 153
SMS_FULLTEXT_MODE = False 

class ATMaster(object):
	
	def __init__(self, sms_max_length = SMS_MAX_LENGTH, sms_fulltext_mode = SMS_FULLTEXT_MODE):
		self.audio = TTSDev()
		self.listening_isenabled = False
		self.is_sending = False
		self.command = ''
		self.CLCC_isenabled = False
		self.CLCC_answer = ''
		self.CLCC_flag = False
		self.has_played = False
		self.init_ring_enabled = True
		self.init_ring_time = 0
		self.sms_fulltext_mode = sms_fulltext_mode

		#The maximum length accepted to be sent is 153
		if sms_max_length > 153:
			self.sms_max_length = 153
		
		else:
			self.sms_max_length = sms_max_length

	def open(self):
		self.ATSerial = serial.Serial(DEVICE, BAUDRATE, timeout=TIMEOUT)

		#start listener
		self.listening_isenabled = True
		AT_listener_starter = threading.Thread(target=self.AT_listener, args=())
		AT_listener_starter.start()

	def makeCall(self, phone, text, lang = 'en'):
		print 'CALLING TO:', phone
		self.audio.open(text, lang)
		self.writeCommand('ATD' + phone + ';')
		self.CLCC_isenabled = True
		self.has_played = False
		CLCC_loop_starter = threading.Thread(target=self.CLCC_loop, args=())
		CLCC_loop_starter.start()

		#Make infinite loop until the call gets finished
		while True:
			time.sleep(SERIAL_SLEEP)
			if not self.CLCC_isenabled:
				break

	def Call_wasAnswered(self):
		return self.has_played

	def enableSMS_fulltext(self):
		self.sms_fulltext_mode = True

	def disableSMS_fulltext(self):
		self.sms_fulltext_mode = False

	def sendSMS(self, phone, text):
		#send SMS
		print 'SENDING SMS TO:', phone
		characters_count = 0
		text_length = len(text)
			
		#Send SMS with characters greater than the máximum length assigned
		while characters_count < text_length:

			self.writeCommand('ATZ')
			time.sleep(SERIAL_SLEEP)
			self.writeCommand('AT+CMGF=1')
			time.sleep(SERIAL_SLEEP)
			self.writeCommand('''AT+CMGS="''' + phone + '''"\r''', False)
			time.sleep(SERIAL_SLEEP)

			#Split text into several messages frames of the max length assigned
			self.writeCommand(text[characters_count : characters_count + self.sms_max_length])

			time.sleep(SERIAL_SLEEP)
			self.writeCommand(chr(26), False)
			time.sleep(SERIAL_SLEEP)

			#Exit loop if the full text is not supposed to be received
			if not self.sms_fulltext_mode:
				break

			else:
				time.sleep(5)

			characters_count +=  self.sms_max_length
			

		self.writeCommand('ATZ')

	def CLCC_loop(self):
		while self.CLCC_isenabled:
			self.writeCommand('AT+CLCC')
			time.sleep(SERIAL_SLEEP)

	def writeCommand(self, command, r_enabled = True):
		if command == 'ATDDET=1':
			command = 'ATDDET=1\r\n'
			r_enabled = False
		
		if command == 'ATSO=2':
			command = 'ATSO=2\r\n'
			r_enabled = False

		self.command = command
		if r_enabled:
			self.ATSerial.write(command + '\r')
		else:
			self.ATSerial.write(command)

	def processCLCC_answer(self, answer):
		state = answer[11]
		if state == '3':
			if self.init_ring_enabled:
				self.init_ring_time = time.time()
				self.init_ring_enabled = False
		
			elif  (time.time() - self.init_ring_time) > ANSWER_GAP:
				self.writeCommand('ATH')
				print 'CALL WAS NOT ANSWERED...'
				self.has_played = False
				self.init_ring_enabled = True
				self.CLCC_isenabled = False

		elif state == '0':
			if not self.has_played:
				#print time.time()
				time.sleep(BEFORE_PLAY_SLEEP)
				os.system('aplay '+ self.audio.getname())
				time.sleep(AFTER_PLAY_SLEEP)
				self.writeCommand('ATH')
				print 'CALL WAS ANSWERED...'
				self.has_played = True
				self.init_ring_enabled = True
				self.CLCC_isenabled = False

	def readline(self):
		eol = '\r'
		line = ''
		while True:
			char = self.ATSerial.read()
			if len(char) > 0:
				if char == eol: 
					break
				elif ord(char) >= 32:
					line += char
			else:
				break
		return line

	def AT_listener(self):
		while self.listening_isenabled:
			if self.ATSerial.inWaiting() > 0:
				data = self.readline()
				if data == 'Call Ready':
					print 'EQUIPMENT IS READY TO MAKE CALLS'

				if data != self.command and len(data) > 0:
					if data.startswith('+CLCC'):
						self.processCLCC_answer(data)

			else:
				time.sleep(IDLE_SLEEP)

	def is_incall(self):
		return self.CLCC_isenabled
			
	def stop(self):
		self.listening_isenabled = False
		self.is_sending = False
		self.CLCC_isenabled = False
		self.writeCommand('ATH')
		self.command = ''
		self.CLCC_flag = False
		self.has_played = False
		self.init_ring_enabled = True
		self.init_ring_time = 0
		
	def close(self):
		self.ATSerial.close()

if __name__ == '__main__':
	try:
		AT = ATMaster()
		AT.open()

		while True:	
			time.sleep(TIMEOUT)
			phone = raw_input('Insert phone number: ')
			text = raw_input('Insert text to send: ')
			lang = raw_input('insert language: ')
			AT.makeCall(phone, text, lang)
			AT.sendSMS(phone, text)
			

	except KeyboardInterrupt:
		AT.stop()
		AT.close()

