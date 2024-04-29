import socket
import argparse
import threading
import time

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


def handle_peer_communication(peer_sock, connected_peers):
    while True:
        try:
            message = peer_sock.recv(1024).decode()
            if message:
                msg_id, text = message.split(':', 1)
                if msg_id not in seen_messages:
                    seen_messages.add(msg_id)
                    print(f"Message from peer: {text}")
                    # Forward the message to all other peers
                    forward_message(message, peer_sock, connected_peers)
            else:
                break
        except Exception as e:
            print(f"Error receiving from peer: {e}")
            break
    peer_sock.close()
    connected_peers.remove(peer_sock)


def forward_message(message, source_sock, connected_peers):
    for sock in connected_peers:
        if sock != source_sock:
            try:
                sock.sendall(message.encode())
            except Exception as e:
                print(f"Error forwarding message to {sock}: {e}")


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


def send_broadcast_message(message, connected_peers):
    msg_id = f"{time.time()}"
    full_message = f"{msg_id}:{message}"
    seen_messages.add(msg_id)
    for sock in connected_peers:
        try:
            sock.sendall(full_message.encode())
        except Exception as e:
            print(f"Failed to send broadcast message to {sock}: {e}")


def main(bootstrap_host, bootstrap_port, my_port):
    connected_peers = []
    peers = register_with_bootstrap(bootstrap_host, bootstrap_port, my_port)
    if peers:
        connect_to_peers(peers, my_port, connected_peers)
    threading.Thread(target=start_listening, args=(
        my_port, connected_peers)).start()

    try:
        while True:
            msg = input("Enter message to broadcast or type 'exit' to quit: ")
            if msg == 'exit':
                break
            send_broadcast_message(msg, connected_peers)
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
