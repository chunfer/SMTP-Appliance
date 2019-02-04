#Softphone for handling VoIP, SIM calls, SMS and Mail
import smtplib, os, time

#VoIP Libraries
from rtp import RTPHandler, PAYD_PCMU, PAYD_PCMA, PAYD_CN, PAYD_TELEVENT, TELEVENT_PARAMS
from sip import SIPSession, REGISTER, INVITE, MESSAGE, CANCEL, BYE
from sdp import SessionDescriptor

#SIM Library
from SIM900 import ATMaster

#Language
LANG = 'en'

#VoIP constants
USERNAME, DOMAIN, PASSWORD, DISPLAY_NAME = '<Softphone extension>', '<Proxy\'s IP>', '<Softphone password>', 'SMTP Softphone'

#Mail Variables
SOFTPHONE_MAIL, SOFTPHONE_PASSWORD = '<Softphone email>', '<Email password>'
MAIL_SERVER, MAIL_PORT = 'smtp.gmail.com', 587

#Modules Enabled
VOIP_ENABLED, SIMCALL_ENABLED, SMS_ENABLED, MAIL_ENABLED = True, True, True, True

#Modules Numbers
MAIL, VOIP_CALL, SIM_CALL, SMS = 0, 1, 2, 3

#Receptors dictionary variables MAIL: (EXTENSION, PHONE NUMBER)
MAIL_NUMBERS = {'<user email>':('<user extension>','<user phone number>')}

class Softphone(object):
	
	def __init__(self, ip):

		if MAIL_ENABLED:
			self.startMail()

		if SIMCALL_ENABLED or SMS_ENABLED:
			self.startSIM()

		if VOIP_ENABLED:
			 self.startVoIP(ip)

	def run(self, mail_text = '', rcpttos = [], sms_text = '', call_text = '', functions_order = (),  call_lang = LANG):
		for elt in functions_order:
			if elt == MAIL and MAIL_ENABLED:
				self.sendMail(rcpttos, mail_text)
			else:
				for rcpt in rcpttos:
					was_answered = False
					if elt == VOIP_CALL and VOIP_ENABLED:
						try:
							self.makeVoIPcall(MAIL_NUMBERS[0], call_text, call_lang)
							was_answered = self.SIP.Call_wasAnswered()
						except IndexError:
							print 'NO EXTENSION FOUND ON REGISTER....'

					elif elt == SIM_CALL and SIMCALL_ENABLED and not was_answered:
						try:
							self.makeSIMcall(MAIL_NUMBERS[1], call_text, call_lang)
						except IndexError:
							print 'NO PHONE NUMBER FOUND ON REGISTER....'

					elif elt == SMS and SMS_ENABLED:
						self.sendSMS(MAIL_NUMBERS[1], sms_text)

					else:
						print 'MODULE NUMBER INCORRECT...'
	def startMail(self):
		self.user = SOFTPHONE_MAIL
		self.password = SOFTPHONE_PASSWORD

	def startSIM(self):
		self.SIM = ATMaster()

	def startVoIP(self, ip):
		self.ip = ip
		self.username = USERNAME
		self.domain = DOMAIN
		self.password = PASSWORD
		self.SIP = SIPSession(self.ip, self.username, self.domain, self.password, display_name=DISPLAY_NAME)
		self.RTP = RTPHandler(self.ip)
		self.SDP = SessionDescriptor(self.ip)
		self.SDP.rtpmap(PAYD_PCMU)
		self.SDP.rtpmap(PAYD_PCMA)
		self.SDP.rtpmap(PAYD_CN)
		self.SDP.rtpmap(PAYD_TELEVENT, TELEVENT_PARAMS, True)
		self.SIP.send_sip(REGISTER)

	def makeSIMcall(self, phone, text, lang = 'en'):
		self.SIM.makeCall(phone, text, lang=lang)

	def sendSMS(self, phone, text):
		self.SIM.sendSMS(phone, text)

	def sendMail(self, rcpttos, data):
		gmail_server = smtplib.SMTP(MAIL_SERVER, MAIL_PORT)
		gmail_server.ehlo()
		gmail_server.starttls()
		gmail_server.ehlo()
		gmail_server.login(self.user, self.password)
		gmail_server.sendmail(self.user, rcpttos, data)
		gmail_server.close()

	def makeVoIPcall(self, extension, text, lang = 'en'):
 		rtp_bindport = self.RTP.open()
		self.SDP.changeRTPport(rtp_bindport)
		self.SDP.changeTime()
		self.RTP.PrepareTransmission(text=text, lang=lang)
		address = extension + '@' + self.domain
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
						is_transmitting = self.RTP.StartTransmission(self.domain, rtp_dport)

					has_timedout = self.RTP.getTimeout()
					if has_timedout:
						is_incall = False

			self.RTP.StopTransmission()
			self.RTP.close()
			if has_timedout:
				self.SIP.send_sip(BYE, address, call_id=call_id, from_tag=from_tag)
						
		except KeyboardInterrupt:
			self.RTP.StopTransmission()
			self.RTP.close()
			self.SIP.send_sip(CANCEL, address, call_id=call_id, from_tag=from_tag)

	def stopSIM(self):
		self.SIM.stop()
		self.SIM.close()

	def stopVoIP(self):
		self.SIP.send_sip(REGISTER, register_frequency=0)
		time.sleep(0.1)
		self.SIP.close()

	def stop(self):
		if SIMCALL_ENABLED or SMS_ENABLED:
			self.stopSIM()

		if VOIP_ENABLED:
			 self.stopVoIP()
