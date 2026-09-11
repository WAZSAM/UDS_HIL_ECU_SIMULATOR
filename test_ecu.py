import can

def test_session_contorl_valid():
    bus = can.interface.Bus(channel='vcan0', interface='socketcan')
    request = can.Message(arbitration_id=0x123, data=[0x02, 0x10, 0x03, 0x00, 0x00, 0x00, 0x00, 0x00], is_extended_id=False)
    bus.send(request)
    response = bus.recv()
    print(response)
    assert list(response.data) == [0x06, 0x50, 0x03, 0x00, 0x32, 0x01, 0xF4]

def test_read_dtc_information():
    bus = can.interface.Bus(channel='vcan0', interface='socketcan')
    request = can.Message(arbitration_id=0x199, data=[0x02, 0x19, 0x02, 0x00, 0x00, 0x00, 0x00, 0x00], is_extended_id=False)
    bus.send(request)
    response = bus.recv()
    print(response)
    assert list(response.data) == [0x06, 0x59, 0x02, 0x01, 0x02, 0x03, 0x08]

def test_read_data_by_identifier():
    bus = can.interface.Bus(channel='vcan0', interface='socketcan')
    request = can.Message(arbitration_id=0x456, data=[0x03, 0x22, 0xF1, 0x90, 0x00, 0x00, 0x00, 0x00], is_extended_id=False)
    bus.send(request)
    response = bus.recv()
    print(response)
    assert list(response.data) == [0x07, 0x62, 0xF1, 0x90, 0x57, 0x41, 0x31, 0x32]

def test_security_access():
    bus = can.interface.Bus(channel='vcan0', interface='socketcan')
    request = can.Message(arbitration_id=0x789, data=[0x02, 0x27, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00], is_extended_id=False)
    bus.send(request)
    response = bus.recv()
    print(response)    
    assert list(response.data) == [0x04, 0x67, 0x01, 0x12, 0x34, 0x00, 0x00]

def test_section_control_invalid_function():
    bus = can.interface.Bus(channel='vcan0', interface='socketcan')
    request =can.Message(arbitration_id=0x123, data=[0x02, 0x10, 0x99, 0x00, 0x00, 0x00, 0x00, 0x00], is_extended_id=False)
    bus.send(request)
    response = bus.recv()
    print(response)
    assert list(response.data) == [0x03, 0x7F, 0x10, 0x12, 0x00, 0x00, 0x00]

def test_read_dtc_information_invalid_function():
    bus = can.interface.Bus(channel='vcan0', interface='socketcan')
    request = can.Message(arbitration_id=0x199, data=[0x02, 0x19, 0x99, 0x00, 0x00, 0x00, 0x00, 0x00], is_extended_id=False)
    bus.send(request)
    response = bus.recv()
    print(response)
    assert list(response.data) == [0x03, 0x7F, 0x19, 0x12, 0x00, 0x00, 0x00]

def test_security_access_invalid_function():
    bus = can.interface.Bus(channel='vcan0', interface='socketcan')
    request = can.Message(arbitration_id=0x789, data=[0x02, 0x27, 0x99, 0x00, 0x00, 0x00, 0x00, 0x00], is_extended_id=False)
    bus.send(request)
    response = bus.recv()
    print(response)
    assert list(response.data) == [0x03, 0x7F, 0x27, 0x12, 0x00, 0x00, 0x00]