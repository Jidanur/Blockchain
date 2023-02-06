
import hashlib,socket,sys,json,os,uuid,threading,time,random
import argparse

from time import sleep

#######################   MINING THREADS  #############################

#words = open('/usr/share/dict/words')
# allWords = list(words.readlines())
# words.close()
def sendWords():
    sleep(2) # wait some time to start
    while(True):
        for _ in range(5):
            content = {
                "type":"NEW_WORD",
                "word":random.choice(allWords).strip()
                }
            print(content)
            peer_socket.sendto(json.dumps(content).encode(), ("localhost",peerPort)) # send words to myself
        time.sleep(60*60)


def mineBlocks():
    sleep(5) # wait some time to build the chain and start
    mineWords = []
    while True:
        if len(wordsToMine) > 0:
            if len(mineWords) > 0:
                mineWords = wordsToMine.copy()  # copy new word received 
                wordsToMine.clear() # clear old words
                mineWords = mineWords[-10:]  # if there are more words because of slow mining but our limit is 10 messeges so just mine last words 10 words
            old_height = len(chain)
            
            for nonce in range(10**40):
                
                if(len(chain) > old_height):
                    break
                
                hashBase = hashlib.sha256()
                # get the most recent hash
                global last_block_hash

                if last_block_hash != '': # check if not mining genesis 
                    # add it to this hash
                    hashBase.update(last_block_hash.encode())            

                # add the miner
                hashBase.update("JIDAN".encode())

                # add the messages in order
                for m in mineWords:                
                    hashBase.update(m.encode())

                # add the nonce
                hashBase.update(str(nonce).encode())   

                # get the pretty hexadecimal
                hash = hashBase.hexdigest()                   

                # is it difficult enough? then announce to all peers including myself
                if hash[-1 * DIFFICULTY:] == '0' * DIFFICULTY:
                    announce_msg = {
                        "type": "ANNOUNCE",
                        "height": len(chain),
                        "minedBy": "JIDAN",
                        "nonce": str(nonce),
                        "messages": mineWords,
                        "hash": hash
                    }

                    force_consensus ={
                        "type": "CONSENSUS"
                        }

                    print(announce_msg)
                    peer_socket.sendto(json.dumps(announce_msg).encode(), ("localhost",peerPort)) # send to myself for revalidation and add to chain

                    #announce to all known peers
                    for peer_addr in peer_list:
                        peer_socket.sendto(json.dumps(announce_msg).encode(), peer_addr)
                        peer_socket.sendto(json.dumps(force_consensus).encode,peer_addr)
                    
                    mineWords.clear()
                    
                    break # go out of loop then start mining different words

        

########################################################################

################################## CONSENSUS THREAD ################################
#do census at start and if out of sync then add the new blocks
def do_consensus():
    #start consensus thread if we have minimum number of peers
    global MIN_PEER
    while len(peer_list) < MIN_PEER:
        pass
    
    stats_req = {"type": "STATS"}
    json_stats_req = json.dumps(stats_req)

    # reset global values to start new consensus
    stats_results.clear()
    curr_peer_stats.clear()
    timedOut_peers = 0

    global ifconsensus
    ifconsensus = True

    print("consensus in progress")

    #run till stats reply collected from all peers except timed out peers
    #stats reply will be catched by main thread
    curr_peer_count = len(peer_list)

    while len(stats_results) < curr_peer_count - timedOut_peers:
        # send stat req to all known peers
        for peer_address in peer_list:
            if peer_address not in curr_peer_stats: # peer already sent reply don't ask for stat req
                peer_socket.sendto(json_stats_req.encode(),peer_address)
        
        #sleep(0.1) # wait some time for main thread to catch the stats replies


    ifconsensus = False  # done collect stat_reply from peers
    print("consensus DONE")

    #find the popular or longest chain
    popular_chain_height = 0 #most populer chain height
    maxfrequency = 0 
    for curr_height in stats_results:
        count = stats_results.count(curr_height) # find the frequency of current height
        if count > maxfrequency: 
            popular_chain_height = curr_height
            maxfrequency = count
        elif maxfrequency == count and maxfrequency != 0: # if tied with most popular
            if curr_height > popular_chain_height: #keep the longest 
                popular_chain_height = curr_height
    
    # find the majority peers who have the updated chain
    majority_peers = []
    for idx in range(len(curr_peer_stats)):
        if stats_results[idx] == popular_chain_height:
            majority_peers.append(curr_peer_stats[idx])


    #block_req message
    block_req = {
        "type": "GET_BLOCK",
        "height": len(chain)
    }
    
    #if peer chain has less blocks than the majority
    # keep requesting blocks till we have the updated chain 
    while len(chain) < popular_chain_height:
        #request blocks in load balance
        block_idx = len(chain) # start index of requesting block  
        #requesting next set of blocks from peers where main thread will catch the get_block_reply and add to chain
        for peer_address in majority_peers:
            block_req["height"] = block_idx
            block_idx += 1
            sendTO = (json.dumps(block_req)).encode()
            peer_socket.sendto(sendTO,peer_address)
        sleep(0.1)
        

    #run consensus every 60s
    sleep(60)# sleep for 60s
    do_consensus()

####################################################


############################ FLOODING THREAD #####################################
#flooding thread which sends flood when joining and sends flood to all known peers every 30s
def flood_thread():
    flood_msg = {
        "type": "FLOOD",
        "host" : peerhost,
        "port" : peerPort,
        "id" : str(uuid.uuid1()),
        "name" : "JIDAN"
    }
    #send 1st flood msg to well-know peer when joining the network
    flood_msg_bytes = json.dumps(flood_msg)
    if known_peer:
        peer_socket.sendto(flood_msg_bytes.encode(),known_peer)
    
    #every 30s flood so we connected to known peers
    while True:
        sleep(30.0) # sleep for 30s
        if len(peer_list) != 0:
            flood_msg["id"] = str(uuid.uuid1())
            flood_msg_bytes = json.dumps(flood_msg)
            for peer_address in peer_list:
                peer_socket.sendto(flood_msg_bytes.encode(),peer_address)

#################################################################################    


############################ BLOCK VALIDATION #####################################
#verify the block and add to the top of chain
def validate_block(curr_block,height):
    block={
        "height": curr_block["height"],
        "minedBy": curr_block["minedBy"],
        "nonce": None,
        "messages": None,
        "hash": None
    }
    
    #block should only add to the end of chain
    if len(chain) == height and curr_block["height"] != None:
        valid = True # validation flag

        #verify nonce - should be less than 40 characters
        if len(curr_block["nonce"]) >= 40:
            valid = False # return if invalid

        #verify messages - should be less than 10 messages and every message should be <= 20
        if len(curr_block["messages"]) <= 10:
            for i in curr_block["messages"]:
                if len(i) > 20:
                    valid = False
            
        # if messages and nonce were valid then verify hash 
        if valid:
            global last_block_hash
            hashBase = hashlib.sha256() 
            # if not genesis block
            if(height > 0):
                lastHash = last_block_hash
                hashBase.update(lastHash.encode())  
            # add the miner
            hashBase.update(curr_block['minedBy'].encode())
            # add the messages in order
            for m in curr_block['messages']:                
                hashBase.update(m.encode())
            # add the nonce
            hashBase.update(curr_block["nonce"].encode())   
            # get the pretty hexadecimal
            hash = hashBase.hexdigest()
            if hash[-1 * DIFFICULTY:] == '0' * DIFFICULTY:
                if hash == curr_block['hash']:
                    block["nonce"] = curr_block["nonce"]
                    block["messages"] = curr_block["messages"]
                    block["hash"] = hash
                    last_block_hash = hash # update last block hash
                    #add block to chain 
                    chain.append(block)

#################################################################################
        

################################ GET BLOCK REPLY  ###########################################
#returns the block at index height
def get_block(height):
    get_block_reply ={
        "type": "GET_BLOCK_REPLY",
        "height": None,
        "minedBy": None,
        "nonce": None,
        "messages": None,
        "hash": None,
    }
    #checking if I have the requested block in the chain
    if height < len(chain) and height > 0:
        get_block_reply["height"] = chain[height]["height"]
        get_block_reply["minedBy"] = chain[height]["minedBy"]
        get_block_reply["nonce"] = chain[height]["nonce"]
        get_block_reply["messages"] = chain[height]["messages"]
        get_block_reply["hash"] = chain[height]["hash"]

    return get_block_reply

#################################################################################


############################# STATS REPLY #####################################
#returns the stats for last block height and hash in the chain
def get_stats():
    stats_reply  = {
        "type": "STATS_REPLY",
        "height": 0,
        "hash": None 
    }

    #checks if chain is initialized
    if len(chain) != 0:
        last_block = chain[-1]
        stats_reply["height"] = last_block["height"] + 1
        stats_reply["hash"] = last_block["hash"]
    
    return stats_reply
#################################################################################


############################# HANDLE FLOOD MESSAGE AND SENDS FLOOD_REPLY #######################################
# FLOOD REAPTER  IMPLEMENTED IN THIS FUNCTION
#send flood reply
recent_repeated_flood_IDs = []

def flood_reply(request):

    #if started with initial peer
    if len(peer_list) == 0:
        add_peer(request)


    #flood repeater
    global recent_repeated_flood_IDs
    #flood wasn't received before then repeat the flood msg to all known peers
    if "id" in request:
        if request["id"] not in recent_repeated_flood_IDs:
            repeat_msg = json.dumps(request)
            for peer_address in peer_list:
                peer_socket.sendto(repeat_msg.encode('utf-8'),peer_address)

            if len(recent_repeated_flood_IDs) > len(peer_list): # clear recent_flood_ids after a while
                recent_repeated_flood_IDs.clear()

            recent_repeated_flood_IDs.append(request["id"]) # add the flood id just repeated now

    ###################################

    flood_reply ={
        "type": "FLOOD-REPLY",
        "host" : peerhost,
        "port" : peerPort,
        "name" : "JIDAN"
    }

    orig_addr = (request["host"],request["port"]) #gets the orignators address to send flood_reply because flood could be sent by repeater

    #if peer exists in the array
    peer_idx = -1
    for i in range(len(peer_list)):
        if peer_list[i][0] == orig_addr[0] and peer_list[i][1] == orig_addr[1]:
            peer_idx = i

    #update the curr_time of peer
    curr_time = time.time()
    if peer_idx != -1:
        peer_list_lastPing[peer_idx][1] = curr_time

    return flood_reply, orig_addr

#################################################################################
    

############################## HANDLE FLOOD REPLY ######################################
# when peers sends flood reply we add them to our peerlist if not already added
def add_peer(req):
    curr_peer = (req["host"], req["port"])
    peer_exists = False

    for peer in peer_list:
        if peer[0] == curr_peer[0] and peer[1] == curr_peer[1]:
            peer_exists = True

    if not peer_exists and curr_peer[1] != peerPort:
        peer_list.append(curr_peer)
        peer_list_lastPing.append([curr_peer,0])

#################################################################################

#initial socket to listen for webPage request
def listen_web():   
    while True:
        try: 
            print("accepted")
            conn, web_addr = web_socket.accept()
            handle_get(conn,web_addr)
        except Exception as e:
            print(e)
            web_socket.close()
            os._exit(1)



def handle_get(client, addr):
    request = client.recv(1024)
    request = request.decode("utf-8")

    print(request)

    headers = request.split('\n')
    req_type = headers[0].split(" ")[0]
    

    response = "HTTP/1.1 200 OK\n"
    contents = ""

    if req_type == "GET":
        filename = headers[0].split()[1]
        try:
            if filename == "/chain":
                contents = json.dumps(chain)
                response += "Content-Type: application/json"
            elif filename == "/peerList":
                contents = json.dumps(peer_list)
                response += "Content-Type: application/json"
            else:
                file = open("index.html")
                contents = file.read()
                file.close()

            
        except Exception as e:
            print(e)
            response = 'HTTP/1.1 404 NOT FOUND\n\nFile Not Found'
        else:
            response += "content-length: " + str(len(contents)) +"\n"
            response += "\n\n" + contents
    
    client.sendall(response.encode("utf-8"))
    client.close()
        





########################## REQUEST HANDLER ############################
# this function handle's all requests in a sperate thread
def handle_requests(request,addr):   
    request = request.decode('utf-8')

    print(request)

    req = {}
    reply = {}

    #checking if bad message
    try:
        req = json.loads(request)
        req_type = req["type"]
    except Exception as e:
        print(e)
        print("bad message from peer")
        sys.exit(0) #close thread

    print(req)

    #if get new word then add the word to mine
    if(req_type == "NEW_WORD"):
        wordsToMine.append(req["word"])

    # if stats reply received 
    if(req_type == "STATS_REPLY"):
        #update stats result and peer who sent so it can be used in consensus thread
        if addr not in curr_peer_stats:
            curr_peer_stats.append(addr)
            stats_results.append(req["height"])
        sys.exit(0) # no need to send reply for this so close the thread


    # if gets block reply then validate the block and add to the chain
    if(req_type == "GET_BLOCK_REPLY"):
        validate_block(req,req["height"])
        sys.exit(0) # no need to send reply for this so close the thread
    
    #handles flood_reply where we add to own peer_list if not added before
    if(req_type == "FLOOD-REPLY"):
        add_peer(req)
        sys.exit(0) # no need to send reply for this so close the thread

    #if stats are requested from peers
    if(req_type == "STATS"):
        reply = get_stats()
    
    #if blocks are requested from peers if available then send else reply with none values
    if(req_type == "GET_BLOCK"):
        reply = get_block(req["height"])

    #if a new block is announced then check and validate if it can be added to the top of the chain 
    if(req_type == "ANNOUNCE"):
        validate_block(req,req["height"])
        sys.exit(0) # no need to send reply for this so close the thread

    # if flood message received then reply to the originator and repeat the flood message to know peers
    if(req_type == "FLOOD"):
        reply,addr = flood_reply(req)
        pass

    #do force consensus
    if(req_type == "CONSENSUS"):
        pass

    reply = json.dumps(reply)

    if peerPort != addr[1]: # does not send message to own port if sent causes too much flood message
        peer_socket.sendto(reply.encode('utf-8'),addr)
    
    sys.exit(0) # exit thread after done with request

#################################################################################

########################## Arguments handler ############################

def args_handle(paramters):
    parser = argparse.ArgumentParser(description="Process input parameters")
    parser.add_argument("-p", required=True ,help="port number current process socket gonna bind with" ,dest='port', nargs=1, type=int)
    parser.add_argument("-m","--mining", help="if peer going to mine", action="store_true")
    parser.add_argument("-c","--cuda", help="if use CUDA for mining", action="store_true")

    #Either of them must be given in order to start the blockchain
    group = parser.add_mutually_exclusive_group(required = True)
    group.add_argument("-k", help=" well-known peer host and port who is part of blockchain", nargs=2 ,dest="known_peer")
    group.add_argument("-i", help="intial peer: if this is the first peer which is starting the blockchain", nargs= 1 , dest="webPort", type=int)


    args = parser.parse_args(paramters)
    return args


########################## ################### ############################




'''-----------------------------MAIN THREAD-------------------------------------'''

chain= [{    "height": 7,"minedBy": "MAXWELL","nonce": 383748,"messages": ["Hello, how are you?","I hope you are doing well."],
    "hash": "0x7f8a938d27f9c4938dkjfd98d8a39487"},
    {
    "height": 9,
    "minedBy": "ASHLEY",
    "nonce": 294837,
    "messages": [
      "Good morning!",
      "It's a beautiful day today."
    ],
    "hash": "0x9d8fh9e8d9hf9d8f9h9d9f8d8a399df8"
  }]   # blocks list
peer_list = []  # list of peers
peer_list_lastPing = [] # last ping time when peers sent flood


last_block_hash = "" # last block's hash
DIFFICULTY = 9 # dificulty for block hashing



#process the arguments
arguments = args_handle(sys.argv[1:])

#port 
peerhost = socket.gethostname() # host of current server this code is running
peerPort = arguments.port[0]

print(peerhost,peerPort)

peer_socket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
peer_socket.bind(("",peerPort))

# know peer where we connect our network from
known_peer = ()

#if initial blockchain peer then no known peers
if arguments.webPort:
    print("Initial peer, {}".format(arguments.webPort[0]))
    web_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    web_socket.bind(("localhost", arguments.webPort[0]))

    #dedicated thread to handle web UI requests
    webPage_thread = threading.Thread(target=listen_web)
    webPage_thread.start()

    #start listening
    web_socket.listen(1)
else:
    known_peer = (arguments.known_peer[0],int(arguments.known_peer[1]))  



####### flooding thread start################
#flooding thread will send flood to all known peers in peer_list every 30s
f_thread = threading.Thread(target=flood_thread)
f_thread.start()

#######################

####### consensus thread start################
#this thread will run consensus every 1 mins if we have MIN_PEERS
ifconsensus = False  # flag for if consensus in progress 
MIN_PEER = 3  # min number of peer to start consensus

stats_results=[] #stats-reply stored 
curr_peer_stats = [] #peers who already sent stats-reply
timedOut_peers = 0 # num of peers who timed out so we don't care about their response

consensus_thread = threading.Thread(target=do_consensus)
consensus_thread.start()
#############################################
peer_lock = threading.Lock()


####### MINING THREAD################
# wordsToMine = [] # list of words to mine

# word_adder = threading.Thread(target=sendWords)
# word_adder.start()

# mining_thread = threading.Thread(target=mineBlocks)
# mining_thread.start()

######################################


while True:
    # check if peers last flood was before 1 min then remove from peer_list
    curr_time = time.time()
    for curr_peer in peer_list_lastPing:
        if curr_peer[1] != 0: # have initialized
            diff = curr_time - curr_peer[1]
            if diff >= 60:
                print("kicked peer",curr_peer)
                peer_list.remove(curr_peer[0])
                peer_list_lastPing.remove(curr_peer)
    

    #if consensus going on
    if ifconsensus:
        peer_socket.settimeout(1) # set timeout to 1s
    else:
        peer_socket.settimeout(None) # set timeout to default

    try: 
        data,addr = peer_socket.recvfrom(1024)

        # if there are more than 50 concurrent threads running slow down---need to chill for a bit
        if(threading.activeCount() > 50):
            sleep(0.1) # give some time for threads to finish 

        handle_thread = threading.Thread(target=handle_requests,args=(data, addr))
        handle_thread.start()

    except socket.timeout as e:
        timedOut_peers += 1
        print("peer timed out")

    except Exception as e:
        print(e)
        peer_socket.close()
        os._exit(1)

    except KeyboardInterrupt as e:
        print(peer_list)
        print("numOfPeers-",len(peer_list))
        print("chain length-",len(chain))
        peer_socket.close()
        os._exit(1)

    
'''--------------END -------------------'''
    





