import select
import socket
from ftplib import FTP

RUDP_PORT = 5000  # Define the RUDP port number to use
RUDP_IP = '127.0.0.1'  # Define the RUDP HOST number to use
FTP_PORT = 21  # Define the FTP port number to use
BUFFER_SIZE = 1024  # Define the buffer size for data transfer
MAX_RETRIES = 5  # Define the maximum number of RUDP transfer retries
RETRY_DELAY = 1  # Define the delay between RUDP transfer retries (in seconds)


# Define the FTP server settings
TCP_HOST = '0.0.0.0'
TCP_PORT = 22


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
    username = 'Sagitush'  #input("User name: ")
    password = '123456'  #input("Password: ")

    ftp = FTP()
    ftp.connect(TCP_HOST, TCP_PORT)
    ftp.login(username, password)

    return ftp


def rudp_download(file_name):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((RUDP_IP, RUDP_PORT))

    ftp_socket.send("rudp socket is up!".encode())

    data_recv = False

    while True:
        file = open(file_name, 'wb')
        timeout = 10
        ctr = 0
        while True:
            ready = select.select([sock], [], [], timeout)
            if ready[0]:
                pak, addr = sock.recvfrom(1024)
                file.write(pak)
                # sock.sendto("ack".encode(), (RUDP_IP, RUDP_PORT))
            else:
                print(f"{file_name} received successfully!")
                file.close()
                data_recv = True
                break

        if data_recv:
            break

    file.close()
    sock.close()


def ask_server():
    # Send FTP commands to server
    while True:
        command = input("> ")

        ftp_socket.send(command.encode())

        if command == "QUIT":
            # Exit loop and close FTP connection
            ftp_socket.close()
            break

        elif command.startswith("GET"):
            if command.split()[1] == "--tcp":
                filename = command.split()[2]
                tcp_download(filename)
            else:
                filename = command.split()[1]
                rudp_download(filename)

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
            print(data.decode())


def connect_to_server():
    # Print the welcome message
    data = ftp_socket.recv(BUFFER_SIZE)
    print(data.decode())
    ask_server()


if __name__ == '__main__':

    ftp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # Create an FTP socket
    ftp_socket.connect(('localhost', FTP_PORT))  # Connect to the FTP server

    connect_to_server()

    # Close the FTP connection
    ftp_socket.close()

