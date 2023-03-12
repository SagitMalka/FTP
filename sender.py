from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer
import socket
import threading
import os
import time
import logging

# from custom_handler import MyHandler

# RUDP configuration
RUDP_PORT = 5000
RUDP_HOST = '127.0.0.1'
FTP_PORT = 21

# TCP configuration
TCP_HOST = '0.0.0.0'
TCP_PORT = 22

FTP_DIRECTORY = 'store/'
BUFFER_SIZE = 1024
users = {"Sagitush": "123456",
         "Lielelel": "password"}

def send_rudp_packet(sock, data):
    # for i in range(5):
    return sock.sendto(data.encode(), (RUDP_HOST, RUDP_PORT))

    #     sock.settimeout(3)
    #     ans = sock.recvfrom(BUFFER_SIZE)
    #     print(f"ans = {ans.decode()}")
    #     if ans.decode() == 'ack':
    #         return True
    #
    # return False


def send_file_via_rudp(file_name, conn):
    # wait for rudp socket to be ready
    conn.recv(BUFFER_SIZE).decode()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    print(f"Sending {file_name} ...")

    f = open("store/" + file_name, "r")

    data = f.read(BUFFER_SIZE)

    while data:
        if not send_rudp_packet(sock, data):
            print("TimeOut Error. Server didn't get ack for packet in time.")
            return

        data = f.read(BUFFER_SIZE)
        time.sleep(0.02)  # Give receiver a bit time to save


    print(f"{file_name} sent successfully!")
    sock.close()
    f.close()


def close_connection(conn, addr):
    print(f"[DISCONNECTED] {addr} disconnected.")
    conn.send("Goodbye.\n".encode())
    conn.close()
    rudp_socket.close()


def send_file_list(conn):
    # Send a list of files in the current directory
    files = os.listdir('store/')
    file_list = ' * ' + '\n * '.join(files)
    conn.send(f" Server's File List:\n{file_list}\n".encode())


def init_tcp_conn():
    # Set up the FTP server authorizer
    authorizer = DummyAuthorizer()
    for username, password in users.items():
        authorizer.add_user(username, password, FTP_DIRECTORY, perm='elradfmw')

    # Set up the FTP server handler
    handler = FTPHandler  # MyHandler
    handler.authorizer = authorizer
    # logging.basicConfig(filename='logs/ftp_server.log', level=logging.NOTSET)

    server = FTPServer((TCP_HOST, TCP_PORT), handler)

    def run_tcp_server():
        server.serve_forever()

    # Set up the FTP server and start it
    tcp_thread = threading.Thread(target=run_tcp_server)
    tcp_thread.start()

    return server


def run_server(conn, addr):
    print(f"[NEW CONNECTION] {addr} connected.")

    # Send welcome message
    conn.send("220 Welcome to the RUDP FTP server\n".encode())

    # Receive FTP commands from client
    while True:
        data = conn.recv(BUFFER_SIZE).decode()
        print(f"Command from client:\n{data}")

        if data:
            command, *args = data.split()

            # Process FTP commands
            if command == "QUIT":
                close_connection(conn, addr)
                return

            elif command == "LIST":
                send_file_list(conn)

            elif command == "GET":
                if args[0] != "--tcp":
                    filename = args[0]
                    send_file_via_rudp(filename, conn)
            elif command == 'UPLOAD':
                pass
            else:
                conn.send("ERROR. Command not implemented.\n".encode())
        else:
            print(f"[DISCONNECTED] {addr} disconnected.")
            break

    close_connection(conn, addr)


def listen_to_ftp_requests():
    while True:
        conn, addr = ftp_requests_socket.accept()
        ftp_thread = threading.Thread(target=run_server, args=(conn, addr))
        ftp_thread.start()


if __name__ == '__main__':
    print(f"Starting server (pid = {os.getpid()})...")

    # open sockets
    rudp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    ftp_requests_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    ftp_requests_socket.bind(('', FTP_PORT))
    ftp_requests_socket.listen()

    # run TCP server
    tcp_server = init_tcp_conn()

    # Listen for incoming FTP connections
    request_thread = threading.Thread(target=listen_to_ftp_requests)
    request_thread.start()

    while True:
        command = input("> ")
        if command == "CLOSE":
            ftp_requests_socket.close()
            rudp_socket.close()
            tcp_server.close()
            break
