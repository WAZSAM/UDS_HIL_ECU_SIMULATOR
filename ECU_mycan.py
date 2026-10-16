import can

bus = can.interface.Bus(channel='vcan0', interface='socketcan')
ECU_is_locked = True
seed_sent = False

while True:
    message = bus.recv()
    print(message)

    if message.data[1] == 0x10:
        ECU_is_locked = True
        Seed_sent = False
        if message.data[2] == 0x01 or message.data[2] == 0x03:
            response = can.Message(arbitration_id=0x321, data=[0x06, 0x50, message.data[2], 0x00, 0x32, 0x01, 0xF4], is_extended_id=False)
            bus.send(response)
        else:
            response = can.Message(arbitration_id=0x321, data=[0x03, 0x7F, message.data[1], 0x12, 0x00, 0x00, 0x00], is_extended_id=False)
            bus.send(response)

    elif message.data[1] == 0x19:

        if message.data[2] == 0x02:
            response = can.Message(arbitration_id=0x321, data=[0x06, 0x59, 0x02, 0x01, 0x02, 0x03, 0x08], is_extended_id=False)
            bus.send(response)
        else:
            response = can.Message(arbitration_id=0x321, data=[0x03, 0x7F, message.data[1], 0x12, 0x00, 0x00, 0x00], is_extended_id=False)
            bus.send(response)

    elif message.data[1] == 0x22:
        vin_byts = list("WA12".encode())
        if message.data[2] == 0xF1 and message.data[3] == 0x90:
            response = can.Message(arbitration_id=0x321, data=[0x07, 0x62, 0xF1, 0x90] + vin_byts, is_extended_id=False)
            bus.send(response)
        elif message.data[2] == 0xF1 and message.data[3] == 0x91:
            if ECU_is_locked:
                response = can.Message(arbitration_id=0x321, data=[0x03, 0x7F, message.data[1], 0x33, 0x00, 0x00, 0x00], is_extended_id=False)
                bus.send(response)
            else:
                response = can.Message(arbitration_id=0x321, data=[0x05, 0x62, 0xF1, 0x91, 0x56, 0x31, 0x00, 0x00], is_extended_id=False)
                bus.send(response)
        else:
            response = can.Message(arbitration_id=0x321, data=[0x03, 0x7F, message.data[1], 0x31, 0x00, 0x00, 0x00], is_extended_id=False)
            bus.send(response)

    elif message.data[1] == 0x27:
        if message.data[2] == 0x01:
            seed_sent = True
            response = can.Message(arbitration_id=0x321, data=[0x04, 0x67, 0x01, 0x12, 0x34, 0x00, 0x00], is_extended_id=False)
            bus.send(response)
        elif message.data[2] == 0x02:
            if not seed_sent:
                response = can.Message(arbitration_id=0x321, data=[0x03, 0x7F, message.data[1], 0x24, 0x00, 0x00, 0x00], is_extended_id=False)
                bus.send(response)
            else:
                if message.data[3] == 0xB7 and message.data[4] == 0x91:
                    ECU_is_locked = False
                    response = can.Message(arbitration_id=0x321, data=[0x02, 0x67, 0x02, 0x00, 0x00, 0x00, 0x00], is_extended_id=False)
                    bus.send(response)
                else:
                    response = can.Message(arbitration_id=0x321, data=[0x03, 0x7F, message.data[1], 0x35, 0x00, 0x00, 0x00], is_extended_id=False)
                    bus.send(response)
        else:
            response = can.Message(arbitration_id=0x321, data=[0x03, 0x7F, message.data[1], 0x12, 0x00, 0x00, 0x00], is_extended_id=False)
            bus.send(response)

bus.shutdown()