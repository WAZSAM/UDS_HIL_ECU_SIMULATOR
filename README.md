**UDS HIL ECU Simulator**

A simulated automotive ECU that responds to UDS diagnostic requests over a virtual CAN bus, paired with an automated test suite that verifies the ECU's responses are correct.

I built this to actually understand HIL/SIL testing instead of just reading about it — everything here runs on a virtual CAN interface (`vcan0`), so no real hardware is needed.

**What It Does**

The simulator handles four UDS (ISO 14229) services:

- **DiagnosticSessionControl (0x10)** — switches the ECU between diagnostic sessions (default, extended)
- **ReadDataByIdentifier (0x22)** — returns ECU data for a requested identifier (e.g. VIN)
- **SecurityAccess (0x27)** — implements the seed request half of the seed/key authentication handshake
- **ReadDTCInformation (0x19)** — returns stored diagnostic trouble codes

If a client requests an unsupported sub-function on 0x10, 0x27, or 0x19, the ECU returns a proper negative response (`7F` + service ID + NRC) instead of failing silently or ignoring the request.

fuzzer.py is a basic fuzzer that sends a configurable number of UDS requests to the simulator, each with a randomized sub-function byte. Since it has no way of knowing the "correct" response for a random value, it doesn't check for correctness — it only checks whether the ECU responds at all within a timeout, to catch cases where malformed input might cause it to hang or crash instead of rejecting the request cleanly.

`test_ecu.py` is a separate pytest-based client that sends requests to the simulator and asserts the responses match what's expected — both the valid requests and the deliberately invalid ones.

## Security behaviour

The simulator behaves like a small ECU with a locked/unlocked state:

- The ECU starts locked.
- `27 01` returns a seed. `27 02` with the correct key unlocks the ECU.
- A key sent before any seed was requested is rejected with NRC `0x24`
  (requestSequenceError). A wrong key is rejected with NRC `0x35` (invalidKey).
- DID `F190` (VIN) is public and can be read at any time.
- DID `F191` (hardware version) is protected. While the ECU is locked it
  returns NRC `0x33` (securityAccessDenied). After a successful unlock it
  returns the data.
- An unknown DID returns NRC `0x31` (requestOutOfRange).
- A diagnostic session change (`10 01` / `10 03`) re-locks the ECU and clears
  the seed, similar to how a real ECU drops security access on a session change.

## Tests

12 pytest tests cover the services, the error responses and the lock logic,
including the full flow: seed, key, unlock, read the protected DID.

Run them with the ECU running in another terminal:

    python3 ECU_mycan.py
    pytest -v

A pytest fixture opens the python-can bus for each test, resets the ECU with a
session control request so every test starts locked, and closes the bus at the
end. Every receive has a 1-second timeout, so if the ECU is not running the
tests fail quickly instead of hanging.

## Known limitations

This is a learning project. What it does not do yet:

- The seed is always `12 34` and the key is the seed XOR `0xA5`. Anyone who
  captures one seed/key pair can recover the secret. A real ECU uses a random
  seed and a keyed cryptographic function.
- The VIN is shortened to 4 characters because multi-frame messages (ISO-TP,
  ISO 15765-2) are not implemented.
- The ECU answers requests on any CAN ID and does not check the length byte.
- There is no limit on wrong key attempts (a real ECU locks out after a few).

**How to Run**

**Prerequisites**
- Linux (or WSL2 on Windows — `wsl --install -d kali-linux`)
- Python 3 with pip

**Setup**

```
git clone https://github.com/WAZSAM/UDS_HIL_ECU_SIMULATOR.git
cd UDS_HIL_ECU_SIMULATOR
pip install python-can pytest --break-system-packages
./setup_vcan.sh
ip link show vcan0   # confirm it shows UP
```

**Running It**

You need two terminals.

**Terminal 1 — start the ECU simulator, leave it running:**
```
python3 ECU_mycan.py
```

**Terminal 2 — run the test suite:**
```
pytest test_ecu.py -v
```

Seven tests should pass: four checking correct responses, three checking that invalid sub-functions get rejected properly.

**Manual testing (optional)**

With the simulator still running, you can send raw requests by hand and watch the responses with `candump vcan0` in a third terminal:

```
cansend vcan0 123#0210030000000000   # DiagnosticSessionControl (valid)
cansend vcan0 123#0210990000000000   # DiagnosticSessionControl (invalid sub-function)
cansend vcan0 199#0219020000000000   # ReadDTCInformation (valid)
cansend vcan0 199#0219990000000000   # ReadDTCInformation (invalid sub-function)
cansend vcan0 456#0322F19000000000   # ReadDataByIdentifier
cansend vcan0 789#0227010000000000   # SecurityAccess (valid)
cansend vcan0 789#0227990000000000   # SecurityAccess (invalid sub-function)
```

**What I Learned**

This was my first real Python project, so most of the "learning" was actually debugging. A few bugs stand out:

`python-can` gives you received data as a `bytearray`, not a plain `list`. I wrote an assertion comparing the two directly and it kept failing even though `print()` showed the exact bytes I expected — turns out `bytearray([1,2,3]) == [1,2,3]` is just `False` in Python, different types, doesn't matter that the numbers match. Took a while to catch that one. Fix was wrapping it in `list(...)` before comparing.

Also spent longer than I should have on `if x == 0x01 or 0x03:` silently doing nothing useful. Python reads that as "x == 0x01, or just 0x03 by itself" — and since 0x03 isn't zero, that second half is always true. So the whole check was always true no matter what came in. Had to spell out both sides of the comparison.

`vcan0` also doesn't survive WSL restarting, which I found out the hard way, repeatedly, before I gave up and just wrote `setup_vcan.sh` so I'd stop re-typing the same three commands every session.

Honestly the most common bug wasn't conceptual at all — it was miscounting bytes in a list. Off by one item here or there, length byte not matching what actually followed it. Most of the actual debugging time went into just lining things up correctly, byte for byte.

**Next Steps**

- Add the key-verification half of SecurityAccess (currently only the seed request is implemented)
- Multi-frame (ISO-TP) support so responses aren't capped at 7 bytes — the VIN response right now is a shortened fake VIN for exactly this reason
