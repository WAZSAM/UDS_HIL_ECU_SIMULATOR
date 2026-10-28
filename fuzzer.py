import can
import random
import time

# Connect to the virtual CAN interface used by the ECU simulator.
bus = can.interface.Bus(channel='vcan0', interface='socketcan')

# Repeat a small set of requests with randomized sub-function values.
for i in range(5):  # Send 5 random requests

    # Try a random DiagnosticSessionControl sub-function and wait for a reply.
    request = can.Message(arbitration_id=0x123, data=[0x02, 0x10, random.randint(0, 255), 0x00, 0x00, 0x00, 0x00, 0x00], is_extended_id=False)
    print("Sent sub-function:", hex(request.data[2]))
    bus.send(request)
    response = bus.recv(timeout=1)

    if response is None:
        print("No response received within the timeout period.")
    else:
        print("Response received:", list(response.data))

    # Try a random ReadDTCInformation sub-function and display the response.
    request = can.Message(arbitration_id=0x199, data=[0x02, 0x19, random.randint(0, 255), 0x00, 0x00, 0x00, 0x00, 0x00], is_extended_id=False)
    print("Sent sub-function:", hex(request.data[2]))
    bus.send(request)
    response = bus.recv(timeout=1)

    if response is None:
        print("No response received within the timeout period.")
    else:
        print("Response received:", list(response.data))

    # Try a random SecurityAccess sub-function and display the response.
    request = can.Message(arbitration_id=0x789, data=[0x02, 0x27, random.randint(0, 255), 0x00, 0x00, 0x00, 0x00, 0x00], is_extended_id=False)
    print("Sent sub-function:", hex(request.data[2]))
    bus.send(request)
    response = bus.recv(timeout=1)

    if response is None:
        print("No response received within the timeout period.")
    else:
        print("Response received:", list(response.data))

    time.sleep(1)  # Wait for 1 second before sending the next request

# Release the CAN bus connection when all test requests are sent.
bus.shutdown()