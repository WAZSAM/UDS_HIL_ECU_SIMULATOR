import can
import pytest
import random

# Provide each test with a CAN bus connection and reset the ECU to a locked state.
@pytest.fixture
def bus():
    b = can.interface.Bus(channel='vcan0', interface='socketcan')
    reset = can.Message(arbitration_id=0x123, data=[0x02, 0x10, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00], is_extended_id=False)
    b.send(reset)
    b.recv(timeout=1)  # Wait for the ECU to process the reset
    yield b
    b.shutdown()

# Verify that a valid extended-session request receives a positive response.
def test_session_contorl_valid(bus):
    request = can.Message(arbitration_id=0x123, data=[0x02, 0x10, 0x03, 0x00, 0x00, 0x00, 0x00, 0x00], is_extended_id=False)
    bus.send(request)
    response = bus.recv(timeout=1)
    print(response)
    assert response is not None, "No response received within the timeout period."
    assert list(response.data) == [0x06, 0x50, 0x03, 0x00, 0x32, 0x01, 0xF4]

# Verify that the supported DTC query returns the sample trouble-code data.
def test_read_dtc_information(bus):
    request = can.Message(arbitration_id=0x199, data=[0x02, 0x19, 0x02, 0x00, 0x00, 0x00, 0x00, 0x00], is_extended_id=False)
    bus.send(request)
    response = bus.recv(timeout=1)
    print(response)
    assert response is not None, "No response received within the timeout period."
    assert list(response.data) == [0x06, 0x59, 0x02, 0x01, 0x02, 0x03, 0x08]

# Verify that the public VIN DID can be read while the ECU is locked.
def test_read_data_by_identifier(bus):
    request = can.Message(arbitration_id=0x456, data=[0x03, 0x22, 0xF1, 0x90, 0x00, 0x00, 0x00, 0x00], is_extended_id=False)
    bus.send(request)
    response = bus.recv(timeout=1)
    print(response)
    assert response is not None, "No response received within the timeout period."
    assert list(response.data) == [0x07, 0x62, 0xF1, 0x90, 0x57, 0x41, 0x31, 0x32]

# Verify that a seed request receives a positive SecurityAccess response.
def test_security_access(bus):
    request = can.Message(arbitration_id=0x789, data=[0x02, 0x27, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00], is_extended_id=False)
    bus.send(request)
    response = bus.recv(timeout=1)
    seed1 = response.data[3]
    seed2 = response.data[4]
    print(response)
    assert response is not None, "No response received within the timeout period."  
    assert list(response.data) == [0x04, 0x67, 0x01, seed1, seed2, 0x00, 0x00]

# Verify that an unsupported diagnostic-session sub-function is rejected.
def test_section_control_invalid_function(bus):
    request =can.Message(arbitration_id=0x123, data=[0x02, 0x10, 0x99, 0x00, 0x00, 0x00, 0x00, 0x00], is_extended_id=False)
    bus.send(request)
    response = bus.recv(timeout=1)
    print(response)
    assert response is not None, "No response received within the timeout period."
    assert list(response.data) == [0x03, 0x7F, 0x10, 0x12, 0x00, 0x00, 0x00]

# Verify that an unsupported DTC sub-function is rejected.
def test_read_dtc_information_invalid_function(bus):
    request = can.Message(arbitration_id=0x199, data=[0x02, 0x19, 0x99, 0x00, 0x00, 0x00, 0x00, 0x00], is_extended_id=False)
    bus.send(request)
    response = bus.recv(timeout=1)
    print(response)
    assert response is not None, "No response received within the timeout period."
    assert list(response.data) == [0x03, 0x7F, 0x19, 0x12, 0x00, 0x00, 0x00]

# Verify that an unsupported SecurityAccess sub-function is rejected.
def test_security_access_invalid_function(bus):
    request = can.Message(arbitration_id=0x789, data=[0x02, 0x27, 0x99, 0x00, 0x00, 0x00, 0x00, 0x00], is_extended_id=False)
    bus.send(request)
    response = bus.recv(timeout=1)
    print(response)
    assert response is not None, "No response received within the timeout period."
    assert list(response.data) == [0x03, 0x7F, 0x27, 0x12, 0x00, 0x00, 0x00]

# Verify that the protected hardware DID is denied before unlocking.
def test_read_protected_did_while_locked(bus):
    request = can.Message(arbitration_id=0x456, data=[0x03, 0x22, 0xF1, 0x91, 0x00, 0x00, 0x00, 0x00], is_extended_id=False)
    bus.send(request)
    response = bus.recv(timeout=1)
    print(response)
    assert response is not None, "No response received within the timeout period."
    assert list(response.data) == [0x03, 0x7F, 0x22, 0x33, 0x00, 0x00, 0x00]

# Exercise the full seed/key exchange, then read the protected hardware DID.
def test_unlock_then_read_protected_did(bus):
    # Step 1: Send security access request to unlock
    request = can.Message(arbitration_id=0x789, data=[0x02, 0x27, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00], is_extended_id=False)
    bus.send(request)
    response = bus.recv(timeout=1)
    seed1 = response.data[3]
    seed2 = response.data[4]
    print(response)
    assert response is not None, "No response received within the timeout period."
    assert list(response.data) == [0x04, 0x67, 0x01, seed1, seed2, 0x00, 0x00]

    # Step 2: Send security access request with correct key to unlock
    correct_key = (seed1) ^ 0xA5  # This is just a placeholder for the correct key calculation
    correct_key2 = (seed2) ^ 0xA5  # This is just a placeholder for the correct key calculation
    request = can.Message(arbitration_id=0x789, data=[0x03, 0x27, 0x02, correct_key, correct_key2, 0x00, 0x00, 0x00], is_extended_id=False)
    bus.send(request)
    response = bus.recv(timeout=1)
    print(response)
    assert response is not None, "No response received within the timeout period."
    assert list(response.data) == [0x02, 0x67, 0x02, 0x00, 0x00, 0x00, 0x00]

    # Step 3: Now read the protected DID
    request = can.Message(arbitration_id=0x456, data=[0x03, 0x22, 0xF1, 0x91, 0x00, 0x00, 0x00, 0x00], is_extended_id=False)
    bus.send(request)
    response = bus.recv(timeout=1)
    print(response)
    assert response is not None, "No response received within the timeout period."
    assert list(response.data) == [0x05, 0x62, 0xF1, 0x91, 0x56, 0x31, 0x00, 0x00]

# Verify that an unrecognized DID returns requestOutOfRange.
def test_read_unkown_did(bus):
    request = can.Message(arbitration_id=0x456, data=[0x03, 0x22, 0xF1, 0x99, 0x00, 0x00, 0x00, 0x00], is_extended_id=False)
    bus.send(request)
    response = bus.recv(timeout=1)
    print(response)
    assert response is not None, "No response received within the timeout period."
    assert list(response.data) == [0x03, 0x7F, 0x22, 0x31, 0x00, 0x00, 0x00]

# Verify that submitting a key before requesting a seed is rejected.
def test_key_without_seed(bus):
    # Step 1: Send security access request without requesting seed
    request = can.Message(arbitration_id=0x789, data=[0x03, 0x27, 0x02, 0xB7, 0x91, 0x00, 0x00], is_extended_id=False)
    bus.send(request)
    response = bus.recv(timeout=1)
    print(response)
    assert response is not None, "No response received within the timeout period."
    assert list(response.data) == [0x03, 0x7F, 0x27, 0x24, 0x00, 0x00, 0x00] 

# Verify that a key that does not match the issued seed is rejected.
def test_wrong_key(bus):
    # Step 1: Send security access request to unlock
    request = can.Message(arbitration_id=0x789, data=[0x02, 0x27, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00], is_extended_id=False)
    bus.send(request)
    response = bus.recv(timeout=1)
    seed1 = response.data[3]
    seed2 = response.data[4]
    print(response)
    assert response is not None, "No response received within the timeout period."
    assert list(response.data) == [0x04, 0x67, 0x01, seed1, seed2, 0x00, 0x00]

    # Step 2: Send security access request with wrong key
    correct_key = (seed1) ^ 0xA5  # This is just a placeholder for the correct key calculation
    correct_key2 = (seed2) ^ 0x5A  # This is just a placeholder for the correct key calculation
    wrong_key = (correct_key) ^ 0x01  # This is just a placeholder for the wrong key calculation
    wrong_key2 = (correct_key2) ^ 0x01  # This is just a placeholder for the wrong key calculation
    request = can.Message(arbitration_id=0x789, data=[0x04, 0x27, 0x02, wrong_key, wrong_key2, 0x00, 0x00, 0x00], is_extended_id=False)
    bus.send(request)
    response = bus.recv(timeout=1)
    print(response)
    assert response is not None, "No response received within the timeout period."
    assert list(response.data) == [0x03, 0x7F, 0x27, 0x35, 0x00, 0x00, 0x00]
