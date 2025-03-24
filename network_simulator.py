# network_simulator.py

import socket
import random
import threading
import time
import argparse

def corrupt_data(data):
    """Flip one random byte in the packet to simulate corruption."""
    if len(data) < 1:
        return data
    data = bytearray(data)
    idx = random.randrange(len(data))
    data[idx] ^= 0xFF  # Flip all bits in that byte
    return bytes(data)

def simulator(listen_ip, listen_port, forward_ip, forward_port,
              drop_prob=0.0, corrupt_prob=0.0, reorder_prob=0.0):
    """
    Start a simulator that listens on (listen_ip, listen_port)
    and forwards to (forward_ip, forward_port) with certain impairments.
    Also listens on (forward_ip, forward_port) and forwards back to (listen_ip, listen_port).
    """
    sock_in = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock_in.bind((listen_ip, listen_port))

    sock_out = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock_out.bind((forward_ip, 0))  # bind to an ephemeral port

    reorder_buffer = []

    def handle_incoming_from_A():
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

    tA = threading.Thread(target=handle_incoming_from_A, daemon=True)
    tB = threading.Thread(target=handle_incoming_from_B, daemon=True)
    tA.start()
    tB.start()

    # Periodically release a packet from reorder_buffer
    while True:
        time.sleep(0.05)
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