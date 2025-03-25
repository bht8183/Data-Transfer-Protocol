"""
Client side of the file transfer application using a custom RDT protocol.
The client can optionally send a file to a remote server over UDP with reliability.
"""

import argparse
import os
from rdt_protocol import RDTSocket

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--server_ip", default="127.0.0.1")
    parser.add_argument("--server_port", type=int, default=9000)
    parser.add_argument("--send_file", default=None,
                        help="File to send to the server.")
    args = parser.parse_args()

    # Create RDT socket and bind to local port
    client_addr = ("0.0.0.0", 0)
    rdt_sock = RDTSocket(client_addr)

    # Connect to server
    server_addr = (args.server_ip, args.server_port)
    rdt_sock.connect(server_addr)

    # If we have a file to send. read it in chunks and send via RDT
    if args.send_file is not None and os.path.exists(args.send_file):
        with open(args.send_file, "rb") as f:
            print(f"Sending file {args.send_file} to {server_addr} ...")
            while True:
                chunk = f.read(1024) # Read 1024 bytes at a time
                if not chunk:
                    break
                rdt_sock.rdt_send(chunk)

        # Indicate to the server that we re done sending
        rdt_sock.rdt_send(b"EOF")
        print("File send complete.")
    else:
        print("No valid file provided.")

    rdt_sock.close()

if __name__ == "__main__":
    main()