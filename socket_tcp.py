import socket
import re
import random

HEADER_SEPARATOR = '|||'
HEADER_REGEX = re.compile(r'^(.*)\|\|\|(.*)\|\|\|(.*)\|\|\|(.*)\|\|\|(.*)$')

class SegmentTCP:
    def __init__(self, syn:bool, ack:bool, fin:bool, seq:int, msg:str):
        self.syn = syn
        self.ack = ack
        self.fin = fin
        self.seq = seq
        self.msg = msg

    @staticmethod
    def parse_segment(*args):
        valid_bools_str = ['0', '1']

        # todo check case of tuple of 5
        if len(args) == 1 and isinstance(args[0], bytes):
            tcp_segment = args[0]
            re_groups = HEADER_REGEX.match(tcp_segment.decode()).groups()

            if len(re_groups) != 5:
                print(f'Invalid TCP segment:\n{tcp_segment}\nExpected 5 groups, got {len(re_groups)}')
                exit(1)

            syn, ack, fin, seq, msg = re_groups


        if re_groups[0] in valid_bools_str:
            syn = bool(int(re_groups[0]))
        else:
            print(
                f'Error: could not transform syn:\'{re_groups[0]}\' into bool.')
            exit(1)

        if re_groups[1] in valid_bools_str:
            ack = bool(int(re_groups[1]))
        else:
            print(
                f'Error: could not transform ack:\'{re_groups[0]}\' into bool.')
            exit(1)

        if re_groups[2] in valid_bools_str:
            fin = bool(int(re_groups[2]))
        else:
            print(
                f'Error: could not transform fin:\'{re_groups[0]}\' into bool.')
            exit(1)

        try:
            seq = int(re_groups[3])
        except (TypeError, ValueError):
            print(
                f'Error: could not transform seq: \'{re_groups[3]}\' into int.')
            exit(1)

        msg = re_groups[4]
        segment = SegmentTCP(syn, ack, fin, seq, msg)
        return segment

    @staticmethod
    def create_segment(segment: SegmentTCP):
        syn_str = '1' if segment.syn else '0'
        ack_str = '1' if segment.ack else '0'
        fin_str = '1' if segment.fin else '0'
        seq_str = str(segment.seq)

        s = f'{syn_str}'
        s = s + f'{HEADER_SEPARATOR}{ack_str}'
        s = s + f'{HEADER_SEPARATOR}{fin_str}'
        s = s + f'{HEADER_SEPARATOR}{seq_str}'
        s = s + f'{segment.msg}'
        return s




class SocketTCP:
    def __init__(self):
        self.socket = socket.socket(socket.AF_INET, socket.NI_DGRAM)
        self.destination_addr = None
        self.destination_port = None
        self.origin_addr = None
        self.sequence = None


    def bind(self, address: tuple[str, int]) -> None:
        self.origin_addr, self.origin_port = address
        self.socket.bind((self.origin_addr, self.origin_port))


    def connect(self, address: tuple[str, int]):
        seq = random.randint(0, 100)
        # TODO tcp client handshake start

    
    def accept(self):
        SocketTCP.create_segment()



