///////////MD Jidanur Rahman//////
//////////7895504//////////
/////////A3--3010--/////////


////////////////// running the code/////////////////////
run-
    python3 blockchain.py <knowpeer host> <knowpeer port> <port>


# knowpeer host- well-known peer host who is part of blockchain
# knowpeer port - well-known port host who is part of blockchain
# port - port number this program's socket gonna bind with

example-
    python3 blockchain.py silicon.cs.umanitoba 8999 8453

//////////////////////////////////////////////////////////

///////////// implementation details //////////////

Structure-
    # Always running threads- 
        * Main thread is always running for receving messages from peers
        
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


# BONUS INCLUDED - 
    * Flood repeater - check flood_reply() function which handles flood messages(also repeating them if not repeated) and sends flood reply  

    * Mining thread - check mineBlocks() and sendWords()


////////////////////////////////////////////////////////////////////