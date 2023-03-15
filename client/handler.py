from constants import *


def send_requests(client):
    # Send FTP commands to server
    while True:
        command = input("> ")
        client.ftp_socket.send(command.encode())

        if command == "QUIT":
            client.ftp_socket.close()
            break

        elif command.startswith("GET"):
            if command.split()[1] == "--tcp":
                filename = command.split()[2]
                print(f"Download {filename} with TCP...")
                client.tcp_download(filename)
            else:
                filename = command.split()[1]
                print(f"Download {filename} with RUDP...")
                client.start_rudp_connection()
                client.rudp_download(filename)

        elif command == "LIST":
            data = client.ftp_socket.recv(BUFFER_SIZE)
            print(data.decode())

        elif command.startswith("UPLOAD"):
            filename = command.split()[1]
            client.tcp_upload(filename)

        else:
            print("unknown command.")
            # Receive FTP command response from server
            data = client.ftp_socket.recv(BUFFER_SIZE)
            # print(data.decode())