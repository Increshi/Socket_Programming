from socket import *
import threading
import re
import sys

stop_event=threading.Event()

# Function to evaluate the expression following BODMAS rule
def evaluate_expression(expression):
    tokens = expression.split()
    
    # Step 1: Convert tokens to a list of numbers and operators
    numbers = []
    operators = []
    i = 0
    while i < len(tokens):
        if re.match(r"^-?\d+(\.\d+)?$", tokens[i]):  # Match integers and floats
            numbers.append(float(tokens[i]) if '.' in tokens[i] else int(tokens[i]))
        else:
            operators.append(tokens[i])
        i += 1
    
    # Step 2: Apply precedence-1 operations (*, /, %)
    i = 0
    while i < len(operators):
        if operators[i] in ('*', '/', '%'):
            a = numbers.pop(i)
            b = numbers.pop(i)
            op = operators.pop(i)
            if op == '*':
                numbers.insert(i, a * b)
            elif op == '/':
                numbers.insert(i, a / b)
            elif op == '%':
                numbers.insert(i, a % b)
            i -= 1  # Stay at the same index for next iteration
        i += 1
    
    # Step 3: Apply precedence-2 operations (+, -)
    i = 0
    while i < len(operators):
        a = numbers.pop(i)
        b = numbers.pop(i)
        op = operators.pop(i)
        if op == '+':
            numbers.insert(i, a + b)
        elif op == '-':
            numbers.insert(i, a - b)
        i -= 1  # Stay at the same index for next iteration
        i += 1
    
    return numbers[0]

# Function to handle client requests
def handle_client(client_socket):
    while True:
        try:
            expression = client_socket.recv(1024).decode()
            if not expression or expression.strip().upper() == "END":
                break
            result = evaluate_expression(expression.strip())
            client_socket.send(f"RESULT: {result}".encode())
        except Exception as e:
            client_socket.send(f"ERROR: {str(e)}".encode())
    client_socket.close()

# Server function
def server():
    try:
        server_socket = socket(AF_INET, SOCK_STREAM)
        server_socket.bind(('127.0.0.1', 12345))
        server_socket.listen(5)
        server_socket.settimeout(1)
        print("Server started, waiting for connections...")
        while not stop_event.is_set():
            try:
            
                client_socket, _ = server_socket.accept()
                client_thread = threading.Thread(target=handle_client, args=(client_socket,))
                client_thread.start()
            except timeout:
                continue
    except KeyboardInterrupt:
        print("\nServer shutting down...")
        stop_event.set()  # Set the event to signal other threads (if needed)
        server_socket.close()
        sys.exit(0)
    
        

   


# Client function
def client():
    client_socket = socket(AF_INET, SOCK_STREAM)
    client_socket.connect(('127.0.0.1', 12345))
    
    while True:
        expression = input("[INPUT] ")
        client_socket.send(expression.encode())
        if expression.strip().upper() == "END":
            break
        response = client_socket.recv(1024).decode()
        print(f"[OUTPUT] {response}")
    client_socket.close()

if __name__ == "__main__":
    choice = input("Start as server (s) or client (c)?: ")
    if choice.lower() == 's':
        server()
    elif choice.lower() == 'c':
        client()