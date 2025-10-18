"""
Test Client for the Simplified TCP Socket implementation using UDP sockets with Stop & Wait.
CC4303 - Computer Networks
Author: Augusto Aguayo Barham
"""

import argparse
from socket_tcp import SocketTCP

parser = argparse.ArgumentParser(description='Actividad 3: Sockets orientados a conexión con Stop & Wait')
parser.add_argument('host', help='Server hostname or IP address')
parser.add_argument('port', type=int, help='Server port number')
args = parser.parse_args()

# Read STDIN
data = ''
while True:
    try:
        line = input()
        data += line + '\n'
    except EOFError:
        break

data_bytes = data.encode()

# Create socket and connect
client_socket = SocketTCP()
client_socket.debug_mode = True
client_socket.connect((args.host, args.port))

print(' ============== CONNECTION DATA ==============')
print(f'client socket : {client_socket}')
print(f'client address: {client_socket.origin_addr}:{client_socket.origin_port}')
print(f'server address: {client_socket.destination_addr}:{client_socket.destination_port}')
print(' =============================================')
print()
print(' =============== SENDING DATA ================')
print()
client_socket.send(data_bytes)
print()
print(' ============= CLOSING CONNECTION ============')
client_socket.close()
