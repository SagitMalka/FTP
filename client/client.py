import hashlib
import os
import threading

import socket
from ftplib import FTP
from handler import *
from constants import *

# GLOBALS
SEQ_FLAG = 0

class Client:
    def __init__(self):
        self.rudp_fd = None
        self.fd = None
        self.ftp = None
        self.file = None
        self.ftp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # Create an FTP socket
        self.ftp_socket.connect(('127.0.0.1', FTP_PORT))  # Connect to the FTP server

    def start(self):
        thread = self.connect_to_server()
        self.ftp = FTP()
        thread.join()

    def close(self):
        # Close the FTP connection
        self.ftp_socket.close()

    def tcp_upload(self, file_name):
        print(f"TCP upload {file_name}...")
        try:
            self.start_tcp_connection()
            with open(file_name, 'rb') as f:
                self.ftp.storbinary(f'STOR {file_name}', f)
        except Exception as e:
            print(f"Upload Failed. Error: '{e}'")
        print("Finish!")

    def tcp_download(self, file_name):
        self.start_tcp_connection()
        print(f"Downloading {file_name}...")
        try:
            with open(file_name, "wb") as file:
                self.ftp.retrbinary(f"RETR {file_name}", file.write)
        except Exception as e:
            print(f"Download Failed. Error: '{e}'")
        print("Finish!")

    def start_tcp_connection(self):
        username = input("User name: ")
        password = input("Password: ")

        self.ftp.connect(TCP_HOST, TCP_PORT)
        self.ftp.login(username, password)

    # @staticmethod
    # def open_file_to_write(file_name, packets_list):
    #     global last_byte
    #     with open(file_name, 'ab') as file:
    #         for i in packets_list:
    #             while i:
    #                 file.write()
    #     last_byte = str(bytearray(packets_list[-1])[-1])
    #     time.sleep(0.15)

    def connect_to_server(self):
        # Print the welcome message
        data = self.ftp_socket.recv(BUFFER_SIZE)
        print(data.decode())
        thread = threading.Thread(target=send_requests, args=(self, ))
        thread.start()
        return thread

    def delete_file(self, file_name, msg=""):
        self.file.close()
        print(msg)
        os.remove("r_" + file_name)

    @staticmethod
    def process_packet(pkt):
        print(pkt)
        header, pkt_payload = pkt.split(PACKET_DELIMITER1)
        hash_code, seq, length = header.decode().split(HEADER_DELIMITER)
        return hash_code, seq, int(length), pkt_payload

    @staticmethod
    def check_seq(seq):
        return SEQ_FLAG == int(seq == True)

    @staticmethod
    def check_hash(payload_hash, payload):
        return payload_hash == hashlib.sha1(payload).hexdigest()


    def send_ack(self, seq_num, packet_len, addr):
        print(30*"===")
        print("send ack")
        print(30 * "===")

        self.rudp_fd.sendto((str(seq_num) + "," + str(packet_len)).encode(), addr)

    def start_rudp_connection(self):
        self.rudp_fd = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.rudp_fd.settimeout(CONNECTION_TIMEOUT)
        self.rudp_fd.bind(RUDP_ADDR)

    def close_rudp_con(self):
        self.rudp_fd.close()
        self.file.close()

    def rudp_download(self, file_name):
        global SEQ_FLAG

        pkt_ctr = 0
        # Start - Connection initiation
        while True:

            # seqNoFlag = 0
            self.file = open("r_" + file_name, 'wb')

            try:
                # Receive indefinitely
                while 1:
                    # Receive response
                    print('\nWaiting to receive..')
                    # Reset failed trials on successful transmission
                    receive_trials_count = 0

                    try:
                        data, addr = self.rudp_fd.recvfrom(4096)

                    except Exception as e:
                        receive_trials_count += 1
                        if receive_trials_count > MAX_TRIALS:
                            self.delete_file(file_name=file_name,
                                        msg=f"\nFailed to get data from server, download abort!\n")
                            break

                        print(f"\nFailed num to receive packet, error msg: '{e}'")
                        continue

                    payload_hash, seq_num, packet_len, payload = self.process_packet(data)

                    if self.check_hash(payload_hash, payload) and self.check_seq(seq_num):
                        if payload == FILE_NOT_FOUND:
                            self.delete_file(file_name=file_name,
                                        msg="Requested file could not be found on the server")
                            self.close_rudp_con()
                            return
                        else:
                            self.file.write(payload)

                        print(f"Sequence number: {seq_num}\nLength: {packet_len}")
                        print(f"Server: {RUDP_HOST} on port {RUDP_PORT}")

                        self.send_ack(seq_num, packet_len, addr)
                    else:
                        # print("Checksum mismatch detected, dropping packet")
                        if not self.check_hash(payload_hash, payload):
                            print("checksum error")
                        else:
                            print("seq error")
                        print(f"Server: {RUDP_HOST} on port {RUDP_PORT}")
                        continue

                    if packet_len < PACKET_SIZE:
                        # seq_num = int(not seq_num)
                        return

            finally:
                print("Closing socket")
            self.close_rudp_con()


if __name__ == '__main__':
    client = Client()
    client.start()
