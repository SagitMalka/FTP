# RUDP_PORT = 5000
# RUDP_HOST = '127.0.0.1'

FTP_PORT = 21
MTU = 1500

SLEEP = 0.1
TIMEOUT = 10  # sec
WINDOW_SIZE = 1

# TCP configuration
TCP_HOST = '127.0.0.1'
TCP_PORT = 22

FTP_DIRECTORY = 'store/'
BUFFER_SIZE = 1024
users = {"Sagitush": "123456",
         "Lielelel": "password"}


MAX_RETRIES = 5  # Define the maximum number of RUDP transfer retries
RETRY_DELAY = 1  # Define the delay between RUDP transfer retries (in seconds)
resultFLAG = False

last_byte = 0
LOSS_SIMULATE = False

# CONSTANTS
MAX_TRIALS = 5
FILE_NOT_FOUND = "FNF".encode()
PACKET_SIZE = 2048

HEADER_DELIMITER = "|:|:|"
PACKET_DELIMITER1 = b"?:?:?"
PACKET_DELIMITER2 = "?:?:?"

RUDP_HOST = 'localhost'
RUDP_PORT = 4999
RUDP_ADDR = (RUDP_HOST, RUDP_PORT)

CONNECTION_TIMEOUT = 10