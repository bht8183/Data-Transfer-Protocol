# client.py

import argparse
import os
from rdt import RDTSocket

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--server_ip", default="127.0.0.1")
    parser.add_argument("--server_port", type=int, default=9000)
    parser.add_argument("--send_file", default=None,
                        help="File to send to the server.")
    args = parser.parse_args()

    # Create RDT socket (bind to ephemeral port)
    client_addr = ("0.0.0.0", 0)
    rdt_sock = RDTSocket(client_addr)

    # Connect to server
    server_addr = (args.server_ip, args.server_port)
    rdt_sock.connect(server_addr)

    # If we have a file to send
    if args.send_file is not None and os.path.exists(args.send_file):
        with open(args.send_file, "rb") as f:
            print(f"Sending file {args.send_file} to {server_addr} ...")
            while True:
                chunk = f.read(1024)
                if not chunk:
                    break
                rdt_sock.rdt_send(chunk)

        # Send a special "EOF" marker
        rdt_sock.rdt_send(b"EOF")
        print("File send complete.")
    else:
        print("No file provided or file does not exist. Exiting.")

    rdt_sock.close()

if __name__ == "__main__":
    main()