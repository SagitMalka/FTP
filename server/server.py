import datetime
import random
import time

from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer
import socket
import threading
import os

from packet import Packet
from constants import *
from handler import *

# GLOBALS
SEQ_FLAG = 0


class Server:
    def __init__(self):
        self.file_name = None
        self.rudp_fd = None
        print(f"Starting server (pid = {os.getpid()})...")

        # open sockets
        self.rudp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.ftp_requests_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.ftp_requests_socket.bind(('', FTP_PORT))
        self.ftp_requests_socket.listen()

        # run TCP server
        self.tcp_server = self.init_tcp_conn()

        # Listen for incoming FTP connections
        self.request_thread = threading.Thread(target=self.start_listening_socket)

    def set_file_name(self, name):
        self.file_name = name
    def close_connection(self, conn, addr):
        print(f"[DISCONNECTED] {addr} disconnected.")
        conn.send("Goodbye.\n".encode())
        conn.close()
        self.rudp_socket.close()

    def send_file_list(self, conn):
        # Send a list of files in the current directory
        files = os.listdir('store/')
        file_list = ' * ' + '\n * '.join(files)
        conn.send(f" Server's File List:\n{file_list}\n".encode())

    def init_tcp_conn(self):
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

    def start_listening_socket(self):
        while True:
            conn, addr = self.ftp_requests_socket.accept()
            self.ftp_thread = threading.Thread(target=read_requests, args=(conn, addr, self))
            self.ftp_thread.start()

    def read_file(self, sock, file_name):
        try:
            print("Opening file %s" % file_name)
            file = open("store/" + file_name, 'rb')
            data = file.read()
            file.close()
            return data
        except Exception as e:
            pkt = Packet(FILE_NOT_FOUND)
            sock.sendto(pkt.encode(), RUDP_ADDR)
            print(f"Fail to read file, replying with FNF.\nError:{e}")
            return

    def check_ack(self, ack, pkt):
        return ack.decode().split(",")[0] == str(pkt.seq)

    def send_via_rudp(self):
        self.rudp_fd = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.rudp_fd.settimeout(TIMEOUT)

        drop_count = 0
        packet_count = 0
        time.sleep(0.5)
        if LOSS_SIMULATE:
            packet_loss_percentage = float(input("Set PLP (0-99)%: ")) / 100.0
            while packet_loss_percentage < 0 or packet_loss_percentage >= 1:
                packet_loss_percentage = float(input("Enter a valid PLP value. Set PLP (0-99)%: ")) / 100.0
        else:
            packet_loss_percentage = 0

        start_time = time.time()
        print("Request started at: " + str(datetime.datetime.utcnow()))

        try:
            # Read file
            data = self.read_file(self.rudp_fd, self.file_name)
            if not data:
                return

            chunk = 0
            while chunk < (len(data) / 2048) + 1:
                packet_count += 1
                randomised_plp = random.random()
                if packet_loss_percentage < randomised_plp:
                    msg = data[chunk * 2048:chunk * 2048 + 2048]
                    pkt = Packet(msg)
                    if not pkt.payload:
                        break

                    # Send packet
                    a = pkt.encode()
                    sent = self.rudp_fd.sendto(a, RUDP_ADDR)
                    print(f'Sent {sent} bytes back to {RUDP_ADDR}, awaiting acknowledgment..')
                    self.rudp_fd.settimeout(CONNECTION_TIMEOUT)
                    try:
                        ack, _ = self.rudp_fd.recvfrom(100)
                    except Exception as e:
                        print(f"Time out reached, resending ...{chunk}")
                        continue

                    if self.check_ack(ack, pkt):
                        pkt.seq = int(not pkt.seq)
                        print("Acknowledged!")
                        chunk += 1
                else:
                    print(f"\n{30 * '-'}\n\t\tDropped packet\n{30 * '-'}\n")
                    drop_count += 1
            print(f"Packets sent: {str(packet_count)}")
            if LOSS_SIMULATE:
                print("Dropped packets: " + str(drop_count) + "\nComputed drop rate: %.2f" % float(
                    float(drop_count) / float(packet_count) * 100.0))
        except Exception as e:
            print(f"Internal server error:{e}")

    def start(self):
        self.request_thread.start()

        while True:
            command = input("> ")
            if command == "CLOSE":
                self.ftp_requests_socket.close()
                self.rudp_socket.close()
                self.tcp_server.close()
                break


if __name__ == '__main__':
    s = Server()
    s.start()
