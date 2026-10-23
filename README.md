**UDS HIL ECU Simulator**

A simulated automotive ECU that responds to UDS diagnostic requests over a virtual CAN bus, paired with an automated test suite that verifies the ECU's responses are correct.

I built this to actually understand HIL/SIL testing instead of just reading about it — everything here runs on a virtual CAN interface (`vcan0`), so no real hardware is needed.

**What It Does**

The simulator handles four UDS (ISO 14229) services:

- **DiagnosticSessionControl (0x10)** — switches the ECU between diagnostic sessions (default, extended)
- **ReadDataByIdentifier (0x22)** — returns ECU data for a requested identifier (e.g. VIN)
- **SecurityAccess (0x27)** — full seed/key authentication handshake: seed request, key verification, and the locked/unlocked state that gates a protected DID
- **ReadDTCInformation (0x19)** — returns stored diagnostic trouble codes

If a client requests an unsupported sub-function on 0x10, 0x27, or 0x19, the ECU returns a proper negative response (`7F` + service ID + NRC) instead of failing silently or ignoring the request.

fuzzer.py is a basic fuzzer that sends a configurable number of UDS requests to the simulator, each with a randomized sub-function byte. Since it has no way of knowing the "correct" response for a random value, it doesn't check for correctness — it only checks whether the ECU responds at all within a timeout, to catch cases where malformed input might cause it to hang or crash instead of rejecting the request cleanly.

`test_ecu.py` is a separate pytest-based client that sends requests to the simulator and asserts the responses match what's expected — both the valid requests and the deliberately invalid ones.

## Source code guide

The source files include comments describing their main steps and the meaning
of the UDS/CAN data they handle. These comments explain the existing code; they
do not change how the programs behave.

- `ECU_mycan.py` is the Python ECU simulator used by the tests. It handles
  diagnostic sessions, DTC and DID reads, and the SecurityAccess seed/key flow.
- `ECU.c` is a C version of the ECU that handles SecurityAccess and session
  control requests over `vcan0`.
- `Hello.c` is a small C example that checks a UDS service ID.
- `unlock_test.c` is a C CAN client that requests a seed, calculates a key,
  submits it, and prints the ECU's response.
- `test_ecu.py` contains pytest checks for the Python simulator.
- `Key_generator.py` demonstrates the simulator's seed/key exchange.
- `attack_capture.py` demonstrates why the simulator's XOR-based key rule is
  insecure by observing a seed/key pair.
- `fuzzer.py` sends a small number of requests with randomized sub-functions
  and prints whether a response arrived.

## Security behaviour

The simulator behaves like a small ECU with a locked/unlocked state:

- The ECU starts locked.
- `27 01` returns a random two-byte seed, generated fresh on every request.
  `27 02` with the correct key unlocks the ECU. The correct key is computed
  per byte: the first byte is `seed1 XOR 0xA5`, the second is `seed2 XOR 0x5A`.
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
including the full flow: request a seed, compute the correct key from it,
unlock, read the protected DID.

Run them with the ECU running in another terminal:

    python3 ECU_mycan.py
    pytest -v

A pytest fixture opens the python-can bus for each test, resets the ECU with a
session control request so every test starts locked, and closes the bus at the
end. Every receive has a 1-second timeout, so if the ECU is not running the
tests fail quickly instead of hanging. Because the seed is random, tests that
need a valid key read the seed out of the ECU's response and compute the key
at test time, rather than hardcoding one.

## Attack demo: recovering the SecurityAccess secret

Two scripts demonstrate why a static XOR-based key algorithm is insecure,
even once the seed itself is randomized:

**`attack_capture.py`** — passively sniffs the CAN bus for one SecurityAccess
seed/key exchange. Because the ECU's key algorithm is a fixed per-byte XOR
(`key = seed XOR secret`), the secret bytes can be recovered from a single
observed pair with `secret = seed XOR key`. This only has to be done once,
ever — the secret never changes, no matter how often the seed does.

**`Key_generator.py`** — uses the recovered secret bytes to unlock the ECU on
demand, with no prior knowledge of any specific key: it requests a fresh
seed, computes the correct key locally from the recovered secret, and sends
it back. It never needs to observe a real client's key again, and it
succeeds against every new random seed.

**Why this matters:** randomizing the seed defeats a simple replay attack
(resending an old captured key), but does nothing against a recovered XOR
secret, because XOR is trivially invertible. A real ECU must not derive its
key with a fixed, reversible function. The actual fix is a keyed
cryptographic primitive (HMAC-SHA256 or AES-CMAC) where recovering the key
from seed/response pairs is computationally infeasible — not just "harder to
guess."

## Known limitations

This is a learning project. What it does not do yet:

- The key algorithm is a fixed per-byte XOR, which (see Attack demo above)
  is recoverable from a single sniffed seed/key pair regardless of how the
  seed is generated.
- The VIN is shortened to 4 characters because multi-frame messages (ISO-TP,
  ISO 15765-2) are not implemented.
- The ECU answers requests on any CAN ID and does not check the length byte.
- There is no limit on wrong key attempts (a real ECU locks out after a few).

**How to Run**

**Prerequisites**
- Linux (or WSL2 on Windows — `wsl --install -d kali-linux`)
- Python 3 with pip

**Setup**

git clone https://github.com/WAZSAM/UDS_HIL_ECU_SIMULATOR.git
cd UDS_HIL_ECU_SIMULATOR
pip install python-can pytest --break-system-packages
./setup_vcan.sh
ip link show vcan0 # confirm it shows UP


**Running It**

You need two terminals.

**Terminal 1 — start the ECU simulator, leave it running:**

python3 ECU_mycan.py


**Terminal 2 — run the test suite:**

pytest test_ecu.py -v


All 12 tests should pass.

**Manual testing (optional)**

With the simulator still running, you can send raw requests by hand and watch the responses with `candump vcan0` in a third terminal:

cansend vcan0 123#0210030000000000 # DiagnosticSessionControl (valid)
cansend vcan0 123#0210990000000000 # DiagnosticSessionControl (invalid sub-function)
cansend vcan0 199#0219020000000000 # ReadDTCInformation (valid)
cansend vcan0 199#0219990000000000 # ReadDTCInformation (invalid sub-function)
cansend vcan0 456#0322F19000000000 # ReadDataByIdentifier
cansend vcan0 789#0227010000000000 # SecurityAccess (valid)
cansend vcan0 789#0227990000000000 # SecurityAccess (invalid sub-function)


Since the seed is random, you can't hand-type a working unlock key in
advance — run `python3 Key_generator.py` instead to see a full automated
unlock.

**What I Learned**

This was my first real Python project, so most of the "learning" was actually debugging. A few bugs stand out:

`python-can` gives you received data as a `bytearray`, not a plain `list`. I wrote an assertion comparing the two directly and it kept failing even though `print()` showed the exact bytes I expected — turns out `bytearray([1,2,3]) == [1,2,3]` is just `False` in Python, different types, doesn't matter that the numbers match. Took a while to catch that one. Fix was wrapping it in `list(...)` before comparing.

Also spent longer than I should have on `if x == 0x01 or 0x03:` silently doing nothing useful. Python reads that as "x == 0x01, or just 0x03 by itself" — and since 0x03 isn't zero, that second half is always true. So the whole check was always true no matter what came in. Had to spell out both sides of the comparison.

`vcan0` also doesn't survive WSL restarting, which I found out the hard way, repeatedly, before I gave up and just wrote `setup_vcan.sh` so I'd stop re-typing the same three commands every session.

Honestly the most common bug wasn't conceptual at all — it was miscounting bytes in a list. Off by one item here or there, length byte not matching what actually followed it. Most of the actual debugging time went into just lining things up correctly, byte for byte.

Randomizing the seed broke every test and script that had a hardcoded key — a useful reminder that a test only proves what it actually asserts. My original tests all checked `response is not None`, which passes on a rejection just as easily as a success, so switching to a random seed didn't fail loudly, it just quietly stopped testing anything meaningful until I rewrote the assertions to check the actual response bytes.

**Next Steps**

- Replace the XOR key algorithm with a keyed cryptographic function (HMAC-SHA256 or AES-CMAC) so the attack demo in this repo no longer works
- Multi-frame (ISO-TP) support so responses aren't capped at 7 bytes — the VIN response right now is a shortened fake VIN for exactly this reason