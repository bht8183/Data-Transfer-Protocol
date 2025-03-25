"""
Simulates a lossy, corrupting, and reordering network layer between two endpoints.
uUseful for testing the custom RDT protocol by emulating real network impairments.
"""

import socket
import random
import threading
import time
import argparse

def corrupt_data(data):
    """
    Flip a random byte to simulate corruption.
    If the dat empty, nothing changes.
    """
    if len(data) < 1:
        return data
    data = bytearray(data)
    idx = random.randrange(len(data)) # pick random byte index
    data[idx] ^= 0xFF  # flip all bits in byte
    return bytes(data)

def simulator(listen_ip, listen_port, forward_ip, forward_port,
              drop_prob=0.0, corrupt_prob=0.0, reorder_prob=0.0):
    """
    Listens on (listen_ip, listen_port) and forwards traffic to (forward_ip, forward_port).
    Also listens on another port for return traffic,
    then forwards it back to (listen_ip, listen_port). It can drop, corrupt, or reorder
    packets according the probabilities.
    """
    # Socket for incoming data from client
    sock_in = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock_in.bind((listen_ip, listen_port))
    # Socket for incoming data from server
    sock_out = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock_out.bind((forward_ip, 0))  # bind to an ephemeral port

    # Buffer for reordering. we can store packets here before sending
    reorder_buffer = []

    def handle_incoming_from_A():
        """
        Continuously receive packets from client,
        then possibly drop, corrupt, reorder, or forward them to server.
        """
        while True:
            
            data, addr = sock_in.recvfrom(4096)
            print("Simulator received", len(data), "bytes from", addr)
            # Possibly drop
            if random.random() < drop_prob:
                continue
            # Possibly corrupt
            if random.random() < corrupt_prob:
                data = corrupt_data(data)
            # Possibly reorder
            if random.random() < reorder_prob:
                reorder_buffer.append((data, 'A'))
            else:
                sock_out.sendto(data, (forward_ip, forward_port))
                print("Simulator forwarded to", (forward_ip, forward_port))

    def handle_incoming_from_B():
        """
        Continuously receive packets from side server,
        then possibly drop, corrupt, reorder, or forward them back to client.
        """
        while True:
            data, addr = sock_out.recvfrom(4096)
            # Possibly drop
            if random.random() < drop_prob:
                continue
            # Possibly corrupt
            if random.random() < corrupt_prob:
                data = corrupt_data(data)
            # Possibly reorder
            if random.random() < reorder_prob:
                reorder_buffer.append((data, 'B'))
            else:
                sock_in.sendto(data, (listen_ip, listen_port))

    # Start threads to handle both directions
    tA = threading.Thread(target=handle_incoming_from_A, daemon=True)
    tB = threading.Thread(target=handle_incoming_from_B, daemon=True)
    tA.start()
    tB.start()

    # Periodically release a packet from reorder_buffer
    while True:
        time.sleep(0.05)
        # 20% chance each cycle to release one packet from the buffer
        if reorder_buffer and random.random() < 0.2:
            # pick a random index
            i = random.randrange(len(reorder_buffer))
            data, direction = reorder_buffer.pop(i)
            if direction == 'A':
                sock_out.sendto(data, (forward_ip, forward_port))
            else:
                sock_in.sendto(data, (listen_ip, listen_port))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--listen_ip", default="127.0.0.1")
    parser.add_argument("--listen_port", type=int, default=8000)
    parser.add_argument("--forward_ip", default="127.0.0.1")
    parser.add_argument("--forward_port", type=int, default=9000)
    parser.add_argument("--drop_prob", type=float, default=0.0)
    parser.add_argument("--corrupt_prob", type=float, default=0.0)
    parser.add_argument("--reorder_prob", type=float, default=0.0)
    args = parser.parse_args()

    simulator(args.listen_ip, args.listen_port, 
              args.forward_ip, args.forward_port,
              args.drop_prob, args.corrupt_prob, args.reorder_prob)

if __name__ == "__main__":
    main()