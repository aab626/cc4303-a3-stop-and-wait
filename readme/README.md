# Actividad 3: Sockets orientados a conexión con Stop & Wait 

> **Nombre:** Augusto Aguayo Barham  
> **Fecha:** 20-10-2025

---

## Uso del Cliente/Servidor de pruebas

Primero, se debe levantar el servidor mediante:

```bash
python ./server.py
```

Este crea un `SocketTCP`, hace `bind` a la dirección `('localhost', 8000)` y acepta una conexión entrante. Luego, acepta segmentos con 16 bytes en el área de datos (configurable mediante `BUFFER_SIZE` en `server.py`). Una vez llega completo se imprime el mensaje y cierra la conexión.

Luego, para ejecutar el cliente se debe indicar el host de destino, el puerto y el archivo a enviar (mediante `stdin`):

```bash
python ./client.py localhost 8000 < file.txt
```

Esto envía los contenidos de `file.txt` a la dirección `('localhost', 8000)` utilizando la mecánica de *Stop & Wait*.

## Estructuras de Datos

### SocketTCP

El archivo `socket_tcp.py` contiene la clase `SocketTCP`, la que es básicamente un *wrapper* de un `socket` no orientado a conexión de *Python*. Esta clase implementa comunicación confiable mediante *TCP Simplificado*, implementando las mecánicas de *Stop & Wait*.

La clase también dispone de un modo *debug*, el que imprime información por pantalla con cada acción tomada (envío y recepción de segmentos principalmente) por la clase internamente, para activar esto:

```python
socket = SocketTCP()
socket.debug_mode = True
```

A continuación, la API pública de `SocketTCP`:

#### bind
```python
bind(address: tuple[str, int]) -> None
```

Asocia el socket UDP interno a una dirección para escuchar conexiones entrantes.

#### connect
```python
connect(address: tuple[str, int]) -> None
```

Método para iniciar el *3-Way Handshake* por parte del cliente, consiste en las siguientes partes:

1. Elige un número de sequencia `seq=x` aleatorio entre 0 y 100.
2. Envía el mensaje `SYN`, con `seq=x`.
3. Espera un `ACK+SYN`, con `seq=x+1`.
4. Envía un `ACK`, con `seq=x+2`.

Una vez se completa esto, se da por coordinada la comunicación bilateral.

#### accept
```python
accept() -> tuple[SocketTCP, (str, int)]
```

Método para responder a un *3-Way Handshake* usada por parte del servidor, consiste en las siguientes partes:

1. Espera un mensaje `SYN`, con algún número de secuencia desconocido `seq=x`.
2. Una vez recibido, crea un nuevo `SocketTCP` para comunicarse con esta conexión.
2. Con este nuevo `SocketTCP`, responde con un `ACK+SYN`, con `seq=x+1`.
3. Espera un `ACK` final, con `seq=x+2`.

Una vez se completan estos 3 pasos, se da por coordinada la comunicación bilateral entre el cliente y el nuevo `SocketTCP`.

#### send
```python
send(message: bytes) -> None
```

Envía el mensaje `message` a la dirección asociada al `SocketTCP`, implementando *Stop & Wait*.

Primero siempre envía un segmento con el largo de los datos a recibir, luego se envía el mensaje original dividido en trozos de 16 bytes cada uno (tamaño controlado mediante la variable `MESSAGE_MAX_PACKET_SIZE`).

El envío de un segmento y subsecuente espera de su `ACK` correspondiente se hace mediante los métodos auxiliares `_send_segment` y `_wait_message`, que se desglosan más abajo.

#### recv
```python
recv(buffer_size: int) -> bytes
```

Método que recibe una cantidad de bytes indicado por la variable `buffer_size` desde el socket interno, usando *Stop & Wait*.

Se encarga de diferenciar la recepción de el número total de bytes a recibir (*bytecount*) de los datos en sí, tambien maneja duplicados comparando el número de secuencia.

Al igual que el método `send`, esta abstrae el envío y recepción de segmentos mediante los métodos `_send_segment` y `_wait_message`.

#### close
```python
close() -> None
```

Método para cerrar la conexión del lado del *Host B* tolerante a pérdidas, con el siguiente mecanismo:

1. Envía `FIN`.
2. Espera el `FIN+ACK` correspondiente, si ocurre un *timeout* envía `FIN` nuevamente (hasta 3 veces).
3. Una vez llega, envía `ACK` hasta 3 veces con un *timeout* entre ellas.
4. Al llegar o si pasan los 3 *timeouts*, asume que la conexión se cerró.

#### recv_close
```python
recv_close(self) -> None
```

Método que se encarga de manejar el cierre de conexión desde el lado del *Host A*, implementa *Stop & Wait* de la siguiente forma:

1. Espera un mensaje `FIN`.
2. Al llegar, envía `FIN+ACK`
3. Luego, espera el `ACK` correspondiente hasta 3 veces, luego asume que la conexión se cerró.


#### Métodos auxiliares

Se usaron los métodos para enviar y recibir segmentos 

##### _send_segment
```python
_send_segment(self, tcp_segment) -> None
```

Serializa una estructura `SegmentTCP` y la envía a la dirección asociada al `SocketTCP`.
Delega las responsabilidades de *Stop & Wait* mediante *timeouts* a las funciones que la llamen.

##### _wait_message
```python
_wait_segment(self, 
              f_condition: Callable[['SocketTCP', SegmentTCP], bool], 
              f_update_seq: Callable[['SocketTCP', SegmentTCP], int]
              ) -> tuple[SegmentTCP, tuple[str, int]]:
```

Método bloqueante que espera recibir un `TCPSegment` (con *timeouts*) que cumpla la condición especificada por la función `f_condition`, si no cumple la condición entonces se trata de un mensaje duplicado o algún mensaje distinto no esperado. En caso de un mensaje duplicado reenvía el `ACK` correspondiente.

Una vez recibido un mensaje que fue verificado por `f_condition`, se actualiza el número de secuencia según lo obtenido por `f_update_seq`.

Este diseño permite manejar las distintas configuraciones de mensajes: sincronización, datos y cierre.

##### _log
```python
_log(self, message: str) -> None
```

Método auxiliar para imprimir por pantalla todas las operaciones de la clase, solo si el campo `debug_mode` es `True`.

### SegmentTCP

Estructura para almacenamiento y verificación de los segmentos recibidos del *TCP Simplificado*. Se encuentra en `segment_tcp.py`.

Utiliza el formato para cada segmento: `[SYN]|||[ACK]|||[FIN]|||[SEQ]|||[DATOS]`. Donde, los flags `SYN`, `ACK` y `FIN` son booleanos representados por 0 y 1, `SEQ` como un entero, y `DATOS` como un string de a lo más 16 caractéres.

#### parse_segment
```python
@staticmethod
parse_segment(tcp_message: bytes) -> SegmentTCP
```

Método estático para construir una estructura `SegmentTCP` a partir de los bytes obtenidos en una respuesta del sistema *TCP Simplificado*. Realiza la lectura y validación mediante el uso de expresiones regulares.

#### create_segment
```python
@staticmethod
create_segment(segment: 'SegmentTCP') -> bytes
```

Método estático para crear una cadena de bytes en el formato especificado anteriormente a partir del segmento. Usado para enviar el segmento.

## Desiciones de Diseño

* Para el mensaje de total de bytes esperados antes de comenzar a envíar los datos, se aumenta el `SEQ` en 1, al igual que los mensajes del *Handshake*.
* Se utiliza un *timeout* de 1 segundo para poder observar los mensajes de depuración con mayor detenimiento.
* Se asume que siempre el cliente y el servidor estarán de acuerdo en la cantidad de bytes a enviar y recibir (el largo de los segmentos y el tamaño del buffer de recepción respectivamente), así se evita el caso borde de `len(message_received) >= buffer_size`.
* El servidor acepta solo una conexión, recibe el mensaje de forma completa y después cierra la conexión y se detiene. Fue escrito así para poder facilitar las pruebas de forma completa: *Handshake* -> Envio de datos -> cierre.

## Diagramas

### 3-Way Handshake

### Caso borde, último ACK perdído en el Handshake

## Pruebas

