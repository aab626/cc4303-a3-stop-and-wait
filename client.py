import socket
import math

SEND_BUFFER_SIZE = 16

msg = 'Para testear el comportamiento de una red bajo pérdida de mensajes y/o retardo (delay) en el tiempo de envío de dichos mensajes podemos usar netem. Podemos ejecutar netem en localhost usando el siguiente comando'
msg = msg.encode()

client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

blocks = int(math.ceil(len(msg)/SEND_BUFFER_SIZE))
for i in range(blocks):
    x0, x1 = i*SEND_BUFFER_SIZE, min((i+1)*SEND_BUFFER_SIZE, len(msg))
    msg_sliced = msg[x0: x1]
    
    print(f'[{x0}:{x1}, {len(msg_sliced)}] -> {msg_sliced}')
    
    client_socket.sendto(msg_sliced, ('localhost', 5000))

client_socket.close()