import can
import random

# Connect to the virtual CAN bus used by the ECU simulator.
bus = can.interface.Bus(channel='vcan0', interface='socketcan')

# Keep track of whether security access is unlocked and whether a seed was issued.
ECU_is_locked = True
seed_sent = False

# Receive CAN requests continuously and respond to supported UDS services.
while True:
    message = bus.recv()
    print(message)

    # DiagnosticSessionControl (0x10) resets security access and selects a session.
    if message.data[1] == 0x10:
        ECU_is_locked = True
        seed_sent = False

        # Accept default (0x01) and extended (0x03) diagnostic sessions.
        if message.data[2] == 0x01 or message.data[2] == 0x03:
            response = can.Message(arbitration_id=0x321, data=[0x06, 0x50, message.data[2], 0x00, 0x32, 0x01, 0xF4], is_extended_id=False)
            bus.send(response)
        else:
            # NRC 0x12 means the requested sub-function is unsupported.
            response = can.Message(arbitration_id=0x321, data=[0x03, 0x7F, message.data[1], 0x12, 0x00, 0x00, 0x00], is_extended_id=False)
            bus.send(response)
    
    # ReadDTCInformation (0x19) returns the simulator's sample trouble codes.
    elif message.data[1] == 0x19:

        if message.data[2] == 0x02:
            response = can.Message(arbitration_id=0x321, data=[0x06, 0x59, 0x02, 0x01, 0x02, 0x03, 0x08], is_extended_id=False)
            bus.send(response)
        else:
            # Reject any DTC sub-function not implemented by this simulator.
            response = can.Message(arbitration_id=0x321, data=[0x03, 0x7F, message.data[1], 0x12, 0x00, 0x00, 0x00], is_extended_id=False)
            bus.send(response)
    
    # ReadDataByIdentifier (0x22) provides public VIN and protected hardware data.
    elif message.data[1] == 0x22:
        # The example VIN is abbreviated to fit in a single CAN frame.
        vin_byts = list("WA12".encode())
        if message.data[2] == 0xF1 and message.data[3] == 0x90:
            response = can.Message(arbitration_id=0x321, data=[0x07, 0x62, 0xF1, 0x90] + vin_byts, is_extended_id=False)
            bus.send(response)
        elif message.data[2] == 0xF1 and message.data[3] == 0x91:
            # DID F191 is only available after the ECU has been unlocked.
            if ECU_is_locked:
                response = can.Message(arbitration_id=0x321, data=[0x03, 0x7F, message.data[1], 0x33, 0x00, 0x00, 0x00], is_extended_id=False)
                bus.send(response)
            else:
                response = can.Message(arbitration_id=0x321, data=[0x05, 0x62, 0xF1, 0x91, 0x56, 0x31, 0x00, 0x00], is_extended_id=False)
                bus.send(response)
        else:
            # NRC 0x31 indicates that the requested DID is not supported.
            response = can.Message(arbitration_id=0x321, data=[0x03, 0x7F, message.data[1], 0x31, 0x00, 0x00, 0x00], is_extended_id=False)
            bus.send(response)

    # SecurityAccess (0x27) supports seed requests and key submissions.
    elif message.data[1] == 0x27:
        if message.data[2] == 0x01:
            # Generate and remember a fresh two-byte seed for the next key request.
            seed_sent = True
            stored_seed = random.randint(0, 255)
            stored_seed2 = random.randint(0, 255)
            response = can.Message(arbitration_id=0x321, data=[0x04, 0x67, 0x01, stored_seed, stored_seed2, 0x00, 0x00], is_extended_id=False)
            bus.send(response)
        elif message.data[2] == 0x02:
            # Require a seed request before evaluating a submitted key.
            if not seed_sent:
                response = can.Message(arbitration_id=0x321, data=[0x03, 0x7F, message.data[1], 0x24, 0x00, 0x00, 0x00], is_extended_id=False)
                bus.send(response)
            else:
                # Compare the key against the simulator's per-byte XOR calculation.
                if message.data[3] == stored_seed ^ 0xA5 and message.data[4] == stored_seed2 ^ 0x5A:
                    ECU_is_locked = False
                    response = can.Message(arbitration_id=0x321, data=[0x02, 0x67, 0x02, 0x00, 0x00, 0x00, 0x00], is_extended_id=False)
                    bus.send(response)
                else:
                    response = can.Message(arbitration_id=0x321, data=[0x03, 0x7F, message.data[1], 0x35, 0x00, 0x00, 0x00], is_extended_id=False)
                    bus.send(response)
        else:
            # Reject SecurityAccess sub-functions that are not implemented here.
            response = can.Message(arbitration_id=0x321, data=[0x03, 0x7F, message.data[1], 0x12, 0x00, 0x00, 0x00], is_extended_id=False)
            bus.send(response)

# Close the CAN bus if the receive loop is exited.
bus.shutdown()