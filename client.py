from threading import Lock
import socket
import argparse
import threading
import time
import json
import os
import shutil
import traceback

# A global set to keep track of message IDs that have been processed
received_files = set()
is_busy = False
peer_ports = {}
# connection_locks = {}


def register_with_bootstrap(host, port, my_port, join_bootstrap):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((host, port))
        print("Connected to server")
        s.sendall(f"register:{socket.gethostname()}:{my_port}".encode())
        time.sleep(0.5)  # Allow time for server to process the request
        s.sendall(b'request_nodes')
        response = s.recv(1024).decode()
        print(f"Active nodes: {response}")
        time.sleep(0.5)
        if join_bootstrap:
            s.sendall(b'join')
        else:
            s.sendall(f'do_not_join:{socket.gethostname()}:{my_port}'.encode())

        return response


def handle_incoming_connections(server_socket, connected_peers, my_port):
    while True:
        try:
            client_socket, addr = server_socket.accept()
            port_data = client_socket.recv(1024).decode()
            peer_ports[client_socket] = port_data
            readable_addr = f"{addr[0]}:{port_data}"
            print(f"Accepted connection from {readable_addr}")
            connected_peers.append(client_socket)
            threading.Thread(target=handle_peer_communication,
                             args=(client_socket, connected_peers, my_port)).start()
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


last_received_message = None


def handle_peer_communication(peer_sock, connected_peers, my_port):
    global is_busy, received_files, last_received_message
    file_data = bytearray()  # To hold received data chunks
    try:
        while True:
            # with conn_lock:
            data = peer_sock.recv(1024)
            last_received_message = data
            # print(f"Received data: {data}")
            if data.decode() == "check_ready":
                # Respond based on the current busy status
                if is_busy:
                    peer_sock.sendall("busy".encode())
                else:
                    peer_sock.sendall("ready".encode())
                    is_busy = True
            elif data.startswith(b'start:'):

                file_id = data.decode().split(':')[1]  # Extract file ID
                if file_id in received_files:
                    print("File already received, ignoring...")
                    peer_sock.sendall("ignored".encode())
                else:
                    received_files.add(file_id)
                continue
            elif data == b'finished':
                # Process the received file
                handle_file_data(file_data, my_port)
                is_busy = False  # Reset busy status after processing the file

                if file_id:
                    send_broadcast_message(
                        file_data, connected_peers, my_port, file_id, peer_sock)
                file_data.clear()
            else:
                # Collect file data
                file_data.extend(data)

    except Exception as e:
        print(f"Error receiving from peer: {e}\n{traceback.format_exc()}")

    finally:
        if file_data:
            # Assume all data is file data for simplicity here
            handle_file_data(file_data, my_port)
        peer_sock.close()
        connected_peers.remove(peer_sock)
        is_busy = False


def target_dir(file_name):
    # Define how to determine the target directory for saving the file
    return os.path.join(os.getcwd(), 'received_files', file_name)


def save_file(data, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'wb') as f:
        f.write(data)
    print(f"File saved to {path} at {time.time()}")


def handle_file_data(data, my_port):
    # Use the current instance's hostname and the provided my_port for directory naming
    receiver_info = f"Workspace_{socket.gethostname()}_{my_port}"

    target_dir = os.path.join(os.getcwd(), receiver_info)

    if not os.path.exists(target_dir):
        os.makedirs(target_dir)

    file_path = os.path.join(target_dir, 'received_file')
    with open(file_path, 'wb') as f:
        f.write(data)  # Directly write the byte data
    print(f"File saved to {file_path} at {time.time()}")


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
    handle_incoming_connections(server_socket, connected_peers, my_port)


def connect_to_peers(peers, my_port, connected_peers):
    for peer in peers.split(','):
        if peer:
            host, port = peer.split(':')
            if host == socket.gethostname() and int(port) == my_port:
                continue
            try:
                peer_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                peer_sock.connect((host, int(port)))
                peer_sock.sendall(str(my_port).encode())
                connected_peers.append(peer_sock)
                print(f"Connected to peer at {host}:{port}")
                threading.Thread(target=handle_peer_communication, args=(
                    peer_sock, connected_peers, my_port)).start()
            except Exception as e:
                print(f"Failed to connect to {host}:{port}: {e}")


def send_broadcast_message(data, connected_peers, my_port, file_id, source_sock):
    my_hostname_port = f"{socket.gethostname()}:{my_port}"
    print(f'Sending broadcast message to {len(connected_peers)} peers')
    chunk_size = 1024  # Adjust chunk size as needed
    for sock in connected_peers:
        # conn_lock = get_connection_lock(sock)
        # with conn_lock:
        if sock == source_sock:
            print(f"Skipping sending to SELF")
            continue
        try:
            sock.sendall("check_ready".encode())
            time.sleep(0.5)
            response = last_received_message
            if response == b"ready":
                print(f"Sending file")
                sock.sendall(f"start:{file_id}".encode())
                # Proceed to send the file data in chunks
                for start in range(0, len(data), chunk_size):
                    chunk = data[start:start + chunk_size]
                    sock.sendall(chunk)
                    # Add a slight delay to prevent overwhelming the receiver
                    # time.sleep(0.001)
                time.sleep(0.5)
                sock.sendall(b'finished')
            else:
                print(f"Target is busy.")
            # Split the data into chunks and send each chunk
            # Indicate end of data
        except Exception as e:
            print(
                f"Failed to send broadcast message to {sock}: {e}")
            sock.close()  # Ensure to close on failure
            connected_peers.remove(sock)  # Remove the disconnected peer


def main(bootstrap_host, bootstrap_port, my_port, join_bootstrap):
    connected_peers = []
    peers = register_with_bootstrap(
        bootstrap_host, bootstrap_port, my_port, join_bootstrap)
    if peers:
        connect_to_peers(peers, my_port, connected_peers)
    if join_bootstrap:
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
                    file_id = f"{file_path}_{time.time()}"
                    start_time = time.time()
                    print(f'start_time: {start_time}')
                    send_broadcast_message(
                        data, connected_peers, my_port, file_id, None)
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
    parser.add_argument('--join_bootstrap', action='store_true')
    args = parser.parse_args()

    main(args.bootstrap_host, args.bootstrap_port,
         args.my_port, args.join_bootstrap)
