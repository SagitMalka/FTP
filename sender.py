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
MTU = 1500
PACKET_SIZE = 1024
SLEEP = 0.1
TIMEOUT = 10   # sec
WINDOW_SIZE = 1

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

def handshake(conn):
    step1 = False
    message = ''
    addr = ''

    for i in range (5):
        try:
            temp1, temp2 = receive_ack(conn)
            if temp1 == 'TIMEOUT':
                continue
            if not step1:
                message = temp1
                addr = temp2
                step1 = True
        except IOError:
          continue

    if message == '' or addr == '':
        print('packet loss ')
        return False

    if message[0] == 'HandShake':

        for k in range (5):
            conn.sendto('ACK'.encode(), addr)

        time.sleep(1)

        print('rudp connection established')

        response = ''
        addr = ''
        step3 = False
        for i in range(5):
            try:
                temp1, temp2 = receive_ack(conn)
                if temp1 == 'TIMEOUT':
                    continue
                if not step3:
                    response = temp1
                    addr = temp2
                    step3 = True
            except IOError:
                continue

        if response == '' or addr == '':
            print('client timeout')
            return False, -1

        if response [0] == 'ACK':
            print('3- way - hand shake complite')
            return True, addr
        elif response [0] == 'NACK':
            return  False, -1

    else:
        return False, -1





def file_to_packets(file_name) -> list:
    # open file
    try:
        file = open("store/" + file_name, 'rb')
    except IOError:
        print('filed open file', file_name)
        return

    # make all packets and add to the buffer
    packets_list = []
    seq_num = 0
    while packet_data := file.read(MTU - 10):
        packets_list.append(packet_data)
    return packets_list
    #     seq_num += 1
    #
    # window_size = set_window_size(len(packets_list))
    # file.close()
    #
    # return packets_list, len(packets_list), window_size



def file_sender_try(conn, clientaddr, packets_list):
    conn.settimeout(TIMEOUT * 2)
    index = 0
    ack_list = []
    for i in range(len(packets_list)):
        ack_list.append(False)
    acked_packet = 0
    cwnd = 10
    first_loss = False
    halfway = True

    while index != len(packets_list):
        print('cwnd:', cwnd)

        window_frame = min(index + cwnd, len(packets_list))
        for k in range(index, window_frame):
            if halfway:
                if acked_packet == len(packets_list) / 2:
                    k += 1
                    halfway = False
                    print('half way sending')
                    # continue_req = transform

                    try:
                        result = conn.recv(4096).decode()
                        if result == 'STOP':
                            print('asked to stop.. im jast a server..')
                            break
                    except IOError:
                        print('client time out')
                        break
                if not ack_list[k]:
                    checksum = packet.calc_checksum(packets_list[k])
                    packetk = packet.make(k, checksum, packets_list[k], cwnd)
                    conn.sendto(packetk, clientaddr)

            checker = index

            for j in range (index, window_frame):
                result, addr = receive_ack(conn)
                threshhold = cwnd / 2

                if result == 'TIMEOUT' or result[0] == 'TIMEOUT':
                    if not first_loss:
                        first_loss = True
                        print('first loss event', result)
                    cwnd = 10

                elif result[0] == 'NACK':
                    if not first_loss:
                        first_loss = True
                        print('first loss event', result)
                    if cwnd > 10:
                        cwnd -= 1

                if result[0] == 'ACK':
                    acked_packet += 1
                    if not first_loss:
                        cwnd *= 2
                    else:
                        if cwnd < threshhold:
                            cwnd *= 2
                        else:
                            cwnd += 1
                    if cwnd > 0.1 * len(packets_list):
                        cwnd = int(0.1 * len(packets_list))
                    ack_list[int(result[1])] = True

                if result[0] == 'ACKALL':
                    print('all packets received')
                    index = len(packets_list)
                    continue

                if index != len(packets_list):
                    for i in range (index, checker + window_frame + 1):
                        if ack_list[i]:
                            index += 1
                        else:
                            break
            print('done')





def UDP_thred(filename, port):
    # conn.recv(BUFFER_SIZE).decode()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind('127.0.0.1', port)
    sock.settimeout(60)
    connection = sock

    twh, addr = handshake(connection)
    if twh:
        print('3 way HS = sucsses')
        packets = file_to_packets(file_name= filename)
        for i in range (5):
            connection.sendto(('length_' + str(len(packets))).encode(), addr)

        time.sleep(1)
        print('sent')
        file_sender_try(connection, addr, packets)
    else:
        print('error 3 w HS')


    sock.close()



 #  send thread
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
            send_timer.start(TIMEOUT)

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
    try:
        message, addr = sock.recvfrom(8192)
        message = message.decode()
        message = message.split('_', 1)
        return message, addr
    except TimeoutError:
        return 'TIMEOUT', -1

    # global mutex
    # global base
    # global send_timer
    #
    # print(sock)
    # while True:
    #     # sock.sendto(data.encode(), (RUDP_HOST, RUDP_PORT))
    #     # sock.recvfrom(BUFFER_SIZE)
    #     pak = sock.recvfrom(1024)
    #     ack, g_data = packet.extract(pak)
    #
    #     # if got ACK for the first packet in-flight
    #     print('got ACK', ack)
    #     if ack >= base:
    #         mutex.acquire()
    #         base = (ack + 1) % 4
    #         print('base update:', base)
    #         send_timer.stop()
    #         mutex.release()


# set window size
def set_window_size(num_packets):
    global base
    return min(WINDOW_SIZE, num_packets - base)

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
                    # send_file(conn, filename)
                    file_sender_try(conn=conn, clientaddr=addr, packets_list=file_to_packets(filename))
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
