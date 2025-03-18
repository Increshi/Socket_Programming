from socket import *
import threading
import sys

exit_flag = threading.Event() 

def handle_incoming_messages(sock):
    
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
            print(f"\n[Received]: {msg}\n[Send]: ", end="", flush=True)
        except:
            break

def listen_for_incoming_connections(peer_socket):
    peer_socket.listen(5)
    print(f"Listening for P2P connections on port {peer_socket.getsockname()[1]}...")
    while not exit_flag.is_set():
        try:
            conn, addr = peer_socket.accept()
            print(f"Connected to peer at {addr}")
            thread = threading.Thread(target=handle_incoming_messages, args=(conn,))
            thread.start()
            send_messages(conn)
        except Exception as e:
            print(f"[ERROR] Peer connection failed: {e}")
            break

def send_messages(conn):
    while not exit_flag.is_set():
        message = input("[Send]: ")
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
        # Start peer-to-peer connection handling in a separate thread
        peer_socket = socket(AF_INET, SOCK_STREAM)
        peer_socket.bind(("0.0.0.0", 0))  # Bind to any available port
        listening_port = peer_socket.getsockname()[1]
        listener_thread=threading.Thread(target=listen_for_incoming_connections, args=(peer_socket,), daemon=True)
        listener_thread.start()
        client_info = (username, listening_port)
        client_socket.send(str(client_info).encode())
        while not exit_flag.is_set():
            command = input("\nEnter 'LIST' to retreive users List or 'CONNECT <username>' to chat: ")
            if command == "LIST":
                client_socket.send(command.encode())
                users = eval(client_socket.recv(1024).decode())  # Convert received string to dictionary
                print(f"\nConnected Users: {users}")
            elif command.startswith("CONNECT "):
                _, connected_user = command.split(" ")
                if connected_user in users:
                    connected_ip, connected_port = users[connected_user]
                    chat_socket = socket(AF_INET, SOCK_STREAM)
                    chat_socket.connect((connected_ip,connected_port))
                    threading.Thread(target=handle_incoming_messages, args=(chat_socket,)).start()
                    send_messages(chat_socket)
                else:
                    print("[ERROR] User not found!")

    except KeyboardInterrupt:
        print("\nExiting chat...")
        exit_flag.set()
        peer_socket.close()
        client_socket.close()
        sys.exit(0)  # Force exit after cleanup
        
if __name__ == "__main__":
    start_client()
