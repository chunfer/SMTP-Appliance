# Servers library ^
# -*- coding: utf-8 -*-
"""
This is the server library version 1.0.0

Along with the code you can see how to:

	- Manage socket timeouts
	- Handle and create your own exceptions
	- Manage queues
	- Handle library re for regular expressions
	- Develop your own server
        - Use the integrated SMTP Server built-in.

This library is thought to be used as a base for server development with python.
I hope you enjoy this library and look forward to developing production servers.

Best regards,
	Juan Fernando Montufar Juarez

Comments: juanfmontufarjuarez@gmail.com 
"""

# Basic libraries
import sys, os, base64, re, time, socket, threading, struct, Queue

#Server exceptions
class ServerException(Exception):
	"""Base class for all server exceptions raised""" 

class ServerInitError(ServerException):
	"""Exception for initialization errors"""
		
#General server constants
DEFAULT_TIMEOUT = 5
PROTO_TYPES = {'TCP': socket.SOCK_STREAM, 'UDP': socket.SOCK_DGRAM}

class Server(object):
	#General server class.

	def __init__(self, port, timeout = DEFAULT_TIMEOUT, greeting_msg = '', proto = 'TCP'):

		#Server validation
		if type(port)!=int or type(timeout)!=int or not proto in PROTO_TYPES:
			raise ServerInitError('Bad arguments given during initialization...')
			sys.exit()

		#Set own variables
		self.port = port
		self.greeting_msg = greeting_msg
		self.timeout = timeout
		self.connections_enabled = True

		#Initiate socket
		try:
			server_sock = socket.socket(socket.AF_INET, PROTO_TYPES[proto])
			server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
			server_sock.bind(('', self.port))
			server_sock.listen(5)
		
			#set timeout socket
			server_sock.settimeout(self.timeout)

			#start listening
			incoming_connection_starter = threading.Thread(target=self.incoming_connection, args=(server_sock,))
			incoming_connection_starter.start()
		
		except socket.error as e:

			e = str(e)
			#Find out if error shows that the address is already in use
			if 'Address already in use' in e:

				#Add recommendation for linux users
				e += '\n Run command \'lsof -i:' + str(port) + '\' to find out the PID blocking the port and stop it.'

			raise ServerInitError(e)
			sys.exit()

 
	def incoming_connection(self, server_sock):
		error_found = False

		#General income connection handler
		while self.connections_enabled:
			try:
				#Listen to incoming connections
				client_sock, client_address = server_sock.accept()
				
				#Set timeout for client socket
				client_sock.settimeout(self.timeout)

				#Send greeting message if it's not empty
				if len(self.greeting_msg) != 0:
					client_sock.sendall(self.greeting_msg)

				#Create a thread to handle each connection
				transactions_manager_starter = threading.Thread(target=self.transactions_manager, args=(client_sock,))
				transactions_manager_starter.start()

			except socket.timeout:
				continue

			except socket.error as e:
				error_found = True
				print e, 'in', server_sock.getpeername()
				break

		if not error_found:
			server_sock.close()


	def transactions_manager(self, client_sock):
		"""Transmit any message. This is left open for several server types"""

	def close(self):
		#Close connections
		self.connections_enabled = False
		time.sleep(self.timeout * 1.1)

#SMTP server constants
CRLF = '\r\n' #End of line
SMTP_PORT = 25 #Default SMTP port
MAX_LINE_SIZE = 4194304 #Máximum amount of bytes that can be received
SMTP_MAXWAIT_TIME = 300 #Máximum amount of time (in seconds) to wait for receiving information for each client
SMTP_EHLO_REGPARAMS = ['SIZE ' + str(MAX_LINE_SIZE), '8BITMIME','HELP'] #EHLO regular parameters
SMTP_HELP = """This is SMTP Sever version 1.0.0
Commands available:
      HELO    EHLO    MAIL    RCPT    DATA
      RSET    NOOP    QUIT    HELP    VRFY
      EXPN
To report bugs in the implementation send email to:
    juanfmontufarjuarez@gmail.com.
Best regards to you programmer.
End of HELP info"""

#SMTP filter requirements
from collections import OrderedDict

#SMTP filter variables
MAX_ITEMS_SIZE = 100 #Máximum messages the filter can receive
DEL_ALLITEMS_GAP = 10800 #Timeframe (in seconds) to delete all elements from the filter dictionary
DEL_ITEM_GAP = 1800 #Timeframe (in seconds) to delete repeated items in filter
DONT_PROCESS_TUPLE = () #Messages not to be processed


class SMTPServer(Server):
	#Server for handling SMTP protocol
	SMTP_USERS = OrderedDict([('969.980.usac@gmail.com',('Juan Montufar', 'Admins')), ('alexmontufar16@gmail.com',('Alex Montufar','My_Group')), ('dpajiflex@hotmail.com',('Luis Montufar','My_Group'))])

	def __init__(self, wait_response = SMTP_MAXWAIT_TIME, port = SMTP_PORT, timeout = DEFAULT_TIMEOUT):

		#Validate wait_response argument. (set wait_response as None is valid and is taken as no cause disconnections)
		if wait_response != None:
			if type(wait_response) != int:
				raise ServerInitError('Bad arguments given during initialization...')
		
		#Set amount of time to wait for receiving a command. If the time has expired will close the connection
		self.wait_response = wait_response

		#Initiate to create a queue based on each mail received
		self.mails_queue = Queue.Queue()
 

		#Generate greeting message
		self.fqdn = socket.getfqdn()
		greeting_msg = '220 ' + self.fqdn + ' Service ready ESMTP' + CRLF

		#Startup time filter variables 
		self.filter_dict = OrderedDict() #Filter dictionary (format = mail_data: (time_value, msg_wasprocessed))
		self.prevmsg_time = time.time()

		#Initiate server
		Server.__init__(self, port, timeout, greeting_msg)

		#Initiate thread for handling queue
		queue_manager_starter = threading.Thread(target=self.queue_manager)
		queue_manager_starter.start()

	def add_user(self, new_user, username = ' ', groupname = 'My_Group'):

		#Add user to dictionary
		self.SMTP_USERS[new_user] = (username, groupname)

	def update_user(self, new_user, position = 0):

		#Update user by replacing it in the dictionary
		new_SMTP_USERS = OrderedDict()
		positions_counter = 0

		for user in self.SMTP_USERS:
			if positions_counter == position:
				new_SMTP_USERS[new_user] = self.SMTP_USERS[user]

			else:
				new_SMTP_USERS[user] = self.SMTP_USERS[user]

			positions_counter += 1

		self.SMTP_USERS = new_SMTP_USERS

	def setwait(self, wait_response):
		self.wait_response = wait_response

	def transactions_manager(self, client_sock):
		""" This function is meant to be used to manage all SMTP transactions for each client.
		RFC followed:
			- RFC 5321: For general SMTP transactions
			
		"""

		def mail_filter():
			"""Filter function.
			Will decide if the message received can be added to the mail queue.
			Boolean value must be returned
			"""
			test_string = '' #String to be tested
			current_time = time.time()
			
			#Try to find subject to add in time filter dictionary
			subject = re.findall(r'Subject: (.*?)\n', data) 
			
			if subject:
				test_string = subject[0]

			else:
				test_string = data

			if test_string in DONT_PROCESS_TUPLE:

				#Deny to add to the queue
				return False

			#Check if the time frame between consecutive messages are greater than the delete all items gap
			if current_time - self.prevmsg_time > DEL_ALLITEMS_GAP:
				del self.filter_dict
				with self.mails_queue.mutex: self.mails_queue.queue.clear()
				self.filter_dict = OrderedDict()
				self.filter_dict[test_string] = (current_time, False)
				return True

			#Check if message was received previously
			if test_string not in self.filter_dict:

				#Verify if the maximum amount of items heve been reached
				if len(self.filter_dict) == MAX_ITEMS_SIZE:

					#Check if first message in filter was already processed
					if self.filter_dict.values()[0][1]:

						#Delete first element and add a new element
						del self.filter_dict[self.filter_dict.keys()[0]]
						self.filter_dict[test_string] = (current_time, False)
						return True

					else:
						return False

				else:
					self.filter_dict[test_string] = (current_time, False)
					return True

			else:

				#Verify if the time frame between same messages received are greater than the delete item gap. 
				if current_time - self.filter_dict[test_string][0] > DEL_ITEM_GAP:
					del self.filter_dict[test_string]
					self.filter_dict[test_string] = (current_time, False)
					return True

				else:
					return False


		error_found = False

		#Initialize arguments for each client
		mailfrom = ''
		rcpttos = []
		data = ''
		mail_stage = '' #Identifier of mail stage
		challenge = '' #Random string for CRAM MD5
		timeout_counter = 0 #Counter (in seconds) of timeouts
		peername = ''
		helo_response = self.fqdn + ' Hello'

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

					#Send EHLO with parameters of this SMTP server
					ehlo_response = gen_resp(250, [helo_response] + SMTP_EHLO_REGPARAMS)
					client_sock.sendall(ehlo_response)
				
				elif upline.startswith('MAIL FROM'):

					#Catch user in MAIL FROM
					user = re.findall(r'<(.*?)>', line, re.I)[0]
					user = user.lower()
					mailfrom = user
					mail_stage = 'MAIL_FROM'
					client_sock.sendall('250 OK' + CRLF)

				elif upline.startswith('RCPT TO'):

					#Verify if a mail from command has been received
					if mail_stage not in ('MAIL_FROM', 'RCPT_TO'):
						client_sock.sendall('503 Bad sequence of commands' + CRLF)
						continue

					#Catch recipient in RCPT TO
					rcpt = re.findall(r'<(.*?)>', line, re.I)[0]
					rcpt = rcpt.lower()

					#Check if user is registered
					if rcpt in self.SMTP_USERS:
						client_sock.sendall('250 OK' + CRLF)

					else:
						if ':' in rcpt:
							rcpt = rcpt.split(':')[-1]
							if rcpt in self.SMTP_USERS:
								client_sock.sendall('250 OK' + CRLF)

							else:
								#Send relay message
								client_sock.sendall('553 Requested action not taken: mailbox name not allowed' + CRLF)

						else:
							#Send relay message
							client_sock.sendall('553 Requested action not taken: mailbox name not allowed' + CRLF)

					#Append recipient
					rcpttos.append(rcpt)

					#Change mail stage
					mail_stage = 'RCPT_TO'


				elif upline.startswith('DATA'):

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

					data = data.replace(CRLF, '\n')

					#Indicate that the message has been received
					client_sock.sendall('250 OK' + CRLF)

					#Do filter operations
					filter_passed = mail_filter()
					self.prevmsg_time = time.time()

					if filter_passed:
						#Add mail information to the queue
						self.mails_queue.put((mailfrom, rcpttos, data))
						
					#Reset mail parameters
					mailfrom = ''
					rcpttos = []
					data = ''
					mail_stage = ''

				elif upline.startswith('RSET'):

					#Send OK only
					client_sock.sendall('250 OK' + CRLF)

					#Reset mail parameters
					mailfrom = ''
					rcpttos = []
					data = ''
					mail_stage = ''

				elif upline.startswith('VRFY'):

					#Verify if user is in local users
					user = line.rstrip(CRLF).split()[1]

					#Check if user is registered
					if user in self.SMTP_USERS:
						client_sock.sendall('250 '+ self.SMTP_USERS[user][0] + ' <'+ user + '>' + CRLF)

					else:
						client_sock.sendall('251 User not local' + CRLF)



				elif upline.startswith('EXPN'):

					#Check out group
					group = line.rstrip(CRLF).split()[1]
					users_ingroup = []

					for user in self.SMTP_USERS:

						#Validate if there is any user that belongs to the group
						if group == self.SMTP_USERS[user][1]:

							#Generate a valid item to be sent
							users_ingroup.append(self.SMTP_USERS[user][0] + ' <' + user + '>')

					if users_ingroup:
						if len(users_ingroup) == 1:
							client_sock.sendall('250 ' + users_ingroup[0] + CRLF)

						else:
							client_sock.sendall(gen_resp(250, users_ingroup))

					else:
						client_sock.sendall('504 Command parameter not implemented' + CRLF)


				elif upline.startswith('HELP'):

					#Send help information
					client_sock.sendall(gen_resp(211, SMTP_HELP.split('\n')))

				elif upline.startswith('NOOP'):

					#NOOP stands for No Operation. Just reply OK
					client_sock.sendall('250 OK' + CRLF)

				elif upline.startswith('QUIT'):

					#Quit from session
					client_sock.sendall('221 ' + self.fqdn + ' Service closing transmission channel' + CRLF)
					peername = client_sock.getpeername()
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
				print 'Syntax error found in: ', line
				client_sock.sendall('501 Syntax error in parameters or arguments' + CRLF)
				continue

			except socket.error as e:
				error_found = True
				if peername:
					print e, 'in', peername
				
				else:
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
