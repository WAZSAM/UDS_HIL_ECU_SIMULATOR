import can

# Listen to the virtual CAN bus for one SecurityAccess exchange.
bus = can.interface.Bus(channel='vcan0', interface='socketcan')
seed = None
key = None

# Keep listening until both a seed response and a submitted key are observed.
while True:
    msg = bus.recv()

    # Save the two seed bytes from a positive seed response.
    if msg.data[1] == 0x67 and msg.data[2] == 0x01:
        seed = [msg.data[3], msg.data[4]]
        print ("Seed received:", seed)

    # Save the two key bytes from a SecurityAccess key request.
    if msg.data[1] == 0x27 and msg.data[2] == 0x02: 
        key = [msg.data[3], msg.data[4]]
        print ("Key received:", key)

    # In this simulator's XOR scheme, XORing each observed pair reveals its constant.
    if seed is not None and key is not None:
        secret1 = seed[0] ^ key[0]
        secret2 = seed[1] ^ key[1]
        print("secret bytes:", hex(secret1), hex(secret2))
        break
        
# Close the CAN bus after the exchange has been processed.
bus.shutdown()