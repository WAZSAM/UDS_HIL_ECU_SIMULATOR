import can

bus = can.interface.Bus(channel='vcan0', interface='socketcan')

# Ask the ECU for seed
request = can.Message(arbitration_id=0x123, data = [0x02, 0x27, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00], is_extended_id=False)
bus.send(request)
response = bus.recv(timeout=1)  # Wait for a response for 1 second

# Pull the two seed bytes from ECU
seed = response.data[3]
seed2 = response.data[4]
print("Seed received from ECU: ", seed, seed2)

# Compute the key based on the seed (this is a placeholder for the actual algorithm)
key1 = seed ^ 0xA5
key2 = seed2 ^ 0x5A
print("Computed key to send to ECU: ", key1, key2)

# Send the key back to the ECU
request = can.Message(arbitration_id=0x123, data = [0x02, 0x27, 0x02, key1, key2, 0x00, 0x00, 0x00], is_extended_id=False)
bus.send(request)
response = bus.recv(timeout=1)  # Wait for a response for 1 second
print("Response from ECU after sending key: ", list(response.data))

bus.shutdown()
