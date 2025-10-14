import re
import sys

HEADER_SEPATOR_UNIT = '|'
HEADER_SEPARATOR = f'{HEADER_SEPATOR_UNIT*3}'
HEADER_REGEX = re.compile(
    rf'^([01]){re.escape(HEADER_SEPARATOR)}([01]){re.escape(HEADER_SEPARATOR)}([01]){re.escape(HEADER_SEPARATOR)}(\d+){re.escape(HEADER_SEPARATOR)}(.*)$',
    re.DOTALL
)

VALID_BOOLS_STR = ['0', '1']

class SegmentTCP:
    def __init__(self, syn:bool, ack:bool, fin:bool, seq:int, msg):
        if not isinstance(syn, bool):
            raise TypeError(f"Error: syn must be bool, got {type(syn).__name__}")
        if not isinstance(ack, bool):
            raise TypeError(f"Error: ack must be bool, got {type(ack).__name__}")
        if not isinstance(fin, bool):
            raise TypeError(f"Error: fin must be bool, got {type(fin).__name__}")
        if not isinstance(seq, int):
            raise TypeError(f"Error: seq must be int, got {type(seq).__name__}")
        
        try:
            msg = str(msg)
        except Exception as e:
            raise TypeError(f'Error: {e}\nmsg could not be converted to str:\nmsg: {msg}')
        
        self.syn = syn
        self.ack = ack
        self.fin = fin
        self.seq = seq
        self.msg = msg

    def __str__(self):
        return f'<SegmentTCP> [SYN:{self.syn}, ACK:{self.ack}, FIN:{self.fin}, SEQ:{self.seq}, MSG:{self.msg}]'
    
    def __repr__(self):
        return str(self)

    @staticmethod
    def parse_segment(tcp_message: bytes) -> 'SegmentTCP':
        tcp_message_s = tcp_message.decode()
        re_groups = HEADER_REGEX.match(tcp_message_s).groups()

        if len(re_groups) != 5:
            print(f'Invalid TCP segment:\n{tcp_message_s}\nExpected 5 groups, got {len(re_groups)}')
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

        s = f'{syn_str}{HEADER_SEPARATOR}{ack_str}{HEADER_SEPARATOR}{fin_str}{HEADER_SEPARATOR}{seq_str}{HEADER_SEPARATOR}{segment.msg}'
        s_bytes = s.encode()
        return s_bytes