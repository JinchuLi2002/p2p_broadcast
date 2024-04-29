import socket
import argparse
import threading
import time
import json
import os
import shutil

# A global set to keep track of message IDs that have been processed
seen_messages = set()


def register_with_bootstrap(host, port, my_port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((host, port))
        print("Connected to server")
        s.sendall(f"register:{socket.gethostname()}:{my_port}".encode())
        time.sleep(0.5)  # Allow time for server to process the request
        s.sendall(b'request_nodes')
        response = s.recv(1024).decode()
        print(f"Active nodes: {response}")
        return response


def handle_incoming_connections(server_socket, connected_peers):
    while True:
        try:
            client_socket, addr = server_socket.accept()
            print(f"Accepted connection from {addr}")
            connected_peers.append(client_socket)
            threading.Thread(target=handle_peer_communication,
                             args=(client_socket, connected_peers)).start()
        except Exception as e:
            print(f"Error accepting connections: {e}")
            break


def send_heartbeat(server_host, server_port, my_port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((server_host, server_port))
        heartbeat_message = f"heartbeat:{socket.gethostname()}:{my_port}"
        while True:
            s.sendall(heartbeat_message.encode())
            time.sleep(10)


def process_message(data, sock, peers):
    raise NotImplementedError("This function should be implemented")


def handle_peer_communication(peer_sock, connected_peers):
    file_data = bytearray()  # To hold received data chunks
    try:
        while True:
            data = peer_sock.recv(1024)
            print(f"Received data: {data}")
            if data == b'finished':
                break

            # Assume all incoming data in this context is file data
            file_data.extend(data)

    except Exception as e:
        print(f"Error receiving from peer: {e}")

    finally:
        if file_data:
            # Assuming all data is file data for simplicity here
            handle_file_data(file_data, peer_sock)
        peer_sock.close()
        connected_peers.remove(peer_sock)


def target_dir(file_name):
    # Define how to determine the target directory for saving the file
    return os.path.join(os.getcwd(), 'received_files', file_name)


def save_file(data, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'wb') as f:
        f.write(data)


def handle_file_data(data, source_sock):
    # Extracting receiver info for directory naming
    receiver_info = f"{socket.gethostname()}_{source_sock.getsockname()[1]}"
    target_dir = os.path.join(os.getcwd(), receiver_info)
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
    with open(os.path.join(target_dir, 'received_file'), 'wb') as f:
        f.write(data)  # Directly write the byte data


def forward_message(message, source_sock, connected_peers):
    for sock in connected_peers:
        if sock != source_sock:
            try:
                sock.sendall(message.encode())
            except Exception as e:
                print(f"Error forwarding message to {sock}: {e}")


def create_message(originator, last_sender, content):
    message_id = f"{time.time()}"
    message = {
        'originator': originator,
        'last_sender': last_sender,
        'message_id': message_id,
        'content': content
    }
    return json.dumps(message)


def start_listening(my_port, connected_peers):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('', my_port))
    server_socket.listen()
    print(f"Listening for peer connections on port {my_port}")
    handle_incoming_connections(server_socket, connected_peers)


def connect_to_peers(peers, my_port, connected_peers):
    for peer in peers.split(','):
        if peer:
            host, port = peer.split(':')
            if host == socket.gethostname() and int(port) == my_port:
                continue
            try:
                peer_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                peer_sock.connect((host, int(port)))
                connected_peers.append(peer_sock)
                print(f"Connected to peer at {host}:{port}")
                threading.Thread(target=handle_peer_communication, args=(
                    peer_sock, connected_peers)).start()
            except Exception as e:
                print(f"Failed to connect to {host}:{port}: {e}")


def send_broadcast_message(data, connected_peers, my_port):
    my_hostname_port = f"{socket.gethostname()}:{my_port}"
    chunk_size = 1024  # Adjust chunk size as needed
    for sock in connected_peers:
        try:
            # Split the data into chunks and send each chunk
            for start in range(0, len(data), chunk_size):
                chunk = data[start:start + chunk_size]
                sock.sendall(chunk)
                # Add a slight delay to prevent overwhelming the receiver
                # time.sleep(0.001)
            time.sleep(0.5)
            sock.sendall(b'finished')  # Indicate end of data
        except Exception as e:
            print(f"Failed to send broadcast message to {sock}: {e}")
            sock.close()  # Ensure to close on failure
            connected_peers.remove(sock)  # Remove the disconnected peer


def main(bootstrap_host, bootstrap_port, my_port):
    connected_peers = []
    peers = register_with_bootstrap(bootstrap_host, bootstrap_port, my_port)
    if peers:
        connect_to_peers(peers, my_port, connected_peers)
    threading.Thread(target=send_heartbeat, args=(
        bootstrap_host, bootstrap_port, my_port)).start()
    threading.Thread(target=start_listening, args=(
        my_port, connected_peers)).start()

    try:
        while True:
            file_path = input(
                "Enter file path to broadcast or type 'exit' to quit: ")
            if file_path == 'exit':
                break
            if os.path.exists(file_path):
                with open(file_path, 'rb') as file:
                    data = file.read()
                    send_broadcast_message(data, connected_peers, my_port)
    except KeyboardInterrupt:
        print("Client is shutting down.")
    finally:
        for sock in connected_peers:
            sock.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='P2P Client')
    parser.add_argument('--bootstrap_host', type=str,
                        required=True, help='Bootstrap server host')
    parser.add_argument('--bootstrap_port', type=int,
                        required=True, help='Bootstrap server port')
    parser.add_argument('--my_port', type=int, required=True,
                        help='Local port for this peer')
    args = parser.parse_args()

    main(args.bootstrap_host, args.bootstrap_port, args.my_port)
