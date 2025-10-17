"""
Test Server for the Simplified TCP Socket implementation using UDP sockets with Stop & Wait.
CC4303 - Computer Networks
Author: Augusto Aguayo Barham
"""

from socket_tcp import SocketTCP

BUFFER_SIZE = 16

server_socket = SocketTCP()
server_socket.debug_mode = True
server_socket.bind(('localhost', 8000))

conn_socket, conn_addr = server_socket.accept()

print(' ============== CONNECTION DATA ==============')
print(f'server socket      : {server_socket}')
print(f'conn socket        : {conn_socket}')
print()
print(f'server address     : {server_socket.origin_addr}:{server_socket.origin_port}')
print(f'conn origin address: {conn_socket.origin_addr}:{conn_socket.origin_port}')
print(f'conn dest address  : {conn_socket.destination_addr}:{conn_socket.destination_port}')
print(' =============================================')

while conn_socket.expected_total_bytes is None or len(conn_socket.current_message) < conn_socket.expected_total_bytes:
    recv_bytes = conn_socket.recv(BUFFER_SIZE)

print()
print(' =============== DATA RECEIVED ===============')
print(conn_socket.current_message)

print()
print(' ============= CLOSING CONNECTION ============')
conn_socket.recv_close()
server_socket.socket.close()
