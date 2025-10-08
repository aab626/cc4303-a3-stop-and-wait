import socket
from socket_tcp import SocketTCP

buffer_size = 16

# socket_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# message, address = socket_udp.recvfrom(buffer_size)
# socket_udp.sendto(message, address)

# server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# server_socket.bind(('localhost', 5000))

server_socket = SocketTCP()
server_socket.bind(('localhost', 5000))
conn_socket, conn_addr = server_socket.accept()

print('handshake completed!')
print(f'server socket      : {server_socket}')
print(f'conn socket        : {conn_socket}')

print(f'server address     : {server_socket.origin_addr}:{server_socket.origin_port}')
print(f'conn origin address: {conn_socket.origin_addr}:{conn_socket.origin_port}')
print(f'conn dest address  : {conn_socket.destination_addr}:{conn_socket.destination_port}')


# msg_complete = ''

# while True:
#     try:
#         print('waiting...')
#         recv_message, recv_address = server_socket.recvfrom(buffer_size)
#         msg_complete = msg_complete + recv_message.decode()

#         print(f'received msg: <{recv_address}>:[{len(recv_message.decode())}]<{recv_message.decode()}> ')
#     except KeyboardInterrupt:
#         break

# print(msg_complete)
# server_socket.close()
