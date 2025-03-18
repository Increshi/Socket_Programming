from socket import *
import threading
import sys

username =None
clients = {}
server_socket = None  # Global reference for cleanup
exit_flag = False  # Global flag to signal shutdown

def handle_client_connection(client_socket, address):
    try:
       # client_socket.settimeout(1)  # Prevent blocking indefinitely
        user_details = client_socket.recv(1024).decode()
        username, listening_port = eval(user_details)

        clients[username] = (client_socket, address, listening_port)

        while not exit_flag:
            try:
                request = client_socket.recv(1024).decode()
                if request.lower() == "list":
                    users_list = {user: (addr, port) for user, (_, (addr, _), port) in clients.items()}
                    client_socket.send(str(users_list).encode()[:1024])
                elif request.lower() == "end":
                    break
            except timeout:  # Ignore timeout errors
                continue

    except Exception as e:
        print(f"Host {address[0]} disconnected due to error: {e}")

    finally:
        print(f"Closing client socket for {address[0]}:{address[1]}")
        if username and username in clients:
            del clients[username]
        client_socket.close()

def start_server():
    
    global server_socket, exit_flag
    HOST = "127.0.0.1"
    PORT = 5555
    try:
        server_socket = socket(AF_INET, SOCK_STREAM)
        server_socket.bind((HOST, PORT))
        server_socket.listen(10)
        server_socket.settimeout(1)  # Set timeout to allow graceful shutdown

        print(f"Server listening on {HOST}:{PORT}")

        while not exit_flag:
            try:
                client_socket, address = server_socket.accept()
                print(f"Connection from {address[0]}:{address[1]}")
                thread = threading.Thread(target=handle_client_connection, args=(client_socket, address), daemon=True)
                thread.start()
            except timeout:
                continue  # Allows checking `exit_flag`

    except KeyboardInterrupt:
        print("\n[INFO] Shutting down server...")
        exit_flag = True  # Signal all threads to stop
        server_socket.close()
        sys.exit(0)

if __name__ == "__main__":
    start_server()
