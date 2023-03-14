# # packet.py - Packet-related functions

# # Creates a packet from a sequence number and byte data
# def make(seq_num, data = b''):
#     seq_bytes = seq_num.to_bytes(4, byteorder = 'little', signed = True)
#     return seq_bytes + data

# # Creates an empty packet
# def make_empty():
#     return b''

# # Extracts sequence number and data from a non-empty packet
# def extract(packet):
#     # seq_num, payload = packet.decode().split(':', 1)[0]
#     seq_num = int.from_bytes(packet[0:4], byteorder = 'little', signed = True)
#     return seq_num


# packet.py - Packet-related functions
#
# # Creates a packet from a sequence number and byte data
# def make(seq_num, data = b''):
#     seq_bytes = seq_num.to_bytes(4, byteorder = 'little', signed = True)
#     return seq_bytes + data
#
# # Creates an empty packet
# def make_empty():
#     return b''
#
# # Extracts sequence number and data from a non-empty packet
# def extract(packet):
#     seq_num = int.from_bytes(packet[0:4], byteorder = 'little', signed = True)
#     return seq_num, packet[4:]
# packet.py - Packet-related functions
import struct
import array


# Creates a packet from a sequence number and byte data
def make(seq_num, checksum, packetdata, cwnd):
    return struct.pack('!LHI', seq_num % ((1 << 16) - 1), int(checksum), int(cwnd)) + packetdata
    # seq_bytes = seq_num.to_bytes(4, byteorder = 'little', signed = True)
    # return seq_bytes + data


# Creates an empty packet
def make_empty():
    return b''


# Extracts sequence number and data from a non-empty packet
def extract(packet):
    return struct.unpack('!LHI', packet[:10]), packet[10:]
    # seq_num, payload = packet.decode().split(':', 1)[0]
    # seq_num = int.from_bytes(packet[0:4], byteorder = 'little', signed = True)
    # return seq_num


def chksum(packet: bytes):
    max_bit = 1 << 16
    numbers = []
    if len(packet) % 2 != 0:
        packet += bytes(1)

    res = sum(array.array("H", packet))
    res = (res >> 16) + (res & 0xffff)
    res += res >> 16

    return (~res) & 0xffff


def calc_checksum(packet):
    max_bit = 1 << 16  # 32,768
    numbers = []

    if len(packet) % 2 == 1:
        packet += bytes(1)  # adding padding of one byte in the case our packet is not of even length

    for i in range(0, len(packet), 2):
        number = packet[i] << 8  # shifts 8 bits to the left,
        number += packet[i + 1]  # making room for this number.
        numbers.append(number)

    _sum = 0
    for number in numbers:
        _sum += number
        sum1 = _sum % max_bit  # calculating carry
        sum2 = _sum // max_bit  # calculating with floor division
        _sum = sum1 + sum2

    checksum = max_bit - 1 - _sum  # checksum using one's complement.
    return checksum
