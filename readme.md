
# running the code-
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

    Structure-
        # Always running threads- 
            * Main thread is always running for receving messages from peers

            * listen_web() thread running if the peer is the initital peer then added which shows the webPage for chain and peerList through TCP 

            * flood_thread() is a scheduled task which runs every 30s and sends flood to know peer when joining

            * do_consensus() thread is also a scheduled task whichs runs every 1 min as long as we have minimum number of peers which is set to 3 by default check MIN_PEER to change it in Main Thread 

            * mining thread - check mineBlocks() if new words is received for mining by main thread mining starts

            * sendWords() thread - this thread sends myself new word messages every hour which then miner thread collects the words and tries to mine

        # request handling thread - 
            * everytime main thread receives response from any peers it creates a new thread and handles it 



    - Clear up peers - Main thread always check peers last ping time if its more than 1 min we remove them from our peer list. last ping time is updated whenever peers send flood check flood_reply() 

    - Verify chain - check validate_block()
        - takes the block_reply and height as parameter
        - if height is the end of the chain only then run validate and add it
        - chain is validated end-end since we only insert block in chain if its valid  


    - Consensus is done in do_consensus() thread.
        - if we have minimum peers which is 3 by default we send stats request which is received by main thread if all peers sends stats reply except they timeout we collect that in global list and run consensus

        - Chooses majority chain with stats reply height's we get if tied with majority then keep the longest and holds the peers address in a list who have majority or longest chain.

        - if current length of chain is less than the consensus chain height only then ask for get-block

        - next set of blocks starting from last empty spot in chain is requested from all peers who holds majority chain and main thread gets the get-block-reply runs validation with validate_block() and adds to chain.

        - consensus thread keeps requesting blocks from peers till we have same height as majority of the peers

        - after chain is updated this thread goes to sleep for 1 min then runs again to check if chain update is needed



