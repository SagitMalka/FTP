import _thread
import signal
import timeit

from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer
import socket
import threading
import os
import time
import logging

import packet
from timer import Timer

# from custom_handler import MyHandler

# RUDP configuration
RUDP_PORT = 5000
RUDP_HOST = '127.0.0.1'
FTP_PORT = 21
PACKET_SIZE = 1024
SLEEP = 0.1
TIMEOUT_INTERVAL = 0.5
WINDOW_SIZE = 4

# TCP configuration
TCP_HOST = '0.0.0.0'
TCP_PORT = 22

FTP_DIRECTORY = 'store/'
BUFFER_SIZE = 1024
users = {"Sagitush": "123456",
         "Lielelel": "password"}

# shared resources across threads
base = 0
mutex = _thread.allocate_lock()
send_timer = Timer()


# set window size
def set_window_size(num_packets):
    global base
    return min(WINDOW_SIZE, num_packets - base)


def file_to_packets(file_name):
    # open file
    try:
        file = open("store/" + file_name, 'rb')
    except IOError:
        print('filed open file', file_name)
        return

    # make all packets and add to the buffer
    packets = []
    seq_num = 0
    while True:
        data = file.read(PACKET_SIZE)
        if not data:
            break
        packets.append(packet.make(seq_num, data))
        seq_num += 1

    window_size = set_window_size(len(packets))
    file.close()

    return packets, len(packets), window_size


# send thread
def send_file(conn, file_name):
    global mutex
    global base
    global send_timer

    conn.recv(BUFFER_SIZE).decode()
    rudp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    packets, num_packets, window_size = file_to_packets(file_name)
    next_to_send, base = 0, 0

    # start receiver thread:
    rudp_sock.sendto("ack".encode(), (RUDP_HOST, RUDP_PORT))
    receive_thread = threading.Thread(target=receive_ack, args=(rudp_sock,))
    receive_thread.start()


    while base < num_packets:
        mutex.acquire()

        # send all packet in the window
        while next_to_send < base + window_size:
            print('sending packet', next_to_send)
            rudp_sock.sendto(packets[next_to_send], (RUDP_HOST, RUDP_PORT))
            next_to_send += 1

        # start timer
        if not send_timer.is_running():
            send_timer.start(TIMEOUT_INTERVAL)

        # wait for ACK or time out
        while send_timer.is_running() and not send_timer.timeout:
            mutex.release()
            print('taking a nap.')
            time.sleep(SLEEP)
            mutex.acquire()

        if send_timer.timeout:
            print('time out detected')
            # send_timer.stop()
            next_to_send = base
        else:
            #  move window [i - i+3] =>  [i+1 - i+4]
        #     # print('sliding the window')
            window_size = set_window_size(num_packets)
        mutex.release()

    # send empty packet as sentinel
    rudp_sock.sendto(packet.make_empty(), (RUDP_HOST, RUDP_PORT))


def receive_ack(sock):
    global mutex
    global base
    global send_timer

    print(sock)
    while True:
        # sock.sendto(data.encode(), (RUDP_HOST, RUDP_PORT))
        # sock.recvfrom(BUFFER_SIZE)
        pak = sock.recvfrom(1024)
        ack, g_data = packet.extract(pak)

        # if got ACK for the first packet in-flight
        print('got ACK', ack)
        if ack >= base:
            mutex.acquire()
            base = (ack + 1) % 4
            print('base update:', base)
            send_timer.stop()
            mutex.release()


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

def foo(conn):
    conn.recv(BUFFER_SIZE).decode()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    while True:
        sock.sendto("data".encode(),  (RUDP_HOST, RUDP_PORT))
        ans = sock.recvfrom(1024)
        print(ans)



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
                    # foo(conn)
                    send_file(conn, filename)
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
