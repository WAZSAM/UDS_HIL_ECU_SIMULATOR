import can

# Connect to the simulator's virtual CAN bus.
bus = can.interface.Bus(channel='vcan0', interface='socketcan')

# Request a new seed using SecurityAccess service 0x27, sub-function 0x01.
request = can.Message(arbitration_id=0x123, data = [0x02, 0x27, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00], is_extended_id=False)
bus.send(request)
response = bus.recv(timeout=1)  # Wait for a response for 1 second

# Read the two seed bytes from the ECU's positive response.
seed = response.data[3]
seed2 = response.data[4]
print("Seed received from ECU: ", seed, seed2)

# Calculate the example key using the XOR rule implemented by this simulator.
key1 = seed ^ 0xA5
key2 = seed2 ^ 0x5A
print("Computed key to send to ECU: ", key1, key2)

# Submit the calculated key using SecurityAccess sub-function 0x02.
request = can.Message(arbitration_id=0x123, data = [0x02, 0x27, 0x02, key1, key2, 0x00, 0x00, 0x00], is_extended_id=False)
bus.send(request)
response = bus.recv(timeout=1)  # Wait for a response for 1 second
print("Response from ECU after sending key: ", list(response.data))

# Release the CAN bus connection.
bus.shutdown()
