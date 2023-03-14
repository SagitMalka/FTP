import select
import socket
from ftplib import FTP
import time
import packet

RUDP_PORT = 5000  # Define the RUDP port number to use
RUDP_HOST = '127.0.0.1'  # Define the RUDP HOST number to use
FTP_PORT = 21  # Define the FTP port number to use
BUFFER_SIZE = 1024  # Define the buffer size for data transfer
MAX_RETRIES = 5  # Define the maximum number of RUDP transfer retries
RETRY_DELAY = 1  # Define the delay between RUDP transfer retries (in seconds)
resultFLAG = False

# Define the FTP server settings
TCP_HOST = '0.0.0.0'
TCP_PORT = 22
last_byte = 0

def tcp_upload(file_name):
    print(f"TCP upload {file_name}...")
    server = start_tcp_connection()
    with open(file_name, 'rb') as f:
        server.storbinary(f'STOR {file_name}', f)
    print("Finish!")


def tcp_download(file_name):
    server = start_tcp_connection()
    print(f"Downloading {file_name}...")
    with open(file_name, "wb") as file:
        server.retrbinary(f"RETR {file_name}", file.write)
    print("Finish!")


def start_tcp_connection():
    username = 'Sagit'  #input("User name: ")
    password = '123456'  #input("Password: ")

    ftp = FTP()
    ftp.connect(TCP_HOST, TCP_PORT)
    ftp.login(username, password)

    return ftp

def recv_msg(sock):
    try:
        msg, addr = sock.recvfrom(8192)
        msg.decode()
        msg.split('_', 1)
        return msg, addr
    except OSError:
        return 'TIMEOUT', -1,

def recv_packets(sock):
    try:
        trs_msg, addr = sock.recvfrom(8192)
        temp, packett = packet.extract(trs_msg)
        seq_num = temp[0]
        checksum = temp [1]
        cwnd = temp[2]
        return packett, addr, seq_num, checksum, cwnd
    except OSError:
        return 'TIMEOUT', -1, -1, -1, 10

def handshake(sock, server_addr):
    global resultFLAG
    for i in range(5):
        sock.sendto('HandShake'.encode(), server_addr)
    time.sleep(1)

    result = ''
    addr = ''
    step2 = False
    for i in range(5):
        try:
            temp1, temp2 = recv_msg(sock)
            if temp1 == 'TIMEOUT':
                pass
            if not step2:
                result = temp1
                addr = temp2
                step2 = True
        except IOError:
          pass

    if result == '' or addr == '':
        print('couldnt get an ack')

    if result[0] == 'ACK':
        resultFLAG = True
        time.sleep(0.2)
    else:
        resultFLAG = True
        time.sleep(0.2)

    for i in range(5):
        sock.sendto('ACK'.encode(), server_addr)

    time.sleep(1)


def foo():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((RUDP_HOST, RUDP_PORT))
    ftp_socket.send("rudp socket is up!".encode())
    while True:
        ans, addr = sock.recvfrom(1024)
        print(ans)
        sock.sendto("ack".encode(), addr)


def open_file_to_write(file_name, packets_list):
    global last_byte
    with open(file_name, 'ab') as file:
        for i in packets_list:
            while i:
                file.write()
    last_byte = str(bytearray(packets_list[-1])[-1])
    time.sleep(0.15)


    # try:
    #     file = open(file_name, 'wb')
    #     return file
    # except IOError:
    #     print('filed open file', file_name)
    #     return

def UDP_thread(file_name):
    server_addr = (RUDP_HOST, RUDP_PORT)
    rudp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    rudp_socket.settimeout(60)
    rudp_socket.connect(server_addr)

    global resultFLAG
    resultFLAG = True
    time.sleep(0.5)
    if handshake(rudp_socket, server_addr):
        resultFLAG = True
        time.sleep(0.5)

        packet_len = ''
        step4 = False
        for i in range(5):
            try:
                temp1, _ = recv_msg(rudp_socket)
                if not step4:
                    packet_len = temp1[1]
                    step4 = True
            except IOError or UnicodeError:
                pass

        if packet_len == '':
            resultFLAG = True
            time.sleep(0.5)

        packet_list = [] * int(packet_len)
        resultFLAG = True
        time.sleep(0.5)

        rudp_download_file(rudp_socket, server_addr, packet_list, file_name)
    else:
        print('3 way HS fail')
    rudp_socket.close()


def rudp_download_file(rudp_socket, server_addr, packets_list, file_name):
    index = 0
    rudp_socket.settimeout(60)
    cwnd = 10

    while index != len(packets_list):
        window_frame = min(index + cwnd + 2, len(packets_list))
        for i in range(index, window_frame):
            packet, addr, seq_num, checksum, cwnd = recv_packets(rudp_socket)
            if packet == 'TIMEOUT' or seq_num == -1:
                rudp_socket.sendto(('NACK_' + str(seq_num)).encode(), server_addr)
            else:
                try:
                    rspo = packet.decode()
                    rspo.split('_', 1)
                    if packet.calc_checksum(packet) == checksum:
                        packets_list[seq_num] = packet
                        rudp_socket.sendto(('ACK_' + str(seq_num)).encode(), server_addr)
                        index += 1
                    else:
                        rudp_socket.sendto(('NACK_' + str(seq_num)).encode(), server_addr)

                except UnicodeDecodeError:
                    if packet.calc_checksum(packet) == checksum:
                        packets_list[seq_num] = packet
                        rudp_socket.sendto(('ACK_' + str(seq_num)).encode(), server_addr)
                        index += 1
                    else:
                        rudp_socket.sendto(('NACK_' + str(seq_num)).encode(), server_addr)
    rudp_socket.sendto('ACKALL'.encode(), server_addr)
    time.sleep(0.15)
    open_file_to_write(file_name, packets_list)




def rudp_download(file_name):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((RUDP_HOST, RUDP_PORT))

    ftp_socket.send("rudp socket is up!".encode())
    file = open_file_to_write(file_name)
    pak, addr = sock.recvfrom(1024)

    expected_seq_num = 0
    while True:
        # get the next packet from sender
        pak, addr = sock.recvfrom(1024)

        if not pak:
            break

        seq_num, data = packet.extract(pak)
        print('got packet num ', seq_num)

        # send ACK to server
        if seq_num == expected_seq_num:
            print('got expected packet, sending ACK ', expected_seq_num)
            pak = packet.make(expected_seq_num)
            sock.sendto(pak, addr)
            expected_seq_num += 1
            file.write(data)
        else:
            print('sending ACK', expected_seq_num - 1)
            pak = packet.make(expected_seq_num - 1)
            sock.sendto(pak, addr)
    file.close()
    sock.close()



    ###########
    # while True:
    #     file = open(file_name, 'wb')
    #     timeout = 10
    #     ctr = 0
    #     while True:
    #         ready = select.select([sock], [], [], timeout)
    #         if ready[0]:
    #             pak, addr = sock.recvfrom(1024)
    #             file.write(pak)
    #             # sock.sendto("ack".encode(), (RUDP_IP, RUDP_PORT))
    #         else:
    #             print(f"{file_name} received successfully!")
    #             file.close()
    #             data_recv = True
    #             break
    #
    #     if data_recv:
    #         break
    #
    # file.close()
    # sock.close()


def ask_server():
    # Send FTP commands to server
    while True:
        command = input("> ")
        if command == "a":
            ftp_socket.send("GET filee.txt".encode())
            rudp_download('filee.txt')
            # foo()
        else:
            ftp_socket.send(command.encode())

            if command == "QUIT":
                # Exit loop and close FTP connection
                ftp_socket.close()
                break

            elif command.startswith("GET"):
                if command.split()[1] == "--tcp":
                    filename = command.split()[2]
                    UDP_thread(filename)
                else:
                    filename = command.split()[1]
                    # rudp_download(filename)
                    # rudp_download_file(rudp_socket, server_addr, packets_list, file_name)
                    UDP_thread(filename)

            elif command == "LIST":
                # Receive a list of files in the current directory from server
                data = ftp_socket.recv(BUFFER_SIZE)
                print(data.decode())

            elif command.startswith("UPLOAD"):
                filename = command.split()[1]
                tcp_upload(filename)

            else:
                print("unknown command.")
                # Receive FTP command response from server
                data = ftp_socket.recv(BUFFER_SIZE)
                # print(data.decode())


def connect_to_server():
    # Print the welcome message
    data = ftp_socket.recv(BUFFER_SIZE)
    print(data.decode())
    ask_server()


if __name__ == '__main__':

    ftp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # Create an FTP socket
    ftp_socket.connect(('127.0.0.1', FTP_PORT))  # Connect to the FTP server

    connect_to_server()

    # Close the FTP connection
    ftp_socket.close()
