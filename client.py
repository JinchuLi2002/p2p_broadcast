import socket
import time  # Import for adding delays


def register_with_bootstrap(host, port, my_port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((host, port))
        print("Connected to server")
        # Send registration command
        s.sendall(f"register:{socket.gethostname()}:{my_port}".encode())
        # Short delay to ensure messages are processed separately
        time.sleep(0.5)
        # Send request for node list
        s.sendall(b'request_nodes')
        response = s.recv(1024).decode()
        print(f"Active nodes: {response}")


if __name__ == '__main__':
    bootstrap_host = '127.0.0.1'  # Use localhost or the known static IP
    bootstrap_port = 9999
    my_port = 5000
    register_with_bootstrap(bootstrap_host, bootstrap_port, my_port)
