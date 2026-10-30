d## UDS ECU Simulator

This project is a small learning example of an Electronic Control Unit (ECU) that responds to Unified Diagnostic Services (UDS) messages over a virtual CAN bus named `vcan0`. It runs without a vehicle or CAN hardware.

Despite the project name, this is a software-only simulator. It is not a hardware-in-the-loop test setup.

There are two ECU programs, but they do not behave the same way. The Python program, `ECU_mycan.py`, is the one covered by `test_ecu.py`. The C program, `ECU.c`, is an earlier, partial version with fewer checks and different responses.

## Python simulator

The Python ECU handles these UDS services:

- `0x10` DiagnosticSessionControl: accepts default session `0x01` and extended session `0x03`. A session request locks the ECU and clears its seed state.
- `0x19` ReadDTCInformation: sub-function `0x02` returns fixed sample data; other sub-functions receive a negative response.
- `0x22` ReadDataByIdentifier: DID `F190` returns the short sample VIN `WA12`. DID `F191` returns `V1` only after a successful unlock.
- `0x27` SecurityAccess: sub-function `0x01` returns a random two-byte seed. For this demonstration, the matching key is calculated by XORing the first seed byte with `0xA5` and the second with `0x5A`. A key before a seed request receives NRC `0x24`; a wrong key receives NRC `0x35`.

Unsupported sub-functions for `0x10`, `0x19`, and `0x27` receive NRC `0x12`. An unknown DID receives NRC `0x31`, and reading `F191` while locked receives NRC `0x33`. A negative response begins with `0x7F`, followed by the requested service and the NRC.

The seed/key rule is intentionally weak and is only suitable for a local demonstration. Do not connect these examples to a vehicle or a real ECU.

## Files

- `ECU_mycan.py`: Python ECU simulator used by the tests.
- `ECU.c`: partial C ECU simulator. Its behavior differs from the Python version; see [Known issues](#known-issues).
- `test_ecu.py`: 12 pytest tests for the Python simulator.
- `unlock_test.c`: C program that requests a seed and submits the matching key.
- `Key_generator.py`: Python client that performs the same example exchange.
- `attack_capture.py`: listens for a SecurityAccess exchange to demonstrate the weakness of the fixed XOR rule. Use only on the isolated virtual bus.
- `brute_force.c` and `burte_force.py`: key-guessing demonstrations. The Python filename is spelled `burte_force.py` in this repository. Run these only against the local simulator on `vcan0`.
- `fuzzer.py`: sends five rounds of requests with random sub-functions and prints responses. It does not check whether the responses are correct.
- `Hello.c`: small C example that checks a sample UDS service ID; it does not communicate over CAN.

## Requirements

- Linux with SocketCAN and the `vcan` kernel module. WSL may work if its Linux kernel provides these features.
- Python 3, `pip`, and `iproute2`.
- The Python packages `python-can` and `pytest`.

## Setup

Create a virtual environment and install the Python packages:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install python-can pytest
```

Create and enable the virtual CAN interface. These commands may ask for your system password. If `vcan0` already exists, skip the `ip link add` command.

```sh
sudo modprobe vcan
sudo ip link add dev vcan0 type vcan
sudo ip link set up vcan0
ip link show vcan0
```

There is no `setup_vcan.sh` file in this repository; the commands above set up the interface directly. The interface may need to be created again after a restart.

## Run the tests

Open two terminals in the project directory. Activate the virtual environment in both.

In the first terminal, start the Python ECU and leave it running:

```sh
python ECU_mycan.py
```

In the second terminal, run the tests:

```sh
pytest -v test_ecu.py
```

The tests send requests over `vcan0` and check response bytes. They cover supported and unsupported requests, locked access, and the seed/key exchange. The ECU must be running for them to pass.

## Run a client

With `ECU_mycan.py` still running, run one client from another terminal:

```sh
python Key_generator.py
```

The other client scripts also use `vcan0`. `attack_capture.py` waits for traffic to observe, so it needs an exchange to occur while it is listening. Keep all demonstrations on the local virtual bus.

To compile the C ECU and client, use a C compiler such as GCC:

```sh
gcc -Wall -Wextra ECU.c -o ecu-c
gcc -Wall -Wextra unlock_test.c -o unlock_test
```

Start `./ecu-c` instead of `ECU_mycan.py` to try the C ECU. The Python tests are not tests for the C program.

## Mistakes and known issues

Some issues found while building the project have been corrected in the Python code and tests:

- Received CAN data is a `bytearray`, not a list. The tests convert it with `list(response.data)` before comparing bytes.
- A check such as `value == 0x01 or 0x03` is always true because `0x03` is tested by itself. The session check now compares the value with both supported options.
- Tests need to check the actual response bytes. Checking only that a response exists does not show whether the request succeeded or was rejected.

There are still problems to address:

- `fuzzer.py` reads fields from the SecurityAccess responses before checking whether a response arrived. It can stop with an exception on a timeout instead of reporting the missing response.
- A few tests also access `response.data` before checking that `response` is not `None`.
- The Python ECU does not validate CAN payload lengths or filter incoming CAN IDs. A short frame can cause an indexing error.
- The Python ECU keeps the seed valid after a key attempt and does not limit wrong keys. This is not a safe design for a real ECU.
- `ECU.c` does not match the Python ECU: its session handler accepts every sub-function as the default session, its DTC handler always sends the same positive response, and unsupported SecurityAccess sub-functions get no response. It also does not check that a seed was requested before accepting a key.
- The C ECU uses `rand()` seeded from the current time. This is not a secure source for keys or security seeds.
- The sample VIN is only four characters. The project does not implement ISO-TP, the transport used to send longer messages over CAN.
- The DTC and DID values are sample data, not readings from a vehicle.

These programs are for learning and local testing only. They are not suitable for protecting or diagnosing a real vehicle.
