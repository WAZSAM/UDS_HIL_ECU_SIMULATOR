import can
import random
import time

bus = can.interface.Bus(channel='vcan0', interface='socketcan')

for i in range(25):

    request = can.Message(arbitration_id=0x123, data=[0x02, 0x10, random.randint(0, 255), 0x00, 0x00, 0x00, 0x00, 0x00], is_extended_id=False)
    print("Sent sub-function:", hex(request.data[2]))
    bus.send(request)
    response = bus.recv(timeout=1)

    if response is None:
        print("No response received within the timeout period.")
    else:
        print("Response received:", list(response.data))

    #time.sleep(1)  # Wait for 1 second before sending the next request

bus.shutdown()