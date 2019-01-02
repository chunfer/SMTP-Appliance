# -*- coding: utf-8 -*-
# SMTP-Softphone
import smtplib, asyncore, base64, myip
from smtpd import SMTPServer
# from Phone import Softphone


class SMTP_Softphone(SMTPServer):

	def start(self, user, password):
		self.user = user
		self.password = password

	def process_message(self, peer, mailfrom, rcpttos, data):
		print "Mail received from: " + mailfrom
		smtp_data = data.replace(mailfrom, self.user)
		self.gmail_server = smtplib.SMTP('smtp.gmail.com', 587)
		self.gmail_server.ehlo()
		self.gmail_server.starttls()
		self.gmail_server.ehlo()
		self.gmail_server.login(self.user, self.password)
		self.gmail_server.sendmail(self.user, rcpttos, smtp_data)
		self.gmail_server.close()


def run():
	ip = myip.getIPaddress()
	SMTP_Phone = SMTP_Softphone((ip, 25), None)
	SMTP_Phone.start('jmsoftphone@gmail.com','@@Manager1')
	try:
		asyncore.loop()
	except KeyboardInterrupt:
		pass

if __name__ == '__main__':
	run()
	
