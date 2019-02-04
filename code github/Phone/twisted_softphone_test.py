import os, time, threading
from rtp_twisted import RTPHandler, PAYD_PCMU, PAYD_PCMA, PAYD_CN, PAYD_TELEVENT, TELEVENT_PARAMS
from sip import SIPSession, REGISTER, INVITE, MESSAGE, CANCEL, BYE
from sdp import SessionDescriptor

from twisted.internet import reactor, defer


def getIPaddress():
	os.system("ifconfig > ifconfig.txt")
	ifconfig = open("ifconfig.txt")

	#Delete first line
	ifconfig.readline()

	#Get IP address from second line
	ip = ifconfig.readline()
	ip = ip.split()[1]
	ip = ip[5:]
	os.system("rm ifconfig.txt") 
	return ip

def Initiate():
	ip = getIPaddress()
	username = "100"
	domain = "10.10.10.6"
	password = "b2ad4080469bd1aaf1b4af43ecc0512c"
	SIP = SIPSession(ip, username, domain, password, display_name="SMTP Softphone")
	RTP = RTPHandler(ip)
	SDP = SessionDescriptor(ip)
	SDP.rtpmap(PAYD_PCMU)
	SDP.rtpmap(PAYD_PCMA)
	SDP.rtpmap(PAYD_CN)
	SDP.rtpmap(PAYD_TELEVENT, TELEVENT_PARAMS, True)
	SIP.send_sip(REGISTER)
	while True:
		trycall = raw_input('Do you wish to make a call (Y/N): ')
		if trycall == 'Y':
			d1 = defer.Deferred()
			d1.addCallback(RTP.open)
 			rtp_bindport = d1.callback()
			SDP.changeRTPport(rtp_bindport)
			SDP.changeTime()

			text = raw_input('Set text you wish to send: ')
			RTP.PrepareTransmission(text=text)

			extension = raw_input('Set extension: ')

			address = extension + '@' + domain
			call_id, from_tag = SIP.send_sip(INVITE, address, str(SDP)) 
			print 'CALLING...'
			is_incall = True
			is_transmitting = False
			try:
				while is_incall:
					is_incall, cansend, rtp_dport = SIP.getStatus()
					if cansend:
						if not is_transmitting: 
							d2 = defer.Deferred()
							d2.addCallback(RTP.StartTransmission)
							is_transmitting = d2.callback(domain, rtp_dport)

				RTP.StopTransmission()
						
			except KeyboardInterrupt:
				if is_transmitting:
					SIP.send_sip(BYE, address, call_id=call_id, from_tag=from_tag)
				else:
					SIP.send_sip(CANCEL, address, call_id=call_id, from_tag=from_tag)

				RTP.StopTransmission()

		elif trycall == 'N':
			SIP.send_sip(REGISTER, register_frequency=0)
			time.sleep(0.1)
			SIP.close()
			break

	print 'BYE\n'
	reactor.stop()
	
reactor.callWhenRunning(Initiate)
reactor.run()

