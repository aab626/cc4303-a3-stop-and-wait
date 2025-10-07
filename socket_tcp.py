import socket
import re

HEADER_SEPARATOR = '|||'
HEADER_REGEX = re.compile(r'^(.*)\|\|\|(.*)\|\|\|(.*)\|\|\|(.*)\|\|\|(.*)$')

class SegmentTCP:
    def __init__(self, syn:bool, ack:bool, fin:bool, seq:int, msg:str):
        self.syn = syn
        self.ack = ack
        self.fin = fin
        self.seq = seq
        self.msg = msg



class SocketTCP:
    def __init__(self):
        self.socket = socket.socket(socket.AF_INET, socket.NI_DGRAM)
        self.destination_addr = None
        self.origin_addr = None
        self.sequence = None


    @staticmethod
    def parse_segment(tcp_segment: bytes):
        re_groups = HEADER_REGEX.match(tcp_segment.decode()).groups()
        valid_bools_str = ['0', '1']

        if re_groups[0] in valid_bools_str:
            syn = bool(int(re_groups[0]))
        else:
            print(f'Error: could not transform syn:\'{re_groups[0]}\' into bool.')

        if re_groups[1] in valid_bools_str:
            ack = bool(int(re_groups[1]))
        else:
            print(f'Error: could not transform ack:\'{re_groups[0]}\' into bool.')

        if re_groups[2] in valid_bools_str:
            fin = bool(int(re_groups[2]))
        else:
            print(f'Error: could not transform fin:\'{re_groups[0]}\' into bool.')

        try:
            seq = int(re_groups[3])
        except (TypeError, ValueError):
            print(f'Error: could not transform seq: \'{re_groups[3]}\' into int.')
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

        s = f'{syn_str}{HEADER_SEPARATOR}{ack_str}{HEADER_SEPARATOR}'
        s = s + f'{fin_str}{HEADER_SEPARATOR}{seq_str}{HEADER_SEPARATOR}{segment.msg}'
        return s


seg = SegmentTCP(True, False, True, 12312, "el pepe")
x = SocketTCP.create_segment(seg)
print(x)