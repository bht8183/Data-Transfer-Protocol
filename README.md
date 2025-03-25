Reliable Data Transfer (RDT) homework
This project implements a Go-Back-N-style reliable data transfer protocol on top of UDP. It consists of:

A network simulator (network_simulator.py) that can introduce packet loss, corruption, and reordering.

An RDT server (server.py) that listens for incoming data and writes it to a file.

An RDT client (client.py) that reads a file from disk and reliably sends it to the server.

The underlying RDT logic is in rdt_protocol.py.

1. How to Compile and Run
Prerequisites
Python 3.6+

You may need to install any dependencies in requirements.txt by running:

pip install -r requirements.txt

No Compilation Needed
This is a pure Python project, so there is no compilation step

2. Running Each Component

A. Network Simulator

python network_simulator.py \
    --listen_ip 127.0.0.1 \
    --listen_port 8000 \
    --forward_ip 127.0.0.1 \
    --forward_port 9000 \
    --drop_prob 0.0 \
    --corrupt_prob 0.0 \
    --reorder_prob 0.0

--listen_ip / --listen_port: Where the simulator listens for incoming packets (often from the client).

--forward_ip / --forward_port: The destination to forward packets to (often the server).

--drop_prob, --corrupt_prob, --reorder_prob: The probabilities of dropping, corrupting, and reordering packets (float values between 0.0 and 1.0).

B. Server
Run the server on the port specified for --forward_port in the simulator (by default 9000).

python server.py --port 9000 --save_file received_file.dat

--port: The port on which the server listens for RDT connections.

--save_file: The name/path of the output file where incoming data will be stored.

After it starts, you’ll see something like:

Server listening on ('0.0.0.0', 9000)
Waiting for client to connect...

C. Client
Run the client after the server and simulator are running. Point it at the simulator’s listening port (default 8000).

python client.py --server_ip 127.0.0.1 --server_port 8000 --send_file testfile.txt

--server_ip: The IP address of the simulator (not the actual server) if you are using the simulator in between.

--server_port: The simulator’s port (e.g., 8000), which then forwards data to the server at port 9000.

--send_file: Path to the file on your local machine that you want to send.

You should see logging output indicating packets were sent and eventually a “File send complete.” message on the client side. On the server side, once the file is completely received, you will see a “Finished receiving file.” message.

3. Command-Line Examples
Example 1: No Impairments

simulator:

python network_simulator.py --listen_ip 127.0.0.1 --listen_port 8000 --forward_ip 127.0.0.1 --forward_port 9000 --drop_prob 0.0 --corrupt_prob 0.0 --reorder_prob 0.0

server:

python server.py --port 9000 --save_file recieved_file.dat

client:

python client.py --server_ip 127.0.0.1 --server_port 8000 --send_file testfile.txt

Example 2: With Impairments

Simulator (20% drop, 10% corrupt, 15% reorder):

python network_simulator.py --listen_ip 127.0.0.1 --listen_port 8000 --forward_ip 127.0.0.1 --forward_port 9000 --drop_prob 0.2 --corrupt_prob 0.1 --reorder_prob 0.15


4. File Structure

├── client.py
├── server.py
├── network_simulator.py
├── rdt_protocol.py
├── requirements.txt
├── README.md
├── Report.pdf
├── git log