import socket
import re
import random
from enum import Enum, auto
import sys
import math

HEADER_SEPATOR_UNIT = '|'
HEADER_SEPARATOR = f'{HEADER_SEPATOR_UNIT*3}'
HEADER_REGEX = re.compile(
    rf'^([01])([01])([01]){re.escape(HEADER_SEPARATOR)}(\d+){re.escape(HEADER_SEPARATOR)}(.*)$',
    re.DOTALL
)

VALID_BOOLS_STR = ['0', '1']
UDP_BUFFER_SIZE = 4096
MESSAGE_MAX_PACKET_SIZE = 16

class SocketState(Enum):
    DISCONNECTED = 0
    CLIENT_SENT_SYN = auto()

    HANDSHAKE_SENT_SYN_WAITING_FOR_ACKSYN = auto()
    HANDSHAKE_SENT_ACKSYN_WAITING_FOR_ACK = auto()










class SegmentTCP:
    def __init__(self, syn:bool, ack:bool, fin:bool, seq:int, msg:str):
        if not isinstance(syn, bool):
            raise TypeError(f"Error: syn must be bool, got {type(syn).__name__}")
        if not isinstance(ack, bool):
            raise TypeError(f"Error: ack must be bool, got {type(ack).__name__}")
        if not isinstance(fin, bool):
            raise TypeError(f"Error: fin must be bool, got {type(fin).__name__}")
        if not isinstance(seq, int):
            raise TypeError(f"Error: seq must be int, got {type(seq).__name__}")
        if not isinstance(msg, str):
            raise TypeError(f"Error: msg must be str, got {type(msg).__name__}")
        
        self.syn = syn
        self.ack = ack
        self.fin = fin
        self.seq = seq
        self.msg = msg

    def __str__(self):
        return f'<SegmentTCP> [syn:{self.syn}, ack:{self.ack}, fin:{self.fin}, seq:{self.seq}, msg:{self.msg}]'
    
    def __repr__(self):
        return str(self)

    @staticmethod
    def parse_segment(tcp_message: bytes) -> 'SegmentTCP':
        tcp_message_s = tcp_message.decode()
        re_groups = HEADER_REGEX.match(tcp_message_s).groups()

        if len(re_groups) != 5:
            print(
                f'Invalid TCP segment:\n{tcp_message_s}\nExpected 5 groups, got {len(re_groups)}')
            sys.exit(1)

        syn, ack, fin, seq, msg = re_groups

        # Type conversion and checking
        errors_found = []
        try:
            assert syn in VALID_BOOLS_STR
            syn = bool(int(syn))
        except Exception as e:
            errors_found.append(f'<{e}> Could not transform syn: {syn}')

        try:
            assert ack in VALID_BOOLS_STR
            ack = bool(int(ack))
        except Exception as e:
            errors_found.append(f'<{e}> Could not transform syn: {ack}')

        try:
            assert fin in VALID_BOOLS_STR
            fin = bool(int(fin))
        except Exception as e:
            errors_found.append(f'<{e}> Could not transform syn: {fin}')

        try:
            assert seq.isdigit()
            seq = int(seq)
        except Exception as e:
            errors_found.append(f'<{e}> Could not transform seq: {seq}')

        # Inform errors if any
        if len(errors_found) > 0:
            print(f"Error parsing TCP Segment: {tcp_message.decode()}")
            for error in errors_found:
                print(f'\t{error}')
            
            sys.exit(1)

        # All checks passed -> return tcp segment
        segment = SegmentTCP(syn, ack, fin, seq, msg)
        return segment


    @staticmethod
    def create_segment(segment: 'SegmentTCP') -> bytes:
        syn_str = '1' if segment.syn else '0'
        ack_str = '1' if segment.ack else '0'
        fin_str = '1' if segment.fin else '0'
        seq_str = str(segment.seq)

        s = f'{syn_str}{ack_str}{fin_str}{HEADER_SEPARATOR}{seq_str}{HEADER_SEPARATOR}{segment.msg}'
        s_bytes = s.encode()
        return s_bytes



class SocketTCP:
    def __init__(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.destination_addr = None
        self.destination_port = None
        self.origin_addr = None
        self.origin_port = None
        self.seq = None
        
        self.state = SocketState.DISCONNECTED


    # Only for servers
    def bind(self, address: tuple[str, int]) -> None:
        self.origin_addr, self.origin_port = address
        self.socket.bind((self.origin_addr, self.origin_port))


    # Client calls this to initiate handshake
    def connect(self, address: tuple[str, int]) -> None:
        self.seq = random.randint(0, 100)
        self.destination_addr, self.destination_port = address

        # Send SYN message
        tcp_segment = SegmentTCP(True, False, False, self.seq, '')
        message_bytes = SegmentTCP.create_segment(tcp_segment)
        print(f'@client.connect, sent syn: {message_bytes}')
        self.socket.sendto(message_bytes, (self.destination_addr, self.destination_port))

        # Wait for ACK+SYN message (with seq+1)
        waiting_ack = True
        while waiting_ack:
            recv_message, recv_address = self.socket.recvfrom(UDP_BUFFER_SIZE)
            print(f'@client.connect, recv syn+ack: {recv_message}')
            recv_segment = SegmentTCP.parse_segment(recv_message)
            
            if recv_segment.ack and recv_segment.syn and recv_segment.seq == self.seq + 1:
                self.seq = self.seq + 1
                waiting_ack = False

        # Send the ACK message
        self.seq += 1
        tcp_segment = SegmentTCP(False, True, False, self.seq, '')
        message_bytes = SegmentTCP.create_segment(tcp_segment)
        print(f'@client.connect, sent ack: {message_bytes}')
        self.socket.sendto(message_bytes, (self.destination_addr, self.destination_port))


    # Server calls this to respond to a client-initiated handshake
    def accept(self) -> 'tuple[SocketTCP, tuple[str, int]]':
        # Waiting for a SYN message
        waiting_syn = True
        while waiting_syn:
            recv_message, recv_address = self.socket.recvfrom(UDP_BUFFER_SIZE)
            print(f'@server.accept, recv syn: {recv_message}')
            recv_segment = SegmentTCP.parse_segment(recv_message)

            if recv_segment.syn:
                self.seq = recv_segment.seq + 1
                waiting_syn = False

        # Send the SYN+ACK message
        tcp_segment = SegmentTCP(True, True, False, self.seq, '')
        message_bytes = SegmentTCP.create_segment(tcp_segment)
        print(f'@server.accept, sent syn+ack: {message_bytes}')
        self.socket.sendto(message_bytes, recv_address)

        # Waiting for ACK message
        waiting_ack = True
        while waiting_ack:
            recv_message, recv_address = self.socket.recvfrom(UDP_BUFFER_SIZE)
            print(f'@server.accept, recv ack: {recv_message}')
            recv_segment = SegmentTCP.parse_segment(recv_message)

            if recv_segment.ack:
                self.seq = recv_segment.seq + 1
                waiting_ack = False

        # Prepare new connection socket to use with this counterpart
        conn_socket = SocketTCP()
        conn_socket.destination_addr, conn_socket.destination_port = recv_address
        conn_socket.origin_addr = self.origin_addr
        conn_socket.origin_port = self.origin_port
        conn_socket.seq = self.seq

        return (conn_socket, recv_address)
    

    def send(self, message: bytes) -> None:
        # Slice message into <MESSAGE_MAX_PACKET_SIZE> sized pieces
        messages_sliced = []
        blocks = int(math.ceil(len(message)/MESSAGE_MAX_PACKET_SIZE))
        for i in range(blocks):
            block_start = i*MESSAGE_MAX_PACKET_SIZE
            block_end = min((i+1)*MESSAGE_MAX_PACKET_SIZE, len(message))
            message_slice = message[block_start: block_end]
            messages_sliced.append(message_slice)

        # First, send the bytecount of the whole message
        self.seq += 1
        tcp_segment = SegmentTCP(False, False, False, self.seq, len(message))
        message_bytes = SegmentTCP.create_segment(tcp_segment)
        print(f'@send, sent bytecount: {message_bytes}')
        self.socket.sendto(message_bytes, (self.destination_addr, self.destination_port))

        # Then, wait for the ACK of the bytecount message
        waiting_ack = True
        while waiting_ack:
            recv_message, recv_address = self.socket.recvfrom(UDP_BUFFER_SIZE)
            print(f'"send, recv bytecount ACK: {recv_message}')
            recv_segment = SegmentTCP.parse_segment(recv_message)

            if recv_segment.ack and recv_segment.seq == self.seq + 1:
                self.seq += 1
                waiting_ack = False

        # Start sending message slices
        for message_slice in messages_sliced:
            self.seq += len(message_slice)
            tcp_segment = SegmentTCP(False, False, False, self.seq, len(message_slice))
            message_bytes = SegmentTCP.create_segment(tcp_segment)
            print(f'@send, sent msg: {message_bytes}')
            self.socket.sendto(message_bytes, (self.destination_addr, self.destination_port))

            # For each message sent, wait the corresponding ACK
            waiting_ack = True
            while waiting_ack:
                recv_message, recv_address = self.socket.recvfrom(UDP_BUFFER_SIZE)
                print(f'"send, recv msg ACK: {recv_message}')
                recv_segment = SegmentTCP.parse_segment(recv_message)

                if recv_segment.ack and recv_segment.seq == self.seq + len(message_slice):
                    self.seq += len(message_slice)
                    waiting_ack = False

    def recv(self, buffer_size: int) -> None:
        # First, wait for the bytecount message
        waiting_bytecount = True
        while waiting_bytecount:
            recv_message, recv_address = self.socket.recvfrom(buffer_size)
            print(f'@recv, recv bytecount: {recv_message}')
            recv_segment = SegmentTCP.parse_segment(recv_message)

            if recv_segment.msg.isdigit() and recv_segment.seq == self.seq + 1:
                self.seq += 1
                message_total_length = int(recv_segment.msg)
                waiting_bytecount = False

        # Then, start receiving messages and assembling the full message
        message = "".encode()
        while len(message) < message_total_length:
            waiting_msg = True
            while waiting_msg:
                recv_message, recv_address = self.socket.recvfrom(buffer_size)
                print(f'@recv, recv msg: {recv_message}')
                recv_segment = SegmentTCP.parse_segment(recv_message)

                if recv_segment.seq > self.seq:
                    self.seq += len(recv_segment.msg)
                    message += recv_message.msg

                    # Send the corresponding ACK
                    # TODO send ack
