from socket import *
import threading
import random
import os
import hashlib
import sys

# Diffie-Hellman Parameters
p = int(os.getenv('P', '31'))  # Prime number
g = int(os.getenv('G', '7'))   # Generator

exit_flag = threading.Event()  # Global flag to signal all threads to exit

def generate_private_key():
    return random.randint(1, p - 1)

def compute_public_key(private_key):
    return pow(g, private_key, p)

def compute_shared_secret(public_key, private_key):
    return pow(public_key, private_key, p)

def derive_aes_key(shared_secret):
    
    random.seed(shared_secret)
    random_number = random.getrandbits(256)
    hashed_secret = hashlib.sha256(str(random_number).encode()).digest()
    return hashed_secret

def handle_incoming_messages(sock, private_key):
    
    shared_secret = None
    while not exit_flag.is_set():
        try:
            msg = sock.recv(1024).decode()
            if not msg:
                break
            if msg == "EOM":
                print("Peer has left the chat. Closing connection.")
                sock.close()
                exit_flag.set()
                break
            if msg.startswith("DH_public_key:"):
                public_key_received = int(msg.split(":")[1])
                shared_secret = compute_shared_secret(public_key_received, private_key)
                print(f"Shared Secret Computed: {shared_secret}")
                encryption_key = derive_aes_key(shared_secret)
                print(f"Derived Encryption Key: {encryption_key.hex()}")
                continue
            print(f"\n[Received]: {msg}\n[Send]: ", end="", flush=True)
        except:
            break

def listen_for_incoming_connections(peer_socket, private_key):
    peer_socket.listen(5)
    print(f"Listening for P2P connections on port {peer_socket.getsockname()[1]}...")
    while not exit_flag.is_set():
        try:
            conn, addr = peer_socket.accept()
            print(f"Connected to peer at {addr}")
            public_key = compute_public_key(private_key)
            print(f"My Public key is :{public_key}")
            conn.send(f"DH_public_key:{public_key}".encode())
            thread = threading.Thread(target=handle_incoming_messages, args=(conn, private_key))
            thread.start()
            send_messages(conn)
        except Exception as e:
            print(f"[ERROR] Peer connection failed: {e}")
            break

def send_messages(conn):
    while not exit_flag.is_set():
        message = input("[Send]: \n")
        if message.strip().lower() == "eom":
            conn.send("EOM".encode())
            print("Chat ended, connection closed.")
            conn.close()
            exit_flag.set()
            break
        conn.send(message.encode())

def start_client():
    try:
        server_ip = "127.0.0.1"
        server_port = 5555
        client_socket = socket(AF_INET, SOCK_STREAM)
        client_socket.connect((server_ip, server_port))
        username = input("Enter your username: ")
        private_key = generate_private_key()
        peer_socket = socket(AF_INET, SOCK_STREAM)
        peer_socket.bind(("0.0.0.0", 0))
        listener_thread=threading.Thread(target=listen_for_incoming_connections, args=(peer_socket, private_key), daemon=True)
        listener_thread.start()
        client_info=(username, peer_socket.getsockname()[1])
        client_socket.send(str(client_info).encode())
        while not exit_flag.is_set():
            command = input("\nEnter 'LIST' to retreive users List or 'CONNECT <username>' to chat: ")
            if command == "LIST":
                client_socket.send(command.encode())
                users = eval(client_socket.recv(1024).decode())
                print(f"\nConnected Users: {users}")
            elif command.startswith("CONNECT "):
                _, connected_user = command.split(" ")
                if connected_user in users:
                    connected_ip, connected_port = users[connected_user]
                    chat_socket = socket(AF_INET, SOCK_STREAM)
                    chat_socket.connect((connected_ip,connected_port))
                    chat_socket.send(f"DH_public_key:{compute_public_key(private_key)}".encode())
                    threading.Thread(target=handle_incoming_messages, args=(chat_socket, private_key)).start()
                    send_messages(chat_socket)
                
                else:
                    print("[ERROR] User not found!")
    except KeyboardInterrupt:
        print("\nExiting chat...")
        exit_flag.set()
        peer_socket.close()
        client_socket.close()
        sys.exit(0)

if __name__ == "__main__":
    start_client()
