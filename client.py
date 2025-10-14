from socket_tcp import SocketTCP

msg = 'An orange cat slipped into the server room, where cool air hummed and tiny lights blinked like stars. She padded between tall machines, batting at cables and chasing her shadow. A spinning fan caught her eye, and she pounced with a soft thump. Soon, she curled up by a warm router, purring as the servers buzzed gently around her.'
msg = msg.encode()

client_socket = SocketTCP()
client_socket.connect(('localhost', 5000))

print()
print(f'client socket : {client_socket}')
print(f'client address: {client_socket.origin_addr}:{client_socket.origin_port}')
print(f'server address: {client_socket.destination_addr}:{client_socket.destination_port}')
print()

print(f'Sending message: {msg.decode()}')
print()
client_socket.send(msg)
