import socket
import threading

HOST = '0.0.0.0'
PORT = 9999
clients = set()


def handle_client(conn, addr):
    print(f"Connected by {addr}")
    while True:
        try:
            data = conn.recv(1024).decode().strip()
            if not data:
                break
            print(f"Received data: {data}")
            if 'request_nodes' in data:
                response = ','.join(clients)
                conn.sendall(response.encode())
            elif 'register' in data:
                _, host, port = data.split(':')
                key = f'{host}:{port}'
                clients.add(key)
        except Exception as e:
            print(f"Error: {e}")
            break
    conn.close()
    print(f"Disconnected by {addr}")


def start_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        print(f"Server started at {HOST}:{PORT}")
        while True:
            conn, addr = s.accept()
            thread = threading.Thread(target=handle_client, args=(conn, addr))
            thread.start()


if __name__ == '__main__':
    start_server()
