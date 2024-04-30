import socket
import threading
import time

HOST = '0.0.0.0'
PORT = 9999
clients = {}  # Now using a dictionary to track last heartbeat time


def handle_client(conn, addr):
    print(f"Connected by {addr}")
    while True:
        try:
            data = conn.recv(1024).decode().strip()
            if not data:
                break
            print(f"Received data: {data}")
            if 'request_nodes' in data:
                response = ','.join(clients.keys())
                conn.sendall(response.encode())
            elif 'register' in data:
                _, host, port = data.split(':')
                key = f'{host}:{port}'
                clients[key] = time.time()  # Update last seen time
            elif 'heartbeat' in data:
                _, host, port = data.split(':')
                key = f'{host}:{port}'
                if key in clients:
                    clients[key] = time.time()  # Update last seen time
            elif 'do_not_join' in data:
                _, host, port = data.split(':')
                key = f'{host}:{port}'
                if key in clients:
                    del clients[key]
            print(f"Active clients: {clients}")
        except Exception as e:
            print(f"Error: {e}")
            break
    conn.close()
    print(f"Disconnected by {addr}")


def cleanup_clients():
    current_time = time.time()
    timeout = 15  # seconds
    keys_to_remove = [
        k for k, v in clients.items() if current_time - v > timeout]
    for key in keys_to_remove:
        del clients[key]
    threading.Timer(10, cleanup_clients).start()  # Check every 10 seconds


def start_server():
    # Start the cleanup thread
    threading.Thread(target=cleanup_clients).start()
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
