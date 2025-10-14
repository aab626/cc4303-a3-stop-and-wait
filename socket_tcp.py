import socket
import random
import math

from segment_tcp import SegmentTCP


UDP_BUFFER_SIZE = 4096
MESSAGE_MAX_PACKET_SIZE = 16
SEGMENT_TIMEOUT_SECONDS = 3.0


class SocketTCP:
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
        self.recv_buffer = bytearray()
        self.bytes_received_in_message = 0
        self.is_closed = False

    # Only for servers
    def bind(self, address: tuple[str, int]) -> None:
        self.origin_addr, self.origin_port = address
        self.socket.bind((self.origin_addr, self.origin_port))

    # Client calls this to initiate handshake
    def connect(self, address: tuple[str, int]) -> None:
        self.seq = random.randint(0, 100)
        self.destination_addr, self.destination_port = address
        print(f'[{self.seq}] @connect, set seq')

        # Send SYN, seq=x
        tcp_segment = SegmentTCP(True, False, False, self.seq, '')
        print(f'[{self.seq}] @connect, send SYN')
        self._send_segment(tcp_segment)

        # Wait ACK+SYN, seq=x+1
        print(f'[{self.seq}] @connect, wait ACK+SYN...')
        while True:
            try:
                recv_segment, recv_address = self._wait_message(
                    f_condition=lambda sock, rseg: rseg.ack and rseg.syn and rseg.seq == sock.seq + 1,
                    f_update_seq=lambda sock, rseg: rseg.seq
                )
                break
            except socket.timeout:
                print(f'[{self.seq}] @connect, timeout waiting SYN-ACK, resending SYN')
                self._send_segment(tcp_segment)
        self.destination_addr, self.destination_port = recv_address
        if self.origin_addr is None or self.origin_port is None:
            self.origin_addr, self.origin_port = self.socket.getsockname()
        
        # Send ACK
        self.seq += 1
        tcp_segment = SegmentTCP(False, True, False, self.seq, '')
        print(f'[{self.seq}] @connect, send ACK')
        self._send_segment(tcp_segment)

        print(f'[{self.seq}] @connect, handshake completed!')

    # Server calls this to respond to a client-initiated handshake
    def accept(self) -> 'tuple[SocketTCP, tuple[str, int]]':
        # Wait SYN, will set seq=x
        print(f'[{self.seq}] @accept, wait SYN...')
        while True:
            try:
                recv_segment, recv_address = self._wait_message(
                    f_condition=lambda sock, rseg: rseg.syn,
                    f_update_seq=lambda sock, rseg: sock.seq
                )
                break
            except socket.timeout:
                # Continue listening for new SYNs
                print(f'[{self.seq}] @accept, timeout waiting SYN, continuing')
                continue

        conn_socket = SocketTCP()
        conn_socket.destination_addr, conn_socket.destination_port = recv_address
        local_bind_addr = self.origin_addr if self.origin_addr is not None else ''
        conn_socket.socket.bind((local_bind_addr, 0))
        conn_socket.origin_addr, conn_socket.origin_port = conn_socket.socket.getsockname()
        conn_socket.seq = recv_segment.seq

        # Send ACK+SYN, seq=x+1
        conn_socket.seq += 1
        tcp_segment = SegmentTCP(True, True, False, conn_socket.seq, '')
        print(f'[{conn_socket.seq}] @accept(conn), send ACK+SYN')
        conn_socket._send_segment(tcp_segment)

        # Wait ACK
        print(f'[{conn_socket.seq}] @accept(conn), wait ACK...')
        while True:
            try:
                conn_socket._wait_message(
                    f_condition=lambda sock, rseg: rseg.ack and rseg.seq == sock.seq + 1,
                    f_update_seq=lambda sock, rseg: rseg.seq
                )
                break
            except socket.timeout:
                print(f'[{conn_socket.seq}] @accept(conn), timeout waiting ACK, resending SYN-ACK')
                conn_socket._send_segment(tcp_segment)

        print(f'[{conn_socket.seq}] @accept(conn), handshake completed!')

        return (conn_socket, (conn_socket.origin_addr, conn_socket.origin_port))
    
    def send(self, message: bytes) -> None:
        if isinstance(message, str):
            message = message.encode()
        elif isinstance(message, bytearray):
            message = bytes(message)
        elif not isinstance(message, (bytes, bytearray)):
            raise TypeError(f'Error: Unsupported message type: {type(message).__name__}')

        message_length = len(message)

        # Slice message into <MESSAGE_MAX_PACKET_SIZE> sized pieces
        messages_sliced = [
            message[i:i + MESSAGE_MAX_PACKET_SIZE]
            for i in range(0, message_length, MESSAGE_MAX_PACKET_SIZE)
        ]

        # First, send the bytecount of the whole message
        self.seq += 1
        tcp_segment = SegmentTCP(False, False, False, self.seq, message_length)
        print(f'[{self.seq}] @send, send BYTECOUNT')
        self._send_segment(tcp_segment)

        # Wait bytecount ACK
        print(f'[{self.seq}] @send, wait BYTECOUNT ACK...')
        while True:
            try:
                self._wait_message(
                    f_condition=lambda sock, rseg: rseg.ack and rseg.seq == sock.seq + 1,
                    f_update_seq=lambda sock, rseg: rseg.seq + 1
                )
                break
            except socket.timeout:
                print(f'[{self.seq}] @send, timeout waiting BYTECOUNT ACK, resending BYTECOUNT')
                self._send_segment(tcp_segment)

        # Start sending all the message slices
        for message_slice in messages_sliced:
            # Send message slice
            self.seq += len(message_slice)
            payload = message_slice.decode('latin1')
            tcp_segment = SegmentTCP(False, False, False, self.seq, payload)
            print(f'[{self.seq}] @send, send msg slice:\'{payload}\'')
            self._send_segment(tcp_segment)

            # Wait message slice ACK
            print(f'[{self.seq}] @send, wait msg slice ACK...')
            while True:
                try:
                    self._wait_message(
                        f_condition=lambda sock, rseg: rseg.ack and rseg.seq == sock.seq,
                        f_update_seq=lambda sock, rseg: sock.seq
                    )
                    break
                except socket.timeout:
                    print(f'[{self.seq}] @send, timeout waiting data ACK, resending slice')
                    self._send_segment(tcp_segment)

        print('@send, end')

    def recv(self, buffer_size: int) -> bytes:
        if buffer_size <= 0:
            raise ValueError('buffer_size must be positive')

        print(f'[{self.seq}] @recv({buffer_size}), waiting message...')

        while True:
            if len(self.recv_buffer) > 0:
                chunk_length = min(buffer_size, len(self.recv_buffer))
                chunk = bytes(self.recv_buffer[:chunk_length])
                del self.recv_buffer[:chunk_length]

                return chunk

            try:
                recv_segment, recv_address = self._wait_message(
                    f_condition=lambda sock, rseg: True,
                    f_update_seq=lambda sock, rseg: sock.seq
                )
            except socket.timeout:
                # Continue waiting for the expected segment
                print(f'[{self.seq}] @recv, timeout waiting data, continuing')
                continue

            # If expected total bytes is not set, message should be bytecount of message
            if self.expected_total_bytes is None or len(self.current_message) >= self.expected_total_bytes:
                self.expected_total_bytes = int(recv_segment.msg)
                self.bytes_received_in_message = 0
                self.current_message = ''
                self.recv_buffer.clear()
                self.seq = recv_segment.seq + 1

                tcp_segment = SegmentTCP(False, True, False, self.seq, '')
                self._send_segment(tcp_segment)
                continue

            if self.seq is not None and recv_segment.seq <= self.seq:
                # Duplicate or out-of-order segment, re-ACK last confirmed seq
                print(f'[{self.seq}] @recv, duplicate segment detected (seq {recv_segment.seq}), re-ACKing')
                tcp_segment = SegmentTCP(False, True, False, self.seq, '')
                self._send_segment(tcp_segment)
                continue

            # Otherwise, it is a slice of the message
            data_bytes = recv_segment.msg.encode('latin1')
            self.current_message += recv_segment.msg
            self.bytes_received_in_message += len(data_bytes)
            self.seq = recv_segment.seq

            # Send the ACK
            tcp_segment = SegmentTCP(False, True, False, self.seq, '')
            self._send_segment(tcp_segment)

            self.recv_buffer.extend(data_bytes)

    def close(self) -> None:
        if self.is_closed:
            return

        print(f'[{self.seq}] @close, initiating termination')

        if self.destination_addr is None or self.destination_port is None:
            self.socket.close()
            self.is_closed = True
            return

        if self.seq is None:
            self.seq = 0

        # Send FIN
        self.seq += 1
        fin_segment = SegmentTCP(False, False, True, self.seq, '')
        print(f'[{self.seq}] @close, send FIN')
        self._send_segment(fin_segment)

        # Wait for ACK of our FIN
        print(f'[{self.seq}] @close, wait FIN ACK...')
        while True:
            try:
                self._wait_message(
                    f_condition=lambda sock, rseg: rseg.ack and rseg.seq == sock.seq,
                    f_update_seq=lambda sock, rseg: sock.seq
                )
                break
            except socket.timeout:
                print(f'[{self.seq}] @close, timeout waiting FIN ACK, resending FIN')
                self._send_segment(fin_segment)

        # Wait for FIN from peer
        print(f'[{self.seq}] @close, wait peer FIN...')
        while True:
            try:
                recv_segment, _ = self._wait_message(
                    f_condition=lambda sock, rseg: rseg.fin,
                    f_update_seq=lambda sock, rseg: rseg.seq
                )
                break
            except socket.timeout:
                print(f'[{self.seq}] @close, timeout waiting peer FIN, continuing')
                continue

        # Send final ACK
        ack_segment = SegmentTCP(False, True, False, self.seq, '')
        print(f'[{self.seq}] @close, send final ACK')
        self._send_segment(ack_segment)

        self.socket.close()
        self.is_closed = True
        print(f'[{self.seq}] @close, connection closed')

    def recv_close(self) -> None:
        if self.is_closed:
            return

        print(f'[{self.seq}] @recv_close, waiting FIN...')

        # Wait for FIN from peer
        while True:
            try:
                recv_segment, _ = self._wait_message(
                    f_condition=lambda sock, rseg: rseg.fin,
                    f_update_seq=lambda sock, rseg: rseg.seq
                )
                break
            except socket.timeout:
                print(f'[{self.seq}] @recv_close, timeout waiting FIN, continuing')
                continue

        # Send ACK for received FIN
        ack_segment = SegmentTCP(False, True, False, self.seq, '')
        print(f'[{self.seq}] @recv_close, send ACK for FIN')
        self._send_segment(ack_segment)

        # Send own FIN
        self.seq += 1
        fin_segment = SegmentTCP(False, False, True, self.seq, '')
        print(f'[{self.seq}] @recv_close, send FIN')
        self._send_segment(fin_segment)

        # Wait for ACK of our FIN
        print(f'[{self.seq}] @recv_close, wait final ACK...')
        while True:
            try:
                self._wait_message(
                    f_condition=lambda sock, rseg: rseg.ack and rseg.seq == sock.seq,
                    f_update_seq=lambda sock, rseg: sock.seq
                )
                break
            except socket.timeout:
                print(f'[{self.seq}] @recv_close, timeout waiting final ACK, resending FIN')
                self._send_segment(fin_segment)

        self.socket.close()
        self.is_closed = True
        print(f'[{self.seq}] @recv_close, connection closed')
        
    def _send_segment(self, tcp_segment, timeout=0):
        message_bytes = SegmentTCP.create_segment(tcp_segment)
        print(f'[{self.seq}] @_send_segment, sent msg: {tcp_segment}')
        self.socket.sendto(message_bytes, (self.destination_addr, self.destination_port))

    def _wait_message(self, f_condition, f_update_seq, timeout=0):
        is_waiting = True
        while is_waiting:
            try:
                recv_message, recv_address = self.socket.recvfrom(UDP_BUFFER_SIZE)
            except socket.timeout as exc:
                raise exc
            recv_segment = SegmentTCP.parse_segment(recv_message)
            print(f'[{self.seq}] @_wait_message, recv: {recv_segment}')
            
            condition_met = f_condition(self, recv_segment)
            if condition_met:
                is_waiting = False
                self.seq = f_update_seq(self, recv_segment)
                print(f'[{self.seq}] @_wait_message, confirmed')
            else:
                if recv_segment.syn and recv_segment.ack:
                    ack_seq = recv_segment.seq + 1
                    ack_segment = SegmentTCP(False, True, False, ack_seq, '')
                    print(f'[{self.seq}] @_wait_message, duplicate SYN+ACK detected, re-ACKing with seq {ack_seq}')
                    self._send_segment(ack_segment)

        return recv_segment, recv_address
