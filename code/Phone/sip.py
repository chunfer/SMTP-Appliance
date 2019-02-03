# -*- coding: utf-8 -*-
import sys, socket, re, random, hashlib, threading, time

class SIPSession(object):

    USER_AGENT = "SMTP Softphone"
    sip_history = {}
    
    def __init__(self, ip, username, domain, password, auth_username=False, outbound_proxy=False, account_port=5060, display_name="-"):
        self.ip = ip
        self.username = username
        self.domain = domain
        self.password = password
        self.auth_username = auth_username
        self.outbound_proxy = outbound_proxy
        self.account_port = account_port
        self.display_name = display_name
	self.cansend_audio = False
        self.is_incall = False
	self.rtp_dport = 0
        
        #Each account is bound to a different port
        self.sipsocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	self.sipsocket.bind(('', 0))
        self.bind_port = self.sipsocket.getsockname()[1]

        #Kill of sip  
        self.kill_sipsocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	self.kill_sipsocket.bind(('', 0))

        #Don't block the main thread with all the listening
        self.stage = "WAITING"
        sip_listener_starter = threading.Thread(target=self.sip_listener, args=())
        sip_listener_starter.start()
    
    def getStatus(self):
	return self.is_incall, self.cansend_audio, self.rtp_dport
            
    def H(self, data):
        return hashlib.md5(data).hexdigest()

    def KD(self, secret, data):
        return self.H(secret + ":" + data)
        
    def http_auth(self, authheader, method, address):
        realm = re.findall(r'realm="(.*?)"', authheader)[0]
        uri = "sip:" + address
        nonce = re.findall(r'nonce="(.*?)"', authheader)[0]


        if self.auth_username:
            username = self.auth_username
        else:
            username = self.username
            
        A1 = username + ":" + realm + ":" + self.password
        A2 = method + ":" + uri

        if "qop=" in authheader:
            qop = re.findall(r'qop="(.*?)"', authheader)[0]
            nc = "00000001"
            cnonce = ''.join([random.choice('0123456789abcdef') for x in range(32)])
            response = self.KD( self.H(A1), nonce + ":" + nc + ":" + cnonce + ":" + qop + ":" + self.H(A2) )
            return 'Digest username="' + username + '",realm="' + realm + '",nonce="' + nonce + '",uri="' + uri + '",response="' + response + '",cnonce="' + cnonce + '",nc=' + nc + ',qop=auth,algorithm=MD5' + "\r\n"
        else:
            response = self.KD( self.H(A1), nonce + ":" + self.H(A2) )
            return 'Digest username="' + username + '",realm="' + realm + '",nonce="' + nonce + '",uri="' + uri + '",response="' + response + '",algorithm=MD5' + "\r\n"

    def answer_call(self, sip_invite, sdp):

        call_id = re.findall(r'Call-ID: (.*?)\r\n', sip_invite)[0]
        call_from = re.findall(r'From: (.*?)\r\n', sip_invite)[0]
        call_to = re.findall(r'To: (.*?)\r\n', sip_invite)[0]
	cseq = re.findall(r'CSeq: (.*?)\r\n', sip_invite)[0]        
        cseq_number = cseq.split(" ")[0]

        reply = ""
        reply += "SIP/2.0 200 OK\r\n"
        for (via_heading) in re.findall(r'Via: (.*?)\r\n', sip_invite):
            reply += "Via: " + via_heading + "\r\n"
        record_route = re.findall(r'Record-Route: (.*?)\r\n', sip_invite)[0]
        reply += "Record-Route: " + record_route + "\r\n"
        reply += "Contact: <sip:" + str(self.username) + "@" + str(self.ip) + ":" + str(self.bind_port) + ">\r\n"
        reply += "To: " + call_to + "\r\n"
        reply += "From: " + call_from + "\r\n"
        reply += "Call-ID: " + str(call_id) + "\r\n"
        reply += "CSeq: " + cseq_number + " INVITE\r\n"
        reply += "Allow: SUBSCRIBE, NOTIFY, INVITE, ACK, CANCEL, BYE, REFER, INFO, OPTIONS, MESSAGE\r\n"
        reply += "Content-Type: application/sdp\r\n"
        reply += "Supported: replaces\r\n"
        reply += "User-Agent: " + str(self.USER_AGENT) + "\r\n"
        reply += "Content-Length: " + str(len(sdp)) + "\r\n"
        reply += "\r\n"
        reply += sdp

        self.sipsocket.sendto(reply, (self.to_server, self.account_port) )    

    def send_sip_message(self, to_address, message_body):
        call_id = ''.join([random.choice('0123456789abcdef') for x in range(32)])

        message_string = ""
        message_string += "MESSAGE sip:" + str(self.username) + "@" + str(self.domain) + " SIP/2.0\r\n"
        message_string += "Via: SIP/2.0/UDP " + str(self.ip) + ":" + str(self.bind_port) + ";rport\r\n"
        message_string += "Max-Forwards: 70\r\n"
        message_string += 'To: <sip:' + to_address + ">;messagetype=IM\r\n"
        message_string += 'From: "' + str(self.display_name) + '"<sip:' + str(self.username) + "@" + str(self.domain) + ":" + str(self.account_port) + ">\r\n"
        message_string += "Call-ID: " + str(call_id) + "\r\n"
        message_string += "CSeq: 1 MESSAGE\r\n"
        message_string += "Allow: SUBSCRIBE, NOTIFY, INVITE, ACK, CANCEL, BYE, REFER, INFO, OPTIONS, MESSAGE\r\n"
        message_string += "Content-Type: text/html\r\n"
        message_string += "User-Agent: " + str(self.USER_AGENT) + "\r\n"
        message_string += "Content-Length: " + str(len(message_body)) + "\r\n"
        message_string += "\r\n"
        message_string += message_body

        if self.outbound_proxy:
            to_server = self.outbound_proxy        
        else:
            to_server = self.domain

        self.sipsocket.sendto(message_string, (to_server, self.account_port) )
        self.sip_history[call_id] = message_string
        return call_id
        
    def send_sip_register(self, register_address, register_frequency=3600):
        call_id = ''.join([random.choice('0123456789abcdef') for x in range(32)])

        register_string = ""
        register_string += "REGISTER sip:" + self.domain + ":" + str(self.account_port) + " SIP/2.0\r\n"
        register_string += "Via: SIP/2.0/UDP " + str(self.ip) + ":" + str(self.bind_port) + ";rport\r\n"
        register_string += "Max-Forwards: 70\r\n"
        register_string += "Contact: <sip:" + str(self.username) + "@" + str(self.ip) + ":" + str(self.bind_port) + ">\r\n"
        register_string += 'To: "' + str(self.display_name) + '"<sip:' + str(self.username) + "@" + str(self.domain) + ":" + str(self.account_port) + ">\r\n"
        register_string += 'From: "' + str(self.display_name) + '"<sip:' + str(self.username) + "@" + str(self.domain) + ":" + str(self.account_port) + ">\r\n"
        register_string += "Call-ID: " + str(call_id) + "\r\n"
        register_string += "CSeq: 1 REGISTER\r\n"
        if register_frequency > 0:
            register_string += "Expires: " + str(register_frequency) + "\r\n"
        register_string += "Allow: NOTIFY, INVITE, ACK, CANCEL, BYE, REFER, INFO, OPTIONS, MESSAGE\r\n"
        register_string += "User-Agent: " + str(self.USER_AGENT) + "\r\n"
        register_string += "Content-Length: 0\r\n"
        register_string += "\r\n"

        if self.outbound_proxy:
            self.to_server = self.outbound_proxy        
        else:
            self.to_server = self.domain

        self.sip_history[call_id] = register_string

        #Reregister to keep the session alive
        if register_frequency > 0:
            reregister_starter = threading.Thread(target=self.reregister, args=(register_string, register_frequency,))
            reregister_starter.start()
        
    def reregister(self, register_string, register_frequency):

        if self.stage == "WAITING":
            self.sipsocket.sendto(register_string, (self.to_server, self.account_port) )
            time.sleep(register_frequency)
            self.reregister(register_string, register_frequency)
        
    def send_sip_invite(self, to_address, call_sdp):
        self.is_incall = True
        call_id = ''.join([random.choice('0123456789abcdef') for x in range(32)])

        invite_string = ""
	invite_string += "INVITE sip:" + to_address + ":" + str(self.account_port) + " SIP/2.0\r\n"
	invite_string += "Via: SIP/2.0/UDP " + str(self.ip) + ":" + str(self.bind_port) + ";rport\r\n"
	invite_string += "Max-Forwards: 70\r\n"
	invite_string += "Contact: <sip:" + str(self.username) + "@" + str(self.ip) + ":" + str(self.bind_port) + ">\r\n"
	invite_string += 'To: <sip:' + to_address + ":" + str(self.account_port) + ">\r\n"
	invite_string += 'From: "' + str(self.display_name) + '"<sip:' + str(self.username) + "@" + str(self.domain) + ":" + str(self.account_port) + ">\r\n"
	invite_string += "Call-ID: " + str(call_id) + "\r\n"
	invite_string += "CSeq: 1 INVITE\r\n"
	invite_string += "Allow: SUBSCRIBE, NOTIFY, INVITE, ACK, CANCEL, BYE, REFER, INFO, OPTIONS, MESSAGE\r\n"
	invite_string += "Content-Type: application/sdp\r\n"
	invite_string += "Supported: replaces\r\n"
	invite_string += "User-Agent: " + str(self.USER_AGENT) + "\r\n"
	invite_string += "Content-Length: " + str(len(call_sdp)) + "\r\n"
	invite_string += "\r\n"
	invite_string += call_sdp

        to_server = ""
        if self.outbound_proxy:
            to_server = self.outbound_proxy        
        else:
            to_server = self.domain

        self.sipsocket.sendto(invite_string, (to_server, self.account_port) )
        self.sip_history[call_id] = invite_string
        return call_id
        
    def sip_listener(self):
        
        try:
            ringing_received = False
            #Wait and send back the auth reply
            while self.stage == "WAITING":
                data, addr = self.sipsocket.recvfrom(2048)
                
                #Send auth response if challenged
                if data.split("\r\n")[0] == "SIP/2.0 407 Proxy Authentication Required" or data.split("\r\n")[0] == "SIP/2.0 407 Proxy Authentication required":
                    authheader = re.findall(r'Proxy-Authenticate: (.*?)\r\n', data)[0]
                    call_id = re.findall(r'Call-ID: (.*?)\r\n', data)[0]
                    cseq = re.findall(r'CSeq: (.*?)\r\n', data)[0]
                    cseq_number = cseq.split(" ")[0]
                    cseq_type = cseq.split(" ")[1]
                    call_to_full = re.findall(r'To: (.*?)\r\n', data)[0]
                    call_to = re.findall(r'<sip:(.*?)>', call_to_full)[0]
                    if ":" in call_to: call_to = call_to.split(":")[0]
                    
                    #Resend the initial message but with the auth_string
                    reply = self.sip_history[call_id]
                    auth_string = self.http_auth(authheader, cseq_type, call_to)

                    #Add one to sequence number
                    reply = reply.replace("CSeq: " + str(cseq_number) + " ", "CSeq: " + str(int(cseq_number) + 1) + " ")
                
                    #Add the Proxy Authorization line before the User-Agent line
                    idx = reply.index("User-Agent:")
                    reply = reply[:idx] + "Proxy-Authorization: " + auth_string + reply[idx:]
                
                    self.sipsocket.sendto(reply, addr)
                    del self.sip_history[call_id]

                elif data.split("\r\n")[0] == "SIP/2.0 401 Unauthorized":

                    authheader = re.findall(r'WWW-Authenticate: (.*?)\r\n', data)[0]
                    call_id = re.findall(r'Call-ID: (.*?)\r\n', data)[0]
                    cseq = re.findall(r'CSeq: (.*?)\r\n', data)[0]
                    cseq_number = cseq.split(" ")[0]
                    cseq_type = cseq.split(" ")[1]
                    call_to_full = re.findall(r'To: (.*?)\r\n', data)[0]
                    call_to = re.findall(r'<sip:(.*?)>', call_to_full)[0]
                    if ":" in call_to: call_to = call_to.split(":")[0]
                    
                    #Resend the initial message but with the auth_string
                    reply = self.sip_history[call_id]
                    auth_string = self.http_auth(authheader, cseq_type, call_to)

                    #Add one to sequence number
                    reply = reply.replace("CSeq: " + str(cseq_number) + " ", "CSeq: " + str(int(cseq_number) + 1) + " ")
                
                    #Add the Authorization line before the User-Agent line
                    idx = reply.index("User-Agent:")
                    reply = reply[:idx] + "Authorization: " + auth_string + reply[idx:]
                             
                    self.sipsocket.sendto(reply, addr)
                    del self.sip_history[call_id]

                elif data.split("\r\n")[0] == "SIP/2.0 403 Forbidden":
                    #Likely means call was rejected
                    self.stage = "Forbidden"
                    return False

                elif data.startswith("MESSAGE"):
                    #Extract the actual message to make things easier for devs
                    message = data.split("\r\n\r\n")[1]
                    if "<isComposing" not in message:
                        print "YOU HAVE A NEW MESSAGE..."

                elif data.startswith("INVITE"):
                    print "INCOMING CALL..."
                    call_from = re.findall(r'From: (.*?)\r\n', data)[0]
                    call_to = re.findall(r'To: (.*?)\r\n', data)[0]
                    call_id = re.findall(r'Call-ID: (.*?)\r\n', data)[0]
                    cseq = re.findall(r'CSeq: (.*?)\r\n', data)[0]

                    #Send Trying
                    trying = ""
		    trying += "SIP/2.0 100 Trying\r\n"
		    for (via_heading) in re.findall(r'Via: (.*?)\r\n', data):
		        trying += "Via: " + via_heading + "\r\n"
		    trying += "To: " + call_to + "\r\n"
		    trying += "From: " + call_from + "\r\n"
		    trying += "Call-ID: " + str(call_id) + "\r\n"
		    trying += "CSeq:"+cseq+"\r\n"
		    trying += "Content-Length: 0\r\n"
                    trying += "\r\n"
                    
                    self.sipsocket.sendto(trying, addr)

                    #Even automated calls can take a second to get ready to answer
                    ringing = ""
                    ringing += "SIP/2.0 180 Ringing\r\n"
                    for (via_heading) in re.findall(r'Via: (.*?)\r\n', data):
                        ringing += "Via: " + via_heading + "\r\n"
                    #record_route = re.findall(r'Record-Route: (.*?)\r\n', data)[0]
                    #ringing += "Record-Route: " + record_route + "\r\n"
                    ringing += "Contact: <sip:" + str(self.username) + "@" + str(self.ip) + ":" + str(self.bind_port) + ">\r\n"
                    ringing += "To: " + call_to + "\r\n"
                    ringing += "From: " + call_from + "\r\n"
                    ringing += "Call-ID: " + str(call_id) + "\r\n"
                    ringing += "CSeq:"+cseq+"\r\n"
                    ringing += "User-Agent: " + str(self.USER_AGENT) + "\r\n"
                    ringing += "Allow-Events: talk, hold\r\n"
                    ringing += "Content-Length: 0\r\n"
                    ringing += "\r\n"

                    self.sipsocket.sendto(ringing, addr)

                elif "Ringing" in data.split("\r\n")[0]:
                    ringing_received = True

                elif "OK" in data.split("\r\n")[0]:
                    cseq = re.findall(r'CSeq: (.*?)\r\n', data)[0]
                    cseq_type = cseq.split(" ")[1]
                
                    #200 OK is used by REGISTER, INVITE and MESSAGE, so the code logic gets split up
                    if cseq_type == "INVITE":
                        cseq_number = cseq.split(" ")[0]
                        contact_header = re.findall(r'Contact: <(.*?)>\r\n', data)[0]
                        #record_route = re.findall(r'Record-Route: (.*?)\r\n', data)[0]
                        call_from = re.findall(r'From: (.*?)\r\n', data)[0]
                        call_to = re.findall(r'To: (.*?)\r\n', data)[0]
                        call_id = re.findall(r'Call-ID: (.*?)\r\n', data)[0]
                        self.rtp_dport = re.findall(r'audio (.*?) RTP', data)[0]
                        self.rtp_dport = int(self.rtp_dport)
                        if ringing_received: 
                            print "CALL ACCEPTED...	", self.rtp_dport
                            self.cansend_audio = True
                        else:
                            print "EXTENSION UNAVAILABLE..."
                            self.is_incall = False

                        #Send the ACK
                        reply = ""
                        reply += "ACK " + contact_header + " SIP/2.0\r\n"
                        reply += "Via: SIP/2.0/UDP " + str(self.ip) + ":" + str(self.bind_port) + ";rport\r\n"
                        reply += "Max-Forwards: 70\r\n"
                        #reply += "Route: " + record_route + "\r\n"
                        reply += "Contact: <sip:" + self.username + "@" + str(self.ip) + ":" + str(self.bind_port) + ">\r\n"
                        reply += 'To: ' + call_to + "\r\n"
                        reply += "From: " + call_from + "\r\n"
                        reply += "Call-ID: " + str(call_id) + "\r\n"
                        reply += "CSeq: " + str(cseq_number) + " ACK\r\n"
                        reply += "User-Agent: " + str(self.USER_AGENT) + "\r\n"
                        reply += "Content-Length: 0\r\n"
                        reply += "\r\n"

                        self.sipsocket.sendto(reply, addr)
                        ringing_received = False

                    elif cseq_type == "MESSAGE":
                        print "MESSAGE RECEIVED..."
                
                elif data.startswith("BYE") or data.startswith("NOTIFY") or data.startswith("CANCEL") or data.startswith("OPTIONS"):
                    call_from = re.findall(r'From: (.*?)\r\n', data)[0]
                    call_to = re.findall(r'To: (.*?)\r\n', data)[0]
                    call_id = re.findall(r'Call-ID: (.*?)\r\n', data)[0]
                    cseq = re.findall(r'CSeq: (.*?)\r\n', data)[0]
                    cseq_number = cseq.split(" ")[0]

                    #Send OK to BYE, NOTIFY, CANCEL or OPTIONS requests
                    ok = ""
                    ok += "SIP/2.0 200 OK\r\n"
                    for (via_heading) in re.findall(r'Via: (.*?)\r\n', data):
                        ok += "Via: " + via_heading + "\r\n"
                    ok += "Contact: <sip:" + str(self.username) + "@" + str(self.ip) + ":" + str(self.bind_port) + ">\r\n"
                    ok += "To: " + call_to + "\r\n"
                    ok += "From: " + call_from + "\r\n"
                    ok += "Call-ID: " + str(call_id) + "\r\n"
                    ok += "CSeq: "+ cseq +"\r\n"
                    if data.startswith("OPTIONS"):
                        ok += "Accept: application/sdp, application/sdp\r\n"
                        ok += "Accept-Language: en\r\n"
                        ok += "Allow: INVITE, ACK, CANCEL, BYE, NOTIFY, REFER, MESSAGE, OPTIONS, INFO, SUBSCRIBE\r\n"
                        ok += "Supported: replaces, norefersub, extended-refer, timer, outbound, path, X-cisco-serviceuri\r\n"
                    ok += "User-Agent: " + str(self.USER_AGENT) + "\r\n"
                    if data.startswith("OPTIONS"):
                        ok += "Allow-Events: talk, hold\r\n"
                    ok += "Content-Length: 0\r\n"
                    ok += "\r\n"

                    self.sipsocket.sendto(ok, addr)

                    if data.startswith("CANCEL"):
                        #Send Request Terminated
			self.cansend_audio = False
                        self.is_incall = False
                        ringing_received = False
                        terminated = ok.replace("200 OK","487 Request Terminated")
			terminated = terminated.replace("CANCEL","INVITE")
                                                
                        self.sipsocket.sendto(terminated, addr)

                    if data.startswith("BYE"):
                        self.is_incall = False
			self.cansend_audio = False
                        ringing_received = False
                        print "CALL FINISHED..."
			
                elif data.split("\r\n")[0].startswith("SIP/2.0 4"):
                    print "ERROR IN CALL..."

            sys.exit()

        except Exception as e:
            print e
            sys.exit()
       
    def close(self):
        #Close listener and reregister threads
        self.stage = "BYE"
        self.kill_sipsocket.sendto('SIP session finished...',(self.ip, self.bind_port))
        time.sleep(0.01)
        self.sipsocket.close()
                
