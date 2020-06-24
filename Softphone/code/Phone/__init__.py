# -*- coding: utf-8 -*-
#Softphone for handling VoIP, SIM Calls, SMS and emails

#Required basic libraries
import smtplib, os, time

#VoIP Libraries
from rtp import RTPHandler, PAYD_PCMU, PAYD_PCMA, PAYD_CN, PAYD_TELEVENT, TELEVENT_PARAMS
from sip import SIPSession, REGISTER, INVITE, MESSAGE, CANCEL, BYE, DEFAULT_TIMEOUT
from sdp import SessionDescriptor

#SIM Library
from SIM900 import ATMaster

#Ordered dictionary
from collections import OrderedDict

#Language
LANG = 'en'

#VoIP constants
IP, VOIP_USERNAME, VOIP_DOMAIN, VOIP_PASSWORD, VOIP_DISPLAY_NAME = 'localhost','100', '10.10.10.4', 'b2ad4080469bd1aaf1b4af43ecc0512c', 'SMTP Appliance'
GETSIPSTATUS_DELAY = 1

#Mail Variables
SOFTPHONE_MAIL, SOFTPHONE_PASSWORD = 'jmsoftphone@gmail.com', 'rzsylthvtfpemcau'
MAIL_SERVER, MAIL_PORT = 'smtp.gmail.com', 587

#Modules Enabled
VOIP_ENABLED, SIMCALL_ENABLED, SMS_ENABLED, MAIL_ENABLED = False, False, False, False

#Modules Numbers
MAIL, VOIP_CALL, SIM_CALL, SMS = 0, 1, 2, 3

DEFAULT_EMAIL = '969.980.usac@gmail.com'

class Softphone(object):
	#Transmision handler
	MAIL_NUMBERS = OrderedDict([('969.980.usac@gmail.com',('101','51741878')), ('alexmontufar16@gmail.com',('102','55165303')), ('dpajiflex@hotmail.com',('103','41745676'))])

	def __init__(self, ip = IP, timeout = DEFAULT_TIMEOUT, voip_enabled = VOIP_ENABLED, simcall_enabled = SIMCALL_ENABLED, sms_enabled = SMS_ENABLED, mail_enabled = MAIL_ENABLED):

		#Enable modules at start
		self.voip_enabled = voip_enabled
		self.simcall_enabled = simcall_enabled
		self.sms_enabled = sms_enabled
		self.mail_enabled = mail_enabled

		if self.mail_enabled:
			self.startMail()

		if self.simcall_enabled or self.sms_enabled:
			self.startSIM()

		if self.voip_enabled:
			self.startVoIP(ip, timeout)

	def run(self, rcpttos = [], mail_text = '', sms_text = '', call_text = '', functions_order = (),  call_lang = LANG):
		
		#Check if mail was sent
		mail_sent = False

		for rcpt in rcpttos:

			#Control to only receive one type of call (VoIP or SIM call) per user
			call_was_answered = False
	
			for elt in functions_order:
				if elt == MAIL and self.mail_enabled and len(mail_text) != 0 and not mail_sent:
					self.sendMail(rcpttos, mail_text)
					mail_sent = True

				if elt == SIM_CALL and self.simcall_enabled and len(call_text) != 0 and not call_was_answered:
					try:
						if len(self.MAIL_NUMBERS[rcpt][1]) != 0:
							self.makeSIMcall(self.MAIL_NUMBERS[rcpt][1], call_text, call_lang)
							call_was_answered = self.SIM.Call_wasAnswered()

					except KeyError or IndexError:
						print 'NO PHONE NUMBER OR USER FOUND ON REGISTER....'
			
				if elt == VOIP_CALL and self.voip_enabled and len(call_text) != 0 and not call_was_answered:
					try:
						if len(self.MAIL_NUMBERS[rcpt][0]) != 0:
							self.makeVoIPcall(self.MAIL_NUMBERS[rcpt][0], call_text, call_lang)
							call_was_answered = self.SIP.Call_wasAnswered()

					except KeyError or IndexError:
						print 'NO EXTENSION OR USER FOUND ON REGISTER....'


				if elt == SMS and self.sms_enabled and len(sms_text) != 0:
					try:
						if len(self.MAIL_NUMBERS[rcpt][1]) != 0:
							self.sendSMS(self.MAIL_NUMBERS[rcpt][1], sms_text)

					except KeyError or IndexError:
						print 'NO PHONE NUMBER OR USER FOUND ON REGISTER....'


	def add_user(self, user = DEFAULT_EMAIL, extension = '', phone_number = ''):
		self.MAIL_NUMBERS[user] = str(extension), str(phone_number) 


	def update_user(self, new_user = DEFAULT_EMAIL, position = 0):
		new_self.MAIL_NUMBERS = OrderedDict()
		positions_counter = 0

		for user in self.MAIL_NUMBERS:
			if positions_counter == position:
				new_self.MAIL_NUMBERS[new_user] = self.MAIL_NUMBERS[user]

			else:
				new_self.MAIL_NUMBERS[user] = self.MAIL_NUMBERS[user]

			positions_counter += 1

		self.MAIL_NUMBERS = new_self.MAIL_NUMBERS

	def enableMail(self, mail_user = SOFTPHONE_MAIL, mail_password = SOFTPHONE_PASSWORD, mail_server = MAIL_SERVER, mail_port = MAIL_PORT):
		self.mail_enabled = True

		#Change mail parameters
		self.startMail(mail_user, mail_password, mail_server, mail_port)

	def startMail(self, mail_user = SOFTPHONE_MAIL, mail_password = SOFTPHONE_PASSWORD, mail_server = MAIL_SERVER, mail_port = MAIL_PORT):
		self.mail_user = mail_user
		self.mail_password = mail_password
		self.mail_server = mail_server
		self.mail_port = mail_port

	def sendMail(self, rcpttos, data):
		try:
			gmail_server = smtplib.SMTP(self.mail_server, self.mail_port)
			gmail_server.ehlo()
			gmail_server.starttls()
			gmail_server.ehlo()
			gmail_server.login(self.mail_user, self.mail_password)
			gmail_server.sendmail(self.mail_user, rcpttos, data)
			gmail_server.quit()

		except smtplib.SMTPAuthenticationError as e:
			print e

	def disableMail(self):
		self.mail_enabled = False

	def enableSIMCall(self):
		if not self.simcall_enabled:
			self.simcall_enabled = True

			#check if the SMS module is enabled
			if not self.sms_enabled:
				self.startSIM()

	def enableSMS(self):
		if not self.sms_enabled:
			self.sms_enabled = True

			#check if the SIM Call module is enabled
			if not self.simcall_enabled:
				self.startSIM()


	def startSIM(self):
		self.SIM = ATMaster()
		self.SIM.open()

	def makeSIMcall(self, phone, text, lang = LANG):
		self.SIM.makeCall(phone, text, lang = lang)

	def sendSMS(self, phone, text):
		self.SIM.sendSMS(phone, text)

	def disableSIMCall(self):
		self.simcall_enabled = False

		#Stop SIM if SMS module is enabled
		if not self.sms_enabled:
			self.stopSIM()

	def disableSMS(self):
		self.sms_enabled = False

		#Stop SIM if SIM Call module is enabled
		if not self.simcall_enabled:
			self.stopSIM()

	def enableSMS_fulltext(self):
		if self.sms_enabled:
			self.SIM.enableSMS_fulltext()

	def disableSMS_fulltext(self):
		if self.sms_enabled:
			self.SIM.disableSMS_fulltext()

	def stopSIM(self):
		self.SIM.stop()
		self.SIM.close()

	def enableVoIP(self, ip = IP, timeout = DEFAULT_TIMEOUT, voip_username = VOIP_USERNAME, voip_domain = VOIP_DOMAIN, voip_password = VOIP_PASSWORD, voip_display_name = VOIP_DISPLAY_NAME):

		#If the module is enabled, stop it and restart it
		if self.voip_enabled:
			self.stopVoIP()

		self.voip_enabled = True
		self.startVoIP(ip, timeout, voip_username, voip_domain, voip_password, voip_display_name)

	def startVoIP(self, ip, timeout = DEFAULT_TIMEOUT, voip_username = VOIP_USERNAME, voip_domain = VOIP_DOMAIN, voip_password = VOIP_PASSWORD, voip_display_name = VOIP_DISPLAY_NAME):
		self.voip_domain = voip_domain
		self.SIP = SIPSession(ip, voip_username, self.voip_domain, voip_password, display_name = voip_display_name, timeout = timeout)
		self.RTP = RTPHandler(ip)
		self.SDP = SessionDescriptor(ip)
		self.SDP.rtpmap(PAYD_PCMU)
		self.SDP.rtpmap(PAYD_PCMA)
		self.SDP.rtpmap(PAYD_CN)
		self.SDP.rtpmap(PAYD_TELEVENT, TELEVENT_PARAMS, True)
		self.SIP.send_sip(REGISTER)

	def makeVoIPcall(self, extension, text, lang = 'en'):
 		rtp_bindport = self.RTP.open()
		self.SDP.changeRTPport(rtp_bindport)
		self.SDP.changeTime()
		self.RTP.PrepareTransmission(text=text, lang=lang)
		address = extension + '@' + self.voip_domain
		call_id, from_tag = self.SIP.send_sip(INVITE, address, str(self.SDP)) 
		print 'CALLING TO ' + extension + '...'
		is_incall = True
		is_transmitting = False
		has_timedout = False
		try:
			while is_incall:
				is_incall, cansend, rtp_dport = self.SIP.getStatus()
				if cansend:
					if not is_transmitting: 
						is_transmitting = self.RTP.StartTransmission(self.voip_domain, rtp_dport)

					has_timedout = self.RTP.getTimeout()
					if has_timedout:
						is_incall = False

				time.sleep(GETSIPSTATUS_DELAY)

			self.RTP.StopTransmission()
			self.RTP.close()

			if has_timedout:
				self.SIP.send_sip(BYE, address, call_id=call_id, from_tag=from_tag)
						
		except KeyboardInterrupt:
			self.RTP.StopTransmission()
			self.RTP.close()
			self.SIP.send_sip(CANCEL, address, call_id=call_id, from_tag=from_tag)


	def disableVoIP(self):
		if self.voip_enabled:
			self.voip_enabled = False
			self.stopVoIP()

	def stopVoIP(self):
		self.SIP.send_sip(REGISTER, register_frequency=0)
		time.sleep(0.1)
		self.SIP.close()

	def stop(self):
		if self.simcall_enabled or self.sms_enabled:
			self.stopSIM()

		if self.voip_enabled:
			 self.stopVoIP()
