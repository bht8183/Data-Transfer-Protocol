# server.py

import argparse
from rdt import RDTSocket

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=9000)
    parser.add_argument("--save_file", default="received_file.dat",
                        help="Where to save the incoming file data.")
    args = parser.parse_args()

    # Create RDT socket
    server_addr = ("0.0.0.0", args.port)
    rdt_sock = RDTSocket(server_addr)
    print(f"Server listening on {server_addr}")

    # Wait for a client to connect
    print("Waiting for client to connect...")
    rdt_sock.accept()
    print("Client connected!")

    # Now we can read data from the client
    with open(args.save_file, "wb") as f:
        while True:
            data = rdt_sock.rdt_recv()
            if data == b"EOF":  # simple end-of-file marker
                print("Finished receiving file.")
                break
            f.write(data)

    # Close the socket
    rdt_sock.close()

if __name__ == "__main__":
    main()