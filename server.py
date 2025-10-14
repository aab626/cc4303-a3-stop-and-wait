from socket_tcp import SocketTCP

BUFFER_SIZE = 16

server_socket = SocketTCP()
server_socket.bind(('localhost', 5000))

conn_socket, conn_addr = server_socket.accept()

print()
print(f'server socket      : {server_socket}')
print(f'conn socket        : {conn_socket}')

print(f'server address     : {server_socket.origin_addr}:{server_socket.origin_port}')
print(f'conn origin address: {conn_socket.origin_addr}:{conn_socket.origin_port}')
print(f'conn dest address  : {conn_socket.destination_addr}:{conn_socket.destination_port}')

while conn_socket.expected_total_bytes is None or len(conn_socket.current_message) < conn_socket.expected_total_bytes:
    print()
    recv_bytes = conn_socket.recv(BUFFER_SIZE)
    # print(f'Received data: {recv_bytes}')
    # print(f'Current message: {conn_socket.current_message}')

print()
print('Final message:')
print(conn_socket.current_message)
