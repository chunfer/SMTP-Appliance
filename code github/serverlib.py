# Servers library
# -*- coding: utf-8 -*-
"""
This is the server library version 1.0.0

 Along the code you can see how to:

	- Manage threading to work with a multiple server port
	- Manage SSL connections
	- Manage socket timeouts
	- Handle and create your own exceptions
	- Manage queues
	- Handle library re for regular expressions
	- Develop your own server

This library is thought to be used a base for server developing with python.
Hope you enjoy this library, and look forward to develop production servers.

Best regards,
	Juan Fernando Montufar Juarez

Comments: juanfmontufarjuarez@gmail.com
"""

# Basic libraries
import os, base64, re, time, socket, threading, struct, Queue

#Security libraries
import ssl, binascii, hmac

#Server exceptions
class ServerException(Exception):
	"""Base class for all server exceptions raised""" 

class ServerInitError(ServerException):
	"""Exception for initialization errors"""
		
#General server constants
DEFAULT_TIMEOUT = 3 #socket timeout
PROTO_TYPES = {'TCP': socket.SOCK_STREAM, 'UDP': socket.SOCK_DGRAM}
SSL_KEY = 'YOUR_PATH_TO_KEYFILE' #Keyfile required for SSL ports
SSL_CERT = 'YOUR_PATH_TO_CERTFILE' #Certfile required for SSL ports

class Server(object):
	"""This class is meant to be used as a base for every servers classes.
	It can handle multiple ports and SSL connections.
	"""
	#General server class.

	def __init__(self, ports = (), ssl_ports = (), key = SSL_KEY, cert = SSL_CERT, timeout = DEFAULT_TIMEOUT, greeting_msg = '', address_filter = [], blacklist_mode = True, proto = 'TCP'):
		#Ports should be a tuple, but if an integer is sent, can take it anyway
		if type(ports) == int:
			ports = (ports,)

		if type(ssl_ports) == int:
			ssl_ports = (ssl_ports,)

		if type(ports)!=tuple or type(ssl_ports)!=tuple or type(timeout)!=int or type(address_filter)!=list or not proto in PROTO_TYPES:
			raise ServerInitError('Bad arguments given during initialization...')

		#Set own variables
		self.key = key
		self.cert = cert
		self.greeting_msg = greeting_msg
		self.address_filter = address_filter
		self.blacklist_mode = blacklist_mode
		self.timeout = timeout
		self.connections_enabled = True

		#Open listeners for regular sockets
		for port in ports:
			#Initiate regular socket
			try:
				server_sock = socket.socket(socket.AF_INET, PROTO_TYPES[proto])
				server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
				server_sock.bind(('', port))
				server_sock.listen(5)
			
				#set timeout for regular sockets
				server_sock.settimeout(self.timeout)

				#start thread for regular sockets
				incoming_connection_starter = threading.Thread(target=self.incoming_connection, args=(server_sock,))
				incoming_connection_starter.start()
			
			except socket.error as e:
				
				e = str(e)
				#Find out if error shows that the address is already in use
				if 'Address already in use' in e:

					#Add recommendation for linux users
					e += '\n Run command \'lsof -i:' + str(port) + '\' to check out the PID blocking the port and stop it.'

				raise ServerInitError(e)
		
		#SSL is only supported by TCP protocol
		if proto != 'TCP' and len(ssl_ports) != 0:
			print 'SSL not supported for port(s): ', ssl_ports
			return 0

		#Open listeners for ssl sockets
		for ssl_port in ssl_ports:
			#Initiate ssl socket
			try:			
				ssl_server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
				ssl_server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
				ssl_server_sock.bind(('', ssl_port))
				ssl_server_sock.listen(5)

				#set timeout for ssl socket
				ssl_server_sock.settimeout(self.timeout)

				#start thread for each ssl socket
				ssl_incoming_connection_starter = threading.Thread(target=self.incoming_connection, args=(ssl_server_sock, True))
				ssl_incoming_connection_starter.start()
		
			except socket.error as e:
				
				e = str(e)
				#Find out if error shows that the address is already in use
				if 'Address already in use' in e:
					e += '\n Run command losf -i:' + str(ssl_port) + ' to check out the PID blocking the port and stop it.'

				raise ServerInitError(e)
 
	def incoming_connection(self, server_sock, do_sslwrap = False):
		error_found = False

		#Generald income connection handler
		while self.connections_enabled:
			try:
				client_sock, client_address = server_sock.accept()

				#Check filter mode. If its in blacklist mode will block all addresses in the address filter
				#Boolean function works with XOR
				if self.blacklist_mode ^ (client_address[0] in self.address_filter):

					print 'Got connected from:', client_address
					# Do SSL wrap after the connection has initiated
					if do_sslwrap:
						client_sock = ssl.wrap_socket(client_sock,server_side=True,keyfile=self.key,certfile=self.cert)
						
					#Set timeout for client socket
					client_sock.settimeout(self.timeout)

					#Send greeting message if it's not empty
					if len(self.greeting_msg) != 0:
						client_sock.sendall(self.greeting_msg)

					#Create a thread
					transactions_manager_starter = threading.Thread(target=self.transactions_manager, args=(client_sock,))
					transactions_manager_starter.start()

				else:
					print 'Access denied to:', client_address
					client_sock.close()

			except socket.timeout:
				continue

			except socket.error as e:
				if e[0] == 'The read operation timed out':
					continue
 
				error_found = True
				print e, 'in', server_sock.getpeername()
				break

		if not error_found:
			server_sock.close()


	def transactions_manager(self, client_sock, sslwrap_done = False):
		"""Transmit any message. This is left open for several server types"""

	def close(self):
		#Close connections
		self.connections_enabled = False
		time.sleep(self.timeout * 1.1)

#SMTP server constants
CRLF = '\r\n'
SSMTP_PORTS = (465,) #Default secure SMTP port
SMTP_PORTS = (25, 587) #Default SMTP ports
MAX_LINE_SIZE = 4194304 #Máximum amount of bytes that can be received
SMTP_MAXWAIT_TIME = 300 #Máximum amount of time (in seconds) to wait for receiving information for each client
SMTP_EHLO_REGPARAMS = ['STARTTLS', 'SIZE ' + str(MAX_LINE_SIZE), '8BITMIME','HELP'] #EHLO regular parameters
AUTH_STR = 'AUTH YOUR_AUTH_TYPES' #Authentication types supported
SMTP_NOAUTH_LIST = ['localhost'] #Addresses that don't require authentication
SMTP_HELP = """
This is SMTP Sever version 1.0.0
Commands available:
      HELO    EHLO    MAIL    RCPT    DATA
      RSET    NOOP    QUIT    HELP    VRFY
      EXPN    AUTH    STARTTLS
To report bugs in the implementation send email to:
    juanfmontufarjuarez@gmail.com.
Best regards to you programmer.
End of HELP info
"""


class SMTPServer(Server):
	"""To initiate a high performance SMTP server with SSL connections on python run the following
		import serverlib
		server = serverlib.SMTPServer()
	"""
	#Server for handling SMTP protocol

	def __init__(self, wait_response = SMTP_MAXWAIT_TIME, ports = SMTP_PORTS, ssl_ports = SSMTP_PORTS, key = SSL_KEY, cert = SSL_CERT, timeout = DEFAULT_TIMEOUT, address_filter = []):

		#Validate wait_response argument. (set wait_response as None is valid and is taken as no cause disconnections)
		if wait_response != None:
			if type(wait_response) != int:
				raise ServerInitError('Bad arguments given during initialization...')
		
		#Set amount of time to wait for receiving a command. If the time has expired will close the connection
		self.wait_response = wait_response

		#Initiate to create a queue based on each mail received
		self.mails_queue = Queue.Queue()

		#Intitate dictionary of users
		self.smtp_users = {} 

		#Generate greeting message
		self.fqdn = socket.getfqdn()
		greeting_msg = '220 ' + self.fqdn + ' Service ready ESMTP' + CRLF

		#Catch ssl ports
		self.ssl_ports = ssl_ports

		#Initiate server
		Server.__init__(self, ports, ssl_ports, key, cert, timeout, greeting_msg, address_filter)

		#Initiate thread for handling queue
		queue_manager_starter = threading.Thread(target=self.queue_manager)
		queue_manager_starter.start() 

	def add_user(self, user, password = '', username = ' ', groupname = 'default_group'):

		#Add user to dictionary
		if user not in self.smtp_users:
			self.smtp_users[user] = (password, username, groupname)
			print user, 'has been added successfully'

	def setwait(self, wait_response):
		self.wait_response = wait_response

	def transactions_manager(self, client_sock):
		""" This function is meant to be used to manage all SMTP transactions for each client.
		RFCs followed:
			- RFC 5321: For general SMTP transactions
			- RFC 3207: STARTTLS Command
			- RFC 2554: Authentication process
			
		"""

		def mail_filter(mailfrom, rcpttos, data):
			"""Filter function.
			Will decide if the message received can be added to the mail queue
			To be defined by user.
			"""

			#By default, will return that all the information is allowed to pass the filter
			return True

		error_found = False

		#Initialize arguments for each client
		mailfrom = ''
		rcpttos = []
		data = ''
		mail_stage = '' #Identifier of mail stage
		challenge = '' #Random string for CRAM MD5
		timeout_counter = 0 #Counter (in seconds) of timeouts
		authenticated = False
		helo_response = self.fqdn + ' Hello'
		
		#Verify if ssl connection has started
		ssl_started = client_sock.getsockname()[1] in self.ssl_ports

		#Generate a single line response based on a list of responses
		gen_resp = lambda code, resps: str(code) + '-' + (CRLF + str(code) +'-').join(resps[:-1]) + CRLF + str(code) + ' ' + resps[-1] + CRLF
		
		client_file = client_sock.makefile('rb')

		#Start reading socket
		while self.connections_enabled:

			try:
				#Disconnect from sockets that are connected longer than a threeshold (default: SMTP_MAXWAIT_TIME)
				if self.wait_response != None:
					if timeout_counter >= self.wait_response:
						raise socket.error('Time limit reached... Will disconnect from socket')

				line = client_file.readline(MAX_LINE_SIZE + 1)

				#If the line read is empty it means a disconnection from the client
				if len(line) == 0:
					raise socket.error('Client closed connection')

				#Make the read non-case sensitive
				upline = line.upper()

				#Start discrimination based on SMTP commands
				if upline.startswith('HELO'):
					client_sock.sendall('250 ' + helo_response + CRLF)
				
				elif upline.startswith('EHLO'):

					#Generate EHLO response base if ssl has been started
					if ssl_started:
						ehlo_response = gen_resp(250, [helo_response, AUTH_STR] + SMTP_EHLO_REGPARAMS[1:])
		
					else:
						ehlo_response = gen_resp(250, [helo_response] + SMTP_EHLO_REGPARAMS)

					client_sock.sendall(ehlo_response)
				
				elif upline.startswith('STARTTLS'):

					#Verify if ssl session has been started
					if not ssl_started:
						client_sock.sendall('220 Ready to start TLS' + CRLF)
						client_sock = ssl.wrap_socket(client_sock,server_side=True,keyfile=self.key,certfile=self.cert)
						client_file = client_sock.makefile('rb')
						
						#Set ssl communication as started 
						ssl_started = True

						#Reset mail parameters
						mailfrom = ''
						rcpttos = []
						data = ''
						mail_stage = ''
						authenticated = False

					else:
						client_sock.sendall('554 Transaction failed' + CRLF)
				
				elif upline.startswith('AUTH'):
				"""Handle you authentication types
				"""
				
				
				elif upline.startswith('MAIL FROM'):

					#Verify if user has authenticated. It only accepts authentication through SSL
					if authenticated or (client_sock.getsockname()[0] in SMTP_NOAUTH_LIST):

						#Catch user in MAIL FROM
						user = re.findall(r'MAIL FROM:<(.*?)>', line, re.I)[0]
						user = user.lower()

						#Check if user is registered
						if user in self.smtp_users:
							mailfrom = user
							mail_stage = 'MAIL_FROM'
							client_sock.sendall('250 OK' + CRLF)
						else:
							client_sock.sendall('553 Requested action not taken: mailbox name not allowed' + CRLF) 	

					else:
						client_sock.sendall('530 Authentication required' + CRLF)

				elif upline.startswith('RCPT TO'):

					#Verify if user has authenticated. 
					if authenticated or (client_sock.getsockname()[0] in SMTP_NOAUTH_LIST):

						#Verify if a mail from command has been received
						if mail_stage not in ('MAIL_FROM', 'RCPT_TO'):
							print mail_stage
							client_sock.sendall('503 Bad sequence of commands' + CRLF)
							continue

						#Catch recipient in RCPT TO
						rcpt = re.findall(r'RCPT TO:<(.*?)>', line, re.I)[0]
						rcpt = rcpt.lower()

						#Check if user is registered
						if rcpt in self.smtp_users:
							client_sock.sendall('250 OK' + CRLF)

						else:
							if ':' in rcpt:
								rcpt = rcpt.split(':')[-1]
								if rcpt in self.smtp_users:
									client_sock.sendall('250 OK' + CRLF)

								else:
									#Send relay message
									client_sock.sendall('251 User not local, will forward to ' + rcpt + CRLF)

							else:
								#Send relay message
								client_sock.sendall('251 User not local, will forward to ' + rcpt + CRLF)

						#Append recipient
						rcpttos.append(rcpt)

						#Change mail stage
						mail_stage = 'RCPT_TO'			

					else:
						client_sock.sendall('530 Authentication required' + CRLF)
		
				elif upline.startswith('DATA'):

					#Verify if user has authenticated. 
					if authenticated or (client_sock.getsockname()[0] in SMTP_NOAUTH_LIST):

						#Verify if a mail from command has been received
						if mail_stage != 'RCPT_TO':
							client_sock.sendall('503 Bad sequence of commands' + CRLF)
							continue


						#Indicate that server is ready to receive data
						client_sock.sendall('354 Start mail input; end with <CRLF>.<CRLF>' + CRLF)			

						#Verify until and EOL (.) is received
						while True:
							line = client_file.readline(MAX_LINE_SIZE + 1)
							if line == '.' + CRLF:
								break

							data += line

						data = data.rstrip(CRLF)
						#Indicate that the message has been received
						client_sock.sendall('250 OK' + CRLF)


						#Do filter operations
						filter_passed = mail_filter(mailfrom, rcpttos, data)

						if filter_passed:
							#Add mail information to the queue
							self.mails_queue.put((mailfrom, rcpttos, data))
							
						#Reset mail parameters
						mailfrom = ''
						rcpttos = []
						data = ''
						mail_stage = ''

					else:
						client_sock.sendall('530 Authentication required' + CRLF)

				elif upline.startswith('RSET'):
					
					#Verify if user has authenticated
					if authenticated or (client_sock.getsockname()[0] in SMTP_NOAUTH_LIST):
						client_sock.sendall('250 OK' + CRLF)

						#Reset mail parameters
						mailfrom = ''
						rcpttos = []
						data = ''
						mail_stage = ''

					else:
						client_sock.sendall('530 Authentication required' + CRLF)

				elif upline.startswith('VRFY'):

					#Check for authentication
					if authenticated or (client_sock.getsockname()[0] in SMTP_NOAUTH_LIST):

						#Verify if user is in local users
						user = line.rstrip(CRLF).split()[1]

						#Check if user is registered
						if user in self.smtp_users:
							client_sock.sendall('250 '+ self.smtp_users[user][1] + ' <'+ user + '>' + CRLF)

						else:
							client_sock.sendall('251 User not local' + CRLF)

					else:
						client_sock.sendall('530 Authentication required' + CRLF)


				elif upline.startswith('EXPN'):

					#Check for authentication
					if authenticated or (client_sock.getsockname()[0] in SMTP_NOAUTH_LIST):
						
						group = line.rstrip(CRLF).split()[1]
						users_ingroup = []

						for user in self.smtp_users:

							#Validate if there is any user that belongs to the group
							if group == self.smtp_users[user][2]:

								#Generate a valid item to be sent
								users_ingroup.append(self.smtp_users[user][1] + ' <' + user + '>')
 
						if users_ingroup:
							if len(users_ingroup) == 1:
								client_sock.sendall('250 ' + users_ingroup[0] + CRLF)

							else:
								client_sock.sendall(gen_resp(250, users_ingroup))

						else:
							client_sock.sendall('504 Command parameter not implemented' + CRLF)

					else:
						client_sock.sendall('530 Authentication required' + CRLF)

				elif upline.startswith('HELP'):

					#Send help information
					client_sock.sendall(gen_resp(211, SMTP_HELP.split('\n')) + CRLF)

				elif upline.startswith('NOOP'):

					#NOOP stands for No Operation. Just reply OK
					client_sock.sendall('250 OK' + CRLF)

				elif upline.startswith('QUIT'):

					#Quit from session
					client_sock.sendall('221 ' + self.fqdn + ' Service closing transmission channel' + CRLF)
					client_sock.close()
					raise socket.error('Client quitted session')

				else:
					#Send syntax error
					client_sock.sendall('500 Syntax Error, command unrecognized' + CRLF)
	
				#Reset timeout counter
				timeout_counter = 0
				

			except socket.timeout:
				
				#Add to timeout counter if variable wait response is not None
				if self.wait_response != None:
					timeout_counter += self.timeout

				continue

			except Queue.Full:
				
				#Send temporary error message when queue is full
				client_sock.sendall('452 Requested action not taken insuficient storage' + CRLF)
				continue 

			except IndexError or ValueError:

				#Indicate syntax error in command received
				client_sock.sendall('501 Syntax error in parameters or arguments' + CRLF)
				continue

			except socket.error as e:

				#Verify if it's not a timeout from SSL socket
				if e[0] == 'The read operation timed out':
					if self.wait_response != None:
						timeout_counter += self.timeout

					continue

				error_found = True
				print e, 'in', client_sock.getpeername()
				break

		if not error_found:
			client_sock.close()

	def queue_manager(self):
		
		#Manage queue function
		while self.connections_enabled:
			try:
				#Extract mail from mails queue
				mailfrom, rcpttos, data = self.mails_queue.get(timeout = self.timeout)
				self.process_message(mailfrom, rcpttos, data)

			except Queue.Empty:
				continue

	def process_message(self, mailfrom, rcpttos, data):
	
		"""This function is left open for anyone to modify it and do whatever they like with the mail received.
		"""

		#Process message received
		print mailfrom, rcpttos, data
