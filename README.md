# UDS ECU Simulator

A software-only learning project that simulates selected Unified Diagnostic Services (UDS) over a Linux virtual CAN interface (`vcan0`). It does not connect to vehicle hardware and is not a hardware-in-the-loop system.

The Python and C programs are separate implementations with different behavior. The Python ECU is the implementation exercised by `test_ecu.py`.

## Implemented services

`ECU_mycan.py` supports:

- `0x10` DiagnosticSessionControl: default session (`0x01`) and extended session (`0x03`). A session request locks the ECU and invalidates the remembered seed.
- `0x19` ReadDTCInformation: sub-function `0x02` returns fixed sample data.
- `0x22` ReadDataByIdentifier: DID `F190` returns the abbreviated sample VIN `WA12`; DID `F191` returns sample hardware data only when unlocked.
- `0x27` SecurityAccess: sub-function `0x01` returns a two-byte random seed; sub-function `0x02` accepts a key made by XORing the seed bytes with `0xA5` and `0x5A`, respectively.

Unsupported sub-functions return NRC `0x12`; an unsupported DID returns NRC `0x31`; reading `F191` while locked returns NRC `0x33`. A key request before a seed request returns NRC `0x24`, and an incorrect key returns NRC `0x35`.

## Files

- `ECU_mycan.py` - Python ECU simulator and the implementation covered by the tests.
- `ECU.c` - earlier C implementation; its service behavior differs from the Python implementation. Kept intentionally as the unhardened baseline for the attack/defense comparison below.
- `ECU_Hardened.c` - hardened C variant implementing a real UDS countermeasure (NRC 0x37, requiredTimeDelayNotExpired) against brute-force SecurityAccess attacks: exponential lockout backoff, a collapsing attempt threshold after the first lockout, lockout state that survives DiagnosticSessionControl resets and ECUReset, and a separate inactivity timeout. Verified against `brute_force.c` and against deliberate repeated-failure bypass attempts.
- `test_ecu.py` - 12 pytest tests for the Python ECU.
- `Key_generator.py` - client demonstrating the simulator's seed/key exchange.
- `unlock_test.c` - C client demonstrating the same exchange.
- `attack_capture.py`, `brute_force.c`, and `burte_force.py` - security demonstrations for an isolated simulator. The Python filename is spelled `burte_force.py`.
- `fuzzer.py` - sends a small number of requests with randomized sub-functions; it is not a comprehensive protocol test.
- `Hello.c` - small example that identifies a sample service ID; it does not communicate over CAN.

## Attack and defense demo

This project includes a working SecurityAccess brute-force attack and a hardened countermeasure against it, in raw C using SocketCAN directly (no library wrapper).

**The target:** `ECU.c` implements SecurityAccess (0x27) with a seed/key challenge: the ECU sends two random seed bytes, the tester XORs them against fixed constants to compute the key, and the ECU checks it. No rate limiting - a tester can submit as many wrong keys as it wants.

**The attack:** `brute_force.c` requests one seed, then tries every possible 2-byte key (0x0000-0xFFFF, 65,536 combinations) against it, stopping as soon as the ECU returns a success response. Against `ECU.c`, this cracks the key in well under a second - the 2-byte keyspace is the problem, not any flaw in the XOR logic itself.

**The defense:** `ECU_Hardened.c` adds a real UDS countermeasure - NRC 0x37 (`requiredTimeDelayNotExpired`) - on top of the identical SecurityAccess logic:

- After 3 wrong keys, the ECU locks out SecurityAccess entirely and returns NRC 0x37 to any further attempt.
- The lockout duration doubles every time it's triggered (10s, 20s, 40s, ...), so a brute-force script that keeps retrying pays an exponentially growing cost.
- After the *first* lockout, the allowance drops from 3 wrong keys to just 1 before the next lockout fires - permanently, for the rest of that ECU process's life.
- The lockout state persists across `DiagnosticSessionControl` (0x10) resets and `ECUReset` (0x11) on purpose - only `ECU_is_locked` is cleared by a reset, not the attack-history counters, so an attacker can't just reset the ECU to get a clean slate.
- A separate 15-second inactivity timeout re-locks the ECU if no request arrives in time, independent of the attack-lockout logic.

`brute_force.c` was updated to detect the NRC 0x37 response and exit immediately instead of grinding through the full keyspace - run it against `ECU_Hardened.c` and it gives up after the first lockout instead of ever finding the key.

**Run it yourself:**
```sh
gcc -Wall -Wextra ECU_Hardened.c -o ecu-hardened && ./ecu-hardened &
gcc -Wall -Wextra brute_force.c -o brute_force && ./brute_force
```

## Requirements

- Linux with SocketCAN and the `vcan` kernel module.
- Python 3 and `pip`.
- `python-can` and `pytest` for the Python simulator and tests.
- GCC for the C programs.

Install the Python packages in a virtual environment:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install python-can pytest
```

Create and bring up `vcan0` if it is not already available:

```sh
sudo modprobe vcan
sudo ip link add dev vcan0 type vcan
sudo ip link set up vcan0
ip link show vcan0
```

If `vcan0` already exists, skip the `ip link add` command. The interface may need to be recreated after a restart.

## Run the Python simulator and tests

In one terminal, start the ECU:

```sh
source .venv/bin/activate
python ECU_mycan.py
```

In another terminal, run the tests:

```sh
source .venv/bin/activate
pytest -v test_ecu.py
```

The ECU must be running on `vcan0` while the tests execute. To try the example client, leave the ECU running and use another terminal:

```sh
source .venv/bin/activate
python Key_generator.py
```

## Build and run a C ECU

Compile either C implementation:

```sh
gcc -Wall -Wextra ECU.c -o ecu-c
gcc -Wall -Wextra ECU_Hardened.c -o ecu-hardened
```

Run one ECU at a time:

```sh
./ecu-c
```

Or:

```sh
./ecu-hardened
```

The Python tests target `ECU_mycan.py`; they do not test either C implementation. `unlock_test.c` can be compiled with:

```sh
gcc -Wall -Wextra unlock_test.c -o unlock_test
```

## Limitations and safety

- The seed/key calculation is deliberately weak and is only suitable for a local demonstration. It is not a secure authentication method.
- The Python ECU does not validate incoming payload lengths or filter incoming CAN identifiers. Several clients also assume a response arrives before reading its data.
- VIN, hardware data, and trouble-code responses are sample values. The abbreviated VIN does not implement ISO-TP for longer messages.
- Keep all demonstrations on an isolated virtual CAN interface that you control. Do not connect this project to a vehicle or any CAN network used by real equipment.# UDS ECU Simulator

A software-only learning project that simulates selected Unified Diagnostic Services (UDS) over a Linux virtual CAN interface (`vcan0`). It does not connect to vehicle hardware and is not a hardware-in-the-loop system.

The Python and C programs are separate implementations with different behavior. The Python ECU is the implementation exercised by `test_ecu.py`.

## Implemented services

`ECU_mycan.py` supports:

- `0x10` DiagnosticSessionControl: default session (`0x01`) and extended session (`0x03`). A session request locks the ECU and invalidates the remembered seed.
- `0x19` ReadDTCInformation: sub-function `0x02` returns fixed sample data.
- `0x22` ReadDataByIdentifier: DID `F190` returns the abbreviated sample VIN `WA12`; DID `F191` returns sample hardware data only when unlocked.
- `0x27` SecurityAccess: sub-function `0x01` returns a two-byte random seed; sub-function `0x02` accepts a key made by XORing the seed bytes with `0xA5` and `0x5A`, respectively.

Unsupported sub-functions return NRC `0x12`; an unsupported DID returns NRC `0x31`; reading `F191` while locked returns NRC `0x33`. A key request before a seed request returns NRC `0x24`, and an incorrect key returns NRC `0x35`.

## Files

- `ECU_mycan.py` - Python ECU simulator and the implementation covered by the tests.
- `ECU.c` - earlier C implementation; its service behavior differs from the Python implementation. Kept intentionally as the unhardened baseline for the attack/defense comparison below.
- `ECU_Hardened.c` - hardened C variant implementing a real UDS countermeasure (NRC 0x37, requiredTimeDelayNotExpired) against brute-force SecurityAccess attacks: exponential lockout backoff, a collapsing attempt threshold after the first lockout, lockout state that survives DiagnosticSessionControl resets and ECUReset, and a separate inactivity timeout. Verified against `brute_force.c` and against deliberate repeated-failure bypass attempts.
- `test_ecu.py` - 12 pytest tests for the Python ECU.
- `Key_generator.py` - client demonstrating the simulator's seed/key exchange.
- `unlock_test.c` - C client demonstrating the same exchange.
- `attack_capture.py`, `brute_force.c`, and `burte_force.py` - security demonstrations for an isolated simulator. The Python filename is spelled `burte_force.py`.
- `fuzzer.py` - sends a small number of requests with randomized sub-functions; it is not a comprehensive protocol test.
- `Hello.c` - small example that identifies a sample service ID; it does not communicate over CAN.

## Attack and defense demo

This project includes a working SecurityAccess brute-force attack and a hardened countermeasure against it, in raw C using SocketCAN directly (no library wrapper).

**The target:** `ECU.c` implements SecurityAccess (0x27) with a seed/key challenge: the ECU sends two random seed bytes, the tester XORs them against fixed constants to compute the key, and the ECU checks it. No rate limiting - a tester can submit as many wrong keys as it wants.

**The attack:** `brute_force.c` requests one seed, then tries every possible 2-byte key (0x0000-0xFFFF, 65,536 combinations) against it, stopping as soon as the ECU returns a success response. Against `ECU.c`, this cracks the key in well under a second - the 2-byte keyspace is the problem, not any flaw in the XOR logic itself.

**The defense:** `ECU_Hardened.c` adds a real UDS countermeasure - NRC 0x37 (`requiredTimeDelayNotExpired`) - on top of the identical SecurityAccess logic:

- After 3 wrong keys, the ECU locks out SecurityAccess entirely and returns NRC 0x37 to any further attempt.
- The lockout duration doubles every time it's triggered (10s, 20s, 40s, ...), so a brute-force script that keeps retrying pays an exponentially growing cost.
- After the *first* lockout, the allowance drops from 3 wrong keys to just 1 before the next lockout fires - permanently, for the rest of that ECU process's life.
- The lockout state persists across `DiagnosticSessionControl` (0x10) resets and `ECUReset` (0x11) on purpose - only `ECU_is_locked` is cleared by a reset, not the attack-history counters, so an attacker can't just reset the ECU to get a clean slate.
- A separate 15-second inactivity timeout re-locks the ECU if no request arrives in time, independent of the attack-lockout logic.

`brute_force.c` was updated to detect the NRC 0x37 response and exit immediately instead of grinding through the full keyspace - run it against `ECU_Hardened.c` and it gives up after the first lockout instead of ever finding the key.

**Run it yourself:**
```sh
gcc -Wall -Wextra ECU_Hardened.c -o ecu-hardened && ./ecu-hardened &
gcc -Wall -Wextra brute_force.c -o brute_force && ./brute_force
```

## Requirements

- Linux with SocketCAN and the `vcan` kernel module.
- Python 3 and `pip`.
- `python-can` and `pytest` for the Python simulator and tests.
- GCC for the C programs.

Install the Python packages in a virtual environment:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install python-can pytest
```

Create and bring up `vcan0` if it is not already available:

```sh
sudo modprobe vcan
sudo ip link add dev vcan0 type vcan
sudo ip link set up vcan0
ip link show vcan0
```

If `vcan0` already exists, skip the `ip link add` command. The interface may need to be recreated after a restart.

## Run the Python simulator and tests

In one terminal, start the ECU:

```sh
source .venv/bin/activate
python ECU_mycan.py
```

In another terminal, run the tests:

```sh
source .venv/bin/activate
pytest -v test_ecu.py
```

The ECU must be running on `vcan0` while the tests execute. To try the example client, leave the ECU running and use another terminal:

```sh
source .venv/bin/activate
python Key_generator.py
```

## Build and run a C ECU

Compile either C implementation:

```sh
gcc -Wall -Wextra ECU.c -o ecu-c
gcc -Wall -Wextra ECU_Hardened.c -o ecu-hardened
```

Run one ECU at a time:

```sh
./ecu-c
```

Or:

```sh
./ecu-hardened
```

The Python tests target `ECU_mycan.py`; they do not test either C implementation. `unlock_test.c` can be compiled with:

```sh
gcc -Wall -Wextra unlock_test.c -o unlock_test
```

## Limitations and safety

- The seed/key calculation is deliberately weak and is only suitable for a local demonstration. It is not a secure authentication method.
- The Python ECU does not validate incoming payload lengths or filter incoming CAN identifiers. Several clients also assume a response arrives before reading its data.
- VIN, hardware data, and trouble-code responses are sample values. The abbreviated VIN does not implement ISO-TP for longer messages.
- Keep all demonstrations on an isolated virtual CAN interface that you control. Do not connect this project to a vehicle or any CAN network used by real equipment.