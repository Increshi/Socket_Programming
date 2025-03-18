from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend
from socket import *
import os
import sys
import threading
import random
import hashlib
import base64


# Diffie-Hellman Parameters
p = int(os.getenv('P', '31')) 
g = int(os.getenv('G', '7'))   

exit_flag = threading.Event()  # Global flag to signal all threads to exit

def generate_private_key():
    return random.randint(1, p - 1)

def compute_public_key(private_key):
    return pow(g, private_key, p)

def compute_shared_secret(public_key, private_key):
    return pow(public_key, private_key, p)

def derive_aes_key(shared_secret):
    random.seed(shared_secret)   #Adding seed to generate same set of sequence  random numbers every time we run the program
    random_number = random.getrandbits(256)
    hashed_secret_key = hashlib.sha256(str(random_number).encode()).digest()
    return hashed_secret_key

def encrypt_message(message, key):
    init_vector = os.urandom(16)
    cipher = Cipher(algorithms.AES(key), modes.CBC(init_vector), backend=default_backend())
    padder = padding.PKCS7(128).padder()
    padded_message = padder.update(message.encode()) + padder.finalize()
    encryptor = cipher.encryptor()
    cipher_text = encryptor.update(padded_message) + encryptor.finalize()
    base64Encoded_msg=base64.b64encode(init_vector+ cipher_text)
    return base64Encoded_msg.decode()

def decrypt_message(encrypted_message, key):
    encrypted_data = base64.b64decode(encrypted_message)
    init_vector, cipher_text = encrypted_data[:16], encrypted_data[16:]
    cipher = Cipher(algorithms.AES(key), modes.CBC(init_vector), backend=default_backend())
    decryptor = cipher.decryptor()
    padded_message = decryptor.update(cipher_text) + decryptor.finalize()
    unpadder = padding.PKCS7(128).unpadder()
    original_msg=unpadder.update(padded_message) + unpadder.finalize()
    return original_msg.decode()

def handle_incoming_messages(sock, private_key, stop_event, key_holder):
    while not stop_event.is_set() and not exit_flag.is_set():
        try:
            msg = sock.recv(1024).decode()
            if not msg:
                break
            if msg == "EOM":
                print("Peer has left the chat. Closing connection.")
                sock.close()
                stop_event.set()
                break
            if msg.startswith("DH_public_key:"):
                public_key_received = int(msg.split(":")[1])
                shared_secret = compute_shared_secret(public_key_received, private_key)
                aes_key = derive_aes_key(shared_secret)
                key_holder["key"] = aes_key
                print(f"Derived AES Key: {aes_key.hex()}")
                continue
            if key_holder["key"] is None:
                print("AES Key is not yet established!")
                continue
            decrypted_msg = decrypt_message(msg, key_holder["key"])
            print(f"\n[Cipher]: {msg}\n[Plain]: {decrypted_msg}\n[Send]: ", end="", flush=True)
        except Exception as e:
            print(f"[ERROR] {e}")
            break

def send_messages(conn, stop_event, key_holder):
    while not stop_event.is_set() and not exit_flag.is_set():
        if key_holder["key"] is not None:
            message = input("[Send]: ")
            if message.strip().lower() == "eom":
                conn.send("EOM".encode())
                print("Chat ended, connection closed.")
                conn.close()
                stop_event.set()
                break
            encrypted_msg = encrypt_message(message, key_holder["key"])
            conn.send(encrypted_msg.encode())
            print(f"[Cipher]: {encrypted_msg}")
        

def listen_for_incoming_connections(peer_socket, private_key):
    peer_socket.listen(5)
    print(f"Listening for P2P connections on port {peer_socket.getsockname()[1]}...")
    while not exit_flag.is_set():
        try:
            conn, addr = peer_socket.accept()
            print(f"Connected to peer at {addr}")
            public_key = compute_public_key(private_key)
            conn.send(f"DH_public_key:{public_key}".encode())
            stop_event = threading.Event()
            key_holder = {"key": None}
            receive_msg_thread = threading.Thread(target=handle_incoming_messages, args=(conn, private_key, stop_event, key_holder))
            receive_msg_thread.start()
            send_messages(conn, stop_event, key_holder)
        except Exception as e:
            print(f"[ERROR] Peer connection failed: {e}")
            break

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
                    stop_event = threading.Event()
                    key_holder = {"key": None}
                    threading.Thread(target=handle_incoming_messages, args=(chat_socket, private_key, stop_event, key_holder)).start()
                    send_messages(chat_socket, stop_event, key_holder)
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
