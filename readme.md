# Overview
The `blockchain.py` code implements a peer in a blockchain network using Python3. The code can be run with several command line arguments to configure the behavior of the peer. The peer can be started as a miner by using the `-m` option and can connect to other peers through a specified port with the `-p` option. The `-i` option is used to specify the web page port for the peer, and the`-k` option is used to specify a well-known peer that is already part of the blockchain network.

The peer runs multiple threads to handle various tasks, including listening for incoming messages, mining, sending messages, and validating the blockchain. The main thread constantly monitors incoming messages and creates a new thread to handle each message received. The `do_consensus()` thread runs every minute to ensure the peer has the majority chain. If the local chain is outdated, the consensus thread requests blocks from peers with the majority chain and adds them to the local chain after validation.

The `listen_web()` thread opens a web page for the peer, which displays the current state of the blockchain and the list of connected peers. The peer also implements mechanisms to clear up inactive peers and validate the blockchain by checking the blocks received from other peers. The consensus mechanism is done by comparing the length and validity of the chains among all connected peers, and the majority chain is chosen as the consensus. This mechanism helps ensure the integrity and consistency of the blockchain network.


# Running the code-
## Arguments
-i <webPage_port>: if the peer starts the blockchain, it should use this along with a port to open a TCP connection.

-k <knowpeer host>: well-known peer host and port who is part of the blockchain.

-p <port>: port number that this program's socket will bind with.

-m: if the peer is going to be used for mining.

-c: enables CUDA for mining.

**Initial Peer Example with Miner**

`python3 blockchain.py -i 8001 -p 8999 -m`


The above command starts the peer with a webPage at localhost:8001 that can be connected to the chain through the 8999 port. The peer will also be used for mining.
    
**General Peer Example**

`python3 blockchain.py -k localhost 8999 -p 8002`

The above command connects to peer 8999 on localhost through the 8002 port.



# Implementation details 

## Always-Running Threads

- Main thread: always running for receiving messages from peers.
- listen_web() thread: running if the peer is the initial peer, then added which shows the web page for the chain and peer list through TCP.
- flood_thread(): a scheduled task that runs every 30 seconds and sends flood to the known peer when joining.
- do_consensus() thread: also a scheduled task that runs every 1 minute as long as there is a minimum number of peers, which is set to 3 by default. Check MIN_PEER to change it in the Main Thread.
- Mining thread: check mineBlocks() if a new word is received for mining by the main thread, mining starts.
- sendWords() thread: this thread sends myself new word messages every hour which then the miner thread collects the words and tries to mine.

- Request Handling Thread -Every time the main thread receives a response from any peers, it creates a new thread and handles it.

## Functionality
- Clear up peers: the Main thread always checks peers' last ping time. If it's more than 1 minute, we remove them from our peer list. The last ping time is updated whenever peers send flood, check flood_reply().
- Verify chain: check validate_block().
        Takes the block_reply and height as parameters.
        If height is the end of the chain, only then run validation and add it.
        The chain is validated end-to-end since we only insert a block in the chain if it's valid.
- Consensus is done in the do_consensus() thread.
        If we have a minimum number of peers, which is 3 by default, we send a stats request, which is received by the main thread. If all peers send a stats reply except they time out, we collect that in a global list and run consensus.
        Chooses the majority chain with stats reply height's we get. If tied with the majority, then keep the longest and hold the peers' address in a list who have the majority or longest chain.
        If the current length of the chain is less than the consensus chain height, only then ask for get-block.
        The next set of blocks starting from the last empty spot in the chain is requested from all peers who hold the majority chain, and the main thread gets the



