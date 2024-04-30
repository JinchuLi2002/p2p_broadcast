# P2P Broadcast

## Description
This is a part of GT CS6675 final project where we attempt to utilize P2P network to make distributed CV training easier. The purpose of this repo is to tackle the data sharing process, we aim to make it fully decentralized.

## Approach
We build a simple P2P network using Python's socket library. For node discovery, we make use of bootstrap nodes as an entry point to the network. Each node is able to broadcast files to all other nodes in the network via propagation.

## Usage and Workflow
1. Start the bootstrap node
```bash
python bootstrap.py
```
2. Start a node (peer) given the bootstrap node's IP and port, the node can choose whether or not to be remembered by the bootstrap node (if not, any subsequent node will not establish direct link to this node)
```bash
python client.py --bootstrap_host <bootstrap_host> --bootstrap_port <bootstrap_port> --join_bootstrap
```
3. Repeat step 2 to start more nodes (in different terminals)
4. Broadcast a file from a node
```bash
<path_to_file>
```
5. After propagation, all nodes receiving the file would create its own workspace and store the file in it.
   
## Evaluation and Discussion
Unfortunately, we are unable to prove that p2p network is faster than the centralized method where a single server broadcasts the file to all nodes, on the local machine (the bandwith on a single machine is constant, regardless of concurrent or not). In theory, however, the efficiency of the p2p network improves with scaling. The larger the network, the more nodes can help propagate the file, thus reducing the time it takes for the file to reach all nodes.

## Limitations and Future Work
1. The current implementation can only support one bootstrap node. If the bootstrap node goes down, no new nodes can join the network. By adding more bootstrap nodes, the network can be made more robust.
2. For the purpose of this demo, we only support single file broadcast. It's natural to extend the functionality to support multiple files and directories.