# -*- coding: utf-8 -*-
#Softphone for handling VoIP and SIM calls
import os, time
from rtp_socket import RTPHandler, PAYD_PCMU, PAYD_PCMA, PAYD_CN, PAYD_TELEVENT, TELEVENT_PARAMS
from sip import SIPSession
from sdp import SessionDescriptor

class Softphone(object):

	def startVoIP(self, ip):
		self.ip = ip
		self.username = "100"
		self.domain = "10.10.10.6"
		self.password = "b2ad4080469bd1aaf1b4af43ecc0512c"
		self.SIP = SIPSession(self.ip, self.username, self.domain, self.password, display_name="SMTP Softphone")
		self.RTP = RTPHandler(self.ip)
		self.SDP = SessionDescriptor(self.ip)
		self.SDP.rtpmap(PAYD_PCMU)
		self.SDP.rtpmap(PAYD_PCMA)
		self.SDP.rtpmap(PAYD_CN)
		self.SDP.rtpmap(PAYD_TELEVENT, TELEVENT_PARAMS, True)
		self.SIP.send_sip_register(domain)

	def makeVoIPcall(self, text, extension):
		rtp_bindport = self.RTP.open()
		self.SDP.changeRTPport(rtp_bindport)
		self.SDP.changeTime()
		self.RTP.PrepareTransmision(text=text)
		address = extension + '@' + domain
		self.SIP.send_sip_invite(address, str(SDP)) 
		print 'CALLING...'
		is_incall = True
		is_transmiting = False

		while is_incall:
			is_incall, cansend, rtp_dport = self.SIP.getStatus()
			if cansend:
				if not is_transmiting: 
					is_transmiting = self.RTP.StartTransmision(domain, rtp_dport)

		self.RTP.StopTransmision()						
		self.RTP.close()

	def stopVoIP(self):
		self.SIP.send_sip_register(domain,0)
		time.sleep(0.1)
		self.SIP.close()
