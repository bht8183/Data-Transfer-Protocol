"""
Implementation of a Go-Back-N style reliable data transfer RDT protocol over UDP.
"""

import socket
import threading
import time
import struct
import zlib

# ===============================
# Constants and Configs
# ===============================
MAX_PACKET_SIZE = 1400       # Approx max bytes we send in a single UDP payload
TIMEOUT = 1.0                # Retransmission timeout (seconds)
WINDOW_SIZE = 4              # Go-Back-N window size
SLEEP_BETWEEN_SENDS = 0.002  # slow sending rate

# ===============================
# RDTSocket Class
# ===============================
class RDTSocket:
    """
    A reliable data transfer socket built on top of UDP using Go-Back-N.
    """

    def __init__(self, local_addr=("0.0.0.0", 0)):
        """
        Initializes a UDP socket at the given local_addr and starts a listener thread.
        """
        self.udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_sock.bind(local_addr)
        self.remote_addr = None  # Will store who we're sending/receiving from

        # Sender-side variables
        self.send_base = 0               # oldest unacknowledged packet
        self.next_seq_num = 0            # next packet to send
        self.window_size = WINDOW_SIZE
        self.send_buffer = {}            # seq_num -> (packet_bytes, timestamp)

        # Receiver-side variables
        self.expected_seq_num = 0        # Next sequence number we expect to receive
        self.recv_buffer = {}            # If we did SR, we'd store out-of-order packets her

        # Lock for thread safety
        self.lock = threading.Lock()

        #  Timer for Go-Back-N
        self.timer = None

        # Thread management
        self.running = True

        self.listen_thread = threading.Thread(target=self._listen)
        self.listen_thread.daemon = True
        self.listen_thread.start()

    def connect(self, remote_addr):
        """
        For clients: specify who we'll be sending to.
        """
        self.remote_addr = remote_addr

    def accept(self):
        """
        For servers: wait until the first packet arrives from client, then store their address.
        """
        while self.remote_addr is None:
            time.sleep(0.01)

    def rdt_send(self, data):
        """
        Split data into chunks and send them reliably using Go-Back-N logic.
        """
        if not self.remote_addr:
            raise ValueError("Remote address not set. Call connect(..) or accept() first.")

        # Break data into chunks that fit into a packet
        offset = 0
        while offset < len(data):
            chunk = data[offset: offset + (MAX_PACKET_SIZE - 20)]  
            offset += (MAX_PACKET_SIZE - 20)
            self._send_one_chunk(chunk)

    def rdt_recv(self):
        """
        Blocking call to receive data in-order. Returns the next chunk once available.
        Uses a queue (self.received_data) internally.
        """
        while True:
            # Check if we have data in a queue
            self.lock.acquire()
            if hasattr(self, "received_data") and len(self.received_data) > 0:
                data = self.received_data.pop(0)
                self.lock.release()
                return data
            self.lock.release()
            time.sleep(0.01)

    def close(self):
        """
        Cleanly close the RDT socket.
        """
        self.running = False
        if self.timer:
            self.timer.cancel()
        self.udp_sock.close()
        self.listen_thread.join()

    # =====================================================
    # Internal methods
    # =====================================================
    def _listen(self):
        """
        Thread target: repeatedly read from the UDP socket, parse packets, handle them.
        """
        self.received_data = []  # queue of in-order messages
        while self.running:
            try:
                packet, addr = self.udp_sock.recvfrom(2048)
                print(f"[DEBUG] Server _listen received {len(packet)} bytes from {addr}")
            except:
                continue  # socket might be closed

            if not packet:
                continue

            # If remote_addr is not set, this is the first communication from a client
            if self.remote_addr is None:
                self.remote_addr = addr
                print(f"[DEBUG] Server remote_addr set to {self.remote_addr}")

            # Distinguish if this is an ACK or a Data packet by parsing the header
            
            seq_num, ack_flag, data, received_cksum = self._parse_packet(packet)

            if self._is_corrupt(seq_num, ack_flag, data, received_cksum):
                print("[DEBUG] Packet is corrupt; discarding")
                continue

            if ack_flag:
                self._handle_ack(seq_num)
            else:
                self._handle_data(seq_num, data)

    def _handle_data(self, seq_num, data):
        """
        Receiver logic for GBN if seq_num == expected_seq_num, deliver and ack it;
        else re-ack the last one we got in order.
        """
        if seq_num == self.expected_seq_num:
            # Deliver data
            self.lock.acquire()
            self.received_data.append(data)
            self.lock.release()

            # Bump expected_seq_num
            self.expected_seq_num += 1

            # Ack
            ack_pkt = self._make_packet(self.expected_seq_num - 1, b'', ack_flag=True)
            self.udp_sock.sendto(ack_pkt, self.remote_addr)

            # Check if we have buffered out-of-order packets
        else:
            # re-ack the last in-order packet
            last_in_order = self.expected_seq_num - 1
            if last_in_order < 0:
                last_in_order = 0
            ack_pkt = self._make_packet(last_in_order, b'', ack_flag=True)
            self.udp_sock.sendto(ack_pkt, self.remote_addr)

    def _handle_ack(self, ack_num):
        """
        Sender logic if ack_num is within our window, move send_base.
        """
        self.lock.acquire()
        # Move send_base if this ACK is new
        if ack_num >= self.send_base:
            self.send_base = ack_num + 1

            # Remove from send_buffer
            keys_to_remove = [k for k in self.send_buffer.keys() if k <= ack_num]
            for k in keys_to_remove:
                self.send_buffer.pop(k, None)

            # If send_base == next_seq_num, stop timer
            if self.send_base == self.next_seq_num:
                if self.timer:
                    self.timer.cancel()
                    self.timer = None
            else:
                # Restart timer
                if self.timer:
                    self.timer.cancel()
                self._start_timer()
        self.lock.release()

    def _send_one_chunk(self, chunk):
        """
        Send a single chunk of data as one packet (with sequence number, etc.).
        Handle window check, timeouts, etc.
        """
        while True:
            self.lock.acquire()
            # Wait if the window is full
            if self.next_seq_num < self.send_base + self.window_size:
                seq_num = self.next_seq_num
                packet = self._make_packet(seq_num, chunk, ack_flag=False)
                self.send_buffer[seq_num] = (packet, time.time())
                self.next_seq_num += 1

                # Send the packet
                self.udp_sock.sendto(packet, self.remote_addr)
                self.lock.release()

                # Start timer if needed
                self.lock.acquire()
                if self.send_base == seq_num:
                    self._start_timer()
                self.lock.release()

                # Artificially slow the sending rate if required
                time.sleep(SLEEP_BETWEEN_SENDS)
                return
            else:
                # Window is full; wait a bit
                self.lock.release()
                time.sleep(0.01)

    def _start_timer(self):
        """
        Start a retransmission timer.
        """
        if self.timer is not None:
            self.timer.cancel()
        self.timer = threading.Timer(TIMEOUT, self._timeout_handler)
        self.timer.daemon = True
        self.timer.start()

    def _timeout_handler(self):
        """
        On timeout, retransmit all packets in the window (Go-Back-N).
        """
        self.lock.acquire()
        # Retransmit from send_base to next_seq_num - 1
        for seq_num in range(self.send_base, self.next_seq_num):
            if seq_num in self.send_buffer:
                packet, _ = self.send_buffer[seq_num]
                self.udp_sock.sendto(packet, self.remote_addr)
        self.lock.release()
        # restart timer
        self._start_timer()

    # =====================================================
    # Packet Helpers
    # =====================================================
    def _make_packet(self, seq_num, data, ack_flag=False):
        """
        Create a packet with the following format:
        [seq_num (4 bytes)] [ACK flag (1 byte)] [checksum (4 bytes)] [payload...]
        """
        header = struct.pack("!I?", seq_num, ack_flag)
        # Calculate a simple CRC32 for (seq_num, ack_flag, data)
        checksum = zlib.crc32(header + data) & 0xffffffff
        cksum_bytes = struct.pack("!I", checksum)
        return header + cksum_bytes + data

    def _parse_packet(self, packet):
        """
        Returns (seq_num, ack_flag, data, received_cksum).
        If packet is too short, returns defaults that will likely be discarded.
        """
        if len(packet) < 9:
            return 0, False, b'', 0  # treat it as "bad"

        header = packet[:5]
        cksum_bytes = packet[5:9]
        data = packet[9:]

        seq_num, ack_flag = struct.unpack("!I?", header)
        received_cksum = struct.unpack("!I", cksum_bytes)[0]

        return seq_num, ack_flag, data, received_cksum

    def _is_corrupt(self, seq_num, ack_flag, data, received_cksum):
        """
        Recomputes the CRC for the received header + data
        and compares it with received_cksum.
        """
        header = struct.pack("!I?", seq_num, ack_flag)
        computed_cksum = zlib.crc32(header + data) & 0xffffffff
        return (computed_cksum != received_cksum)