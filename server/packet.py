import hashlib

from constants import *


class Packet:
    checksum = 0
    length = 0
    seq = 0
    payload = 0

    def __init__(self, data):
        self.payload = data
        self.length = str(len(data))
        if data != "FNF":
            self.checksum = hashlib.sha1(data).hexdigest()
        else:
            self.checksum = ""

    def encode(self):
        return f"{self.checksum}{HEADER_DELIMITER}{self.seq}{HEADER_DELIMITER}{self.length}{PACKET_DELIMITER2}".encode() + self.payload
