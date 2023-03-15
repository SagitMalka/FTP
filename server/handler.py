import threading

from constants import *


def read_requests(conn, addr, ftp_server):
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
                ftp_server.close_connection(conn, addr)
                return

            elif command == "LIST":
                ftp_server.send_file_list(conn)

            elif command == "GET":
                if args[0] != "--tcp":
                    file_name = args[0]
                    ftp_server.set_file_name(file_name)
                    threading.Thread(target=ftp_server.send_via_rudp).start()

            elif command == 'UPLOAD':
                pass
            else:
                conn.send("ERROR. Command not implemented.\n".encode())
        else:
            print(f"[DISCONNECTED] {addr} disconnected.")
            break

    ftp_server.close_connection(conn, addr)