"""
Simplified TCP with Stop & Wait implementation.
CC4303 - Computer Networks
Author: Augusto Aguayo Barham
"""

import socket
import random
import time
import builtins

from segment_tcp import SegmentTCP

# Socket constants
UDP_BUFFER_SIZE = 4096
MESSAGE_MAX_PACKET_SIZE = 16
SEGMENT_TIMEOUT_SECONDS = 1.0

# Simplified TCP socket wrapper, using UDP with Stop & Wait.
class SocketTCP:
    # Constructor
    def __init__(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.settimeout(SEGMENT_TIMEOUT_SECONDS)
        self.destination_addr = None
        self.destination_port = None
        self.origin_addr = None
        self.origin_port = None
        self.seq = None
        
        self.current_message = ''
        self.expected_total_bytes = None
        self.bytes_received_in_message = 0
        self.is_closed = False

    # Server function
    # Start listerning on the address
    def bind(self, address: tuple[str, int]) -> None:
        self.origin_addr, self.origin_port = address
        self.socket.bind((self.origin_addr, self.origin_port))

    # Client function
    # Initiate handshake with the server
    def connect(self, address: tuple[str, int]) -> None:
        self.seq = random.randint(0, 100)
        self.destination_addr, self.destination_port = address
        self._log(f'[{self.seq}] @connect, set seq to {self.seq}')

        # Send SYN, seq=x
        tcp_segment = SegmentTCP(True, False, False, self.seq, '')
        self._log(f'[{self.seq}] @connect, send SYN')
        self._send_segment(tcp_segment)

        # Wait ACK+SYN, seq=x+1
        self._log(f'[{self.seq}] @connect, wait ACK+SYN...')
        while True:
            try:
                recv_segment, recv_address = self._wait_message(
                    f_condition=lambda sock, rseg: rseg.ack and rseg.syn and rseg.seq == sock.seq + 1,
                    f_update_seq=lambda sock, rseg: rseg.seq
                )
                break
            except socket.timeout:
                self._log(f'[{self.seq}] @connect, timeout waiting SYN-ACK, resending SYN')
                self._send_segment(tcp_segment)

        self.destination_addr, self.destination_port = recv_address
        
        # Send ACK
        self.seq += 1
        tcp_segment = SegmentTCP(False, True, False, self.seq, '')
        self._log(f'[{self.seq}] @connect, send ACK')
        self._send_segment(tcp_segment)

        self._log(f'[{self.seq}] @connect, handshake completed!')

    # Server function
    # Responds to a client-initiated handshake
    def accept(self) -> 'tuple[SocketTCP, tuple[str, int]]':
        # Wait SYN, will set seq=x
        self._log(f'[{self.seq}] @accept, wait SYN...')
        while True:
            try:
                recv_segment, recv_address = self._wait_message(
                    f_condition=lambda sock, rseg: rseg.syn,
                    f_update_seq=lambda sock, rseg: sock.seq
                )
                break
            except socket.timeout:
                # Continue listening for new SYNs
                self._log(
                    f'[{self.seq}] @accept, timeout waiting SYN, continuing')
                continue

        conn_socket = SocketTCP()
        conn_socket.destination_addr, conn_socket.destination_port = recv_address
        local_bind_addr = self.origin_addr if self.origin_addr is not None else ''

        # Let the system pick a port
        conn_socket.socket.bind((local_bind_addr, 0))
        conn_socket.origin_addr, conn_socket.origin_port = conn_socket.socket.getsockname()
        conn_socket.seq = recv_segment.seq

        # Send ACK+SYN, seq=x+1
        conn_socket.seq += 1
        tcp_segment = SegmentTCP(True, True, False, conn_socket.seq, '')
        self._log(f'[{conn_socket.seq}] @accept(conn), send ACK+SYN')
        conn_socket._send_segment(tcp_segment)

        # Wait ACK
        self._log(f'[{conn_socket.seq}] @accept(conn), wait ACK...')
        while True:
            try:
                conn_socket._wait_message(
                    f_condition=lambda sock, rseg: rseg.ack and rseg.seq == sock.seq + 1,
                    f_update_seq=lambda sock, rseg: rseg.seq
                )
                break
            except socket.timeout:
                self._log(f'[{conn_socket.seq}] @accept(conn), timeout waiting ACK, resending SYN-ACK')
                conn_socket._send_segment(tcp_segment)

        self._log(f'[{conn_socket.seq}] @accept(conn), handshake completed!')

        return (conn_socket, (conn_socket.origin_addr, conn_socket.origin_port))
    
    # Sends a full message in byte form
    def send(self, message: bytes) -> None:
        # Slice message into pieces of MESSAGE_MAX_PACKET_SIZE size
        message_length = len(message)
        messages_sliced = [
            message[i:i + MESSAGE_MAX_PACKET_SIZE]
            for i in range(0, message_length, MESSAGE_MAX_PACKET_SIZE)
        ]

        # Step 1
        # Send the bytecount of the whole message
        self.seq += 1
        tcp_segment = SegmentTCP(False, False, False, self.seq, message_length)
        self._log(f'[{self.seq}] @send, send BYTECOUNT')
        self._send_segment(tcp_segment)

        # Wait bytecount ACK
        self._log(f'[{self.seq}] @send, wait BYTECOUNT ACK...')
        while True:
            try:
                self._wait_message(
                    f_condition=lambda sock, rseg: rseg.ack and rseg.seq == sock.seq + 1,
                    f_update_seq=lambda sock, rseg: rseg.seq + 1
                )
                break
            except socket.timeout:
                self._log(f'[{self.seq}] @send, timeout waiting BYTECOUNT ACK, resending BYTECOUNT')
                self._send_segment(tcp_segment)

        # Step 2
        # Start sending all the message slices
        for message_slice in messages_sliced:
            # Send message slice
            self.seq += len(message_slice)
            message_slice_data = message_slice.decode()
            tcp_segment = SegmentTCP(False, False, False, self.seq, message_slice_data)
            self._log(f'[{self.seq}] @send, send msg slice:\'{message_slice_data}\'')
            self._send_segment(tcp_segment)

            # Wait message slice ACK
            self._log(f'[{self.seq}] @send, wait msg slice ACK...')
            while True:
                try:
                    self._wait_message(
                        f_condition=lambda sock, rseg: rseg.ack and rseg.seq == sock.seq,
                        f_update_seq=lambda sock, rseg: sock.seq
                    )
                    break
                except socket.timeout:
                    self._log(f'[{self.seq}] @send, timeout waiting data ACK, resending msg slice')
                    self._send_segment(tcp_segment)

        self._log(f'[{self.seq}] @send, end')

    # Receives a TCP Segment of a message, of size buffer_size
    def recv(self, buffer_size: int) -> bytes:
        self._log(f'[{self.seq}] @recv({buffer_size}), waiting message...')

        while True:
            # Wait for data
            try:
                recv_segment, recv_address = self._wait_message(
                    f_condition=lambda sock, rseg: True,
                    f_update_seq=lambda sock, rseg: sock.seq
                )
            except socket.timeout:
                self._log(f'[{self.seq}] @recv, timeout waiting data, continuing')
                continue

            # If expected total bytes is not set, message should be bytecount of message
            if self.expected_total_bytes is None or len(self.current_message.encode()) >= self.expected_total_bytes:
                self.expected_total_bytes = int(recv_segment.msg)
                self.bytes_received_in_message = 0
                self.current_message = ''
                self.seq = recv_segment.seq + 1

                # Send bytecount ACK
                tcp_segment = SegmentTCP(False, True, False, self.seq, '')
                self._send_segment(tcp_segment)
                continue

            # Handle duplicates or out of order packages
            # Just re-send the last ACK for the last confirmed package
            if self.seq is not None and recv_segment.seq <= self.seq:
                self._log(f'[{self.seq}] @recv, duplicate segment detected (seq {recv_segment.seq}), re-ACKing')
                tcp_segment = SegmentTCP(False, True, False, self.seq, '')
                self._send_segment(tcp_segment)
                continue

            # Otherwise, it is a slice of the message
            data_bytes = recv_segment.msg.encode()
            self.current_message += recv_segment.msg
            self.bytes_received_in_message += len(data_bytes)
            self.seq = recv_segment.seq

            # Send the ACK
            tcp_segment = SegmentTCP(False, True, False, self.seq, '')
            self._send_segment(tcp_segment)

            return data_bytes

    # Terminates the socket
    # Handles the B-Host-side FIN/ACK package exchange
    def close(self) -> None:
        if self.is_closed:
            return

        self._log(f'[{self.seq}] @close, initiating termination')

        # Send FIN
        self.seq += 1
        fin_segment = SegmentTCP(False, False, True, self.seq, '')
        self._log(f'[{self.seq}] @close, send FIN')
        self._send_segment(fin_segment)

        # Wait FIN+ACK (3 timeouts), on timeout resends FIN
        retries = 1
        self._log(f'[{self.seq}] @close, wait FIN+ACK...')
        while True:
            try:
                self._wait_message(
                    f_condition=lambda sock, rseg: rseg.ack and rseg.fin and rseg.seq == sock.seq,
                    f_update_seq=lambda sock, rseg: sock.seq
                )
                break
            except socket.timeout:
                retries += 1

                # If third sent FIN+ACK without response, assume connection is closed.
                if retries >= 3:
                    self._log(f'[{self.seq}] @close, 3 timeouts waiting FIN+ACK, assume connection closed')
                    self.socket.close()
                    self.is_closed = True
                    return
                
                self._log(f'[{self.seq}] @close, timeout waiting FIN+ACK, resending FIN')
                self._send_segment(fin_segment)

        # Send final ACK it 3 times with a timeout between sends.
        ack_segment = SegmentTCP(False, True, False, self.seq, '')
        for i in range(3):
            self._log(f'[{self.seq}] @close, re-send final ACK {i+1}/3')
            self._send_segment(ack_segment)
            time.sleep(SEGMENT_TIMEOUT_SECONDS)

        self.socket.close()
        self.is_closed = True
        self._log(f'[{self.seq}] @close, connection closed')

    # Terminates the socket
    # Handles the A-Host-side FIN/ACK package exchange
    def recv_close(self) -> None:
        if self.is_closed:
            return

        self._log(f'[{self.seq}] @recv_close, waiting FIN...')

        # Wait FIN
        while True:
            try:
                recv_segment, _ = self._wait_message(
                    f_condition=lambda sock, rseg: rseg.fin,
                    f_update_seq=lambda sock, rseg: rseg.seq
                )
                break
            except socket.timeout:
                self._log(
                    f'[{self.seq}] @recv_close, timeout waiting FIN, continuing')
                continue

        # Send FIN+ACK
        tcp_segment = SegmentTCP(False, True, True, self.seq, '')
        self._log(f'[{self.seq}] @recv_close, send FIN+ACK')
        self._send_segment(tcp_segment)

        retries = 1
        self._log(f'[{self.seq}] @recv_close, wait final ACK...')
        while True:
            try:
                self._wait_message(
                    f_condition=lambda sock, rseg: rseg.ack and rseg.seq == sock.seq,
                    f_update_seq=lambda sock, rseg: sock.seq
                )
                break
            except socket.timeout:
                retries += 1
                if retries >= 3:
                    self._log(f'[{self.seq}] @recv_close, 3 timeouts waiting final ACK, assume connection closed')
                    self.socket.close()
                    self.is_closed = True
                    self._log(f'[{self.seq}] @recv_close, connection closed')
                    return
                
                self._log(f'[{self.seq}] @recv_close, timeout waiting final ACK, resending FIN+ACK')
                tcp_segment = SegmentTCP(False, True, True, self.seq, '')
                self._send_segment(tcp_segment)

        self.socket.close()
        self.is_closed = True
        self._log(f'[{self.seq}] @recv_close, connection closed')

    # Helper private method to send a tcp segment
    def _send_segment(self, tcp_segment):
        message_bytes = SegmentTCP.create_segment(tcp_segment)
        self._log(f'[{self.seq}] @_send_segment, sent msg: {tcp_segment}')
        self.socket.sendto(message_bytes, (self.destination_addr, self.destination_port))

    # Helper private method to await a tcp segment based on a condition
    # f_condition:  lambda function (self, received_segment)
    #               Condition for when the received message is accepted
    # f_update_seq: lambda function (self, received_segment)
    #               Assigns the new seq number to the caller
    def _wait_message(self, f_condition, f_update_seq):
        is_waiting = True
        while is_waiting:
            try:
                recv_message, recv_address = self.socket.recvfrom(UDP_BUFFER_SIZE)
            except socket.timeout as exc:
                raise exc
            recv_segment = SegmentTCP.parse_segment(recv_message)
            self._log(f'[{self.seq}] @_wait_message, recv: {recv_segment}')
            
            condition_met = f_condition(self, recv_segment)
            if condition_met:
                is_waiting = False
                self.seq = f_update_seq(self, recv_segment)
                self._log(f'[{self.seq}] @_wait_message, confirmed')
            else:
                if recv_segment.syn and recv_segment.ack:
                    ack_seq = recv_segment.seq + 1
                    ack_segment = SegmentTCP(False, True, False, ack_seq, '')
                    self._log(
                        f'[{self.seq}] @_wait_message, duplicate SYN+ACK detected, re-ACKing with seq {ack_seq}')
                    self._send_segment(ack_segment)

        return recv_segment, recv_address

    # Helper debugging function
    def _log(self, message):
        print(message)