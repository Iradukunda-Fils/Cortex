"""
Generator script for Layer 2 Streaming Test Vector Corpus (14 Draft Vectors)
"""

import hashlib
import json
import os
import struct

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VALID_DIR = os.path.join(BASE_DIR, "valid")
BOUNDARIES_DIR = os.path.join(BASE_DIR, "boundaries")
INVALID_DIR = os.path.join(BASE_DIR, "invalid")

os.makedirs(VALID_DIR, exist_ok=True)
os.makedirs(BOUNDARIES_DIR, exist_ok=True)
os.makedirs(INVALID_DIR, exist_ok=True)

TV_A = b"L4:S6:wf-101S14:payment:chargeS8:caus-999M2:S6:amountI100S8:currencyS3:USD"
TV_B = b"L4:S6:wf-102S10:file:writeS9:caus-1000M1:S4:pathS13:/tmp/data.txt"


def make_frame(frame_type: int, sequence: int, payload: bytes) -> bytes:
    header = b"CF" + bytes([frame_type]) + struct.pack(">II", sequence, len(payload))
    return header + payload


# --- VALID VECTORS ---
# 1. st-01-single-frame.cbeframe
v_st01 = make_frame(0x01, 0, TV_A)
with open(os.path.join(VALID_DIR, "st-01-single-frame.cbeframe"), "wb") as f:
    f.write(v_st01)

# 2. st-02-multi-frame.cbeframe
v_st02 = make_frame(0x01, 0, TV_A) + make_frame(0x01, 1, TV_B) + make_frame(0x04, 2, b"")
with open(os.path.join(VALID_DIR, "st-02-multi-frame.cbeframe"), "wb") as f:
    f.write(v_st02)

# 3. st-03-control-sequence.cbeframe
v_st03 = make_frame(0x01, 0, TV_A) + make_frame(0x02, 1, b"") + make_frame(0x03, 2, b"") + make_frame(0x01, 3, TV_B)
with open(os.path.join(VALID_DIR, "st-03-control-sequence.cbeframe"), "wb") as f:
    f.write(v_st03)

# 4. st-04-clean-end.cbeframe
v_st04 = make_frame(0x01, 0, TV_A) + make_frame(0x04, 1, b"")
with open(os.path.join(VALID_DIR, "st-04-clean-end.cbeframe"), "wb") as f:
    f.write(v_st04)


# --- BOUNDARY VECTORS ---
# 5. st-b01-zero-length-control.cbeframe
v_b01 = make_frame(0x04, 0, b"")
with open(os.path.join(BOUNDARIES_DIR, "st-b01-zero-length-control.cbeframe"), "wb") as f:
    f.write(v_b01)

# 6. st-b02-max-frame-16MiB.cbeframe (Header specifying exactly 16,777,216 bytes)
v_b02_hdr = b"CF\x01\x00\x00\x00\x00\x01\x00\x00\x00"  # 16,777,216 bytes length
with open(os.path.join(BOUNDARIES_DIR, "st-b02-max-frame-16MiB.cbeframe"), "wb") as f:
    f.write(v_b02_hdr + (b"A" * 1024))  # Truncated payload stub for vector metadata

# 7. st-b03-sequence-zero.cbeframe
v_b03 = make_frame(0x01, 0, TV_A)
with open(os.path.join(BOUNDARIES_DIR, "st-b03-sequence-zero.cbeframe"), "wb") as f:
    f.write(v_b03)

# 8. st-b04-sequence-max.cbeframe (UINT32_MAX)
v_b04 = make_frame(0x01, 0xFFFFFFFF, TV_A)
with open(os.path.join(BOUNDARIES_DIR, "st-b04-sequence-max.cbeframe"), "wb") as f:
    f.write(v_b04)


# --- INVALID VECTORS ---
# 9. st-err-01-oversized.cbeframe (Requested length = 17,000,000 > 16MiB)
v_err01 = b"CF\x01\x00\x00\x00\x00\x01\x03\x79\x00"
with open(os.path.join(INVALID_DIR, "st-err-01-oversized.cbeframe"), "wb") as f:
    f.write(v_err01)

# 10. st-err-02-truncated-header.cbeframe (5 bytes total)
v_err02 = b"CF\x01\x00\x00"
with open(os.path.join(INVALID_DIR, "st-err-02-truncated-header.cbeframe"), "wb") as f:
    f.write(v_err02)

# 11. st-err-03-truncated-payload.cbeframe
v_err03 = b"CF\x01\x00\x00\x00\x00\x00\x00\x00\x4a" + TV_A[:20]
with open(os.path.join(INVALID_DIR, "st-err-03-truncated-payload.cbeframe"), "wb") as f:
    f.write(v_err03)

# 12. st-err-04-bad-magic.cbeframe (Magic XY)
v_err04 = b"XY\x01\x00\x00\x00\x00\x00\x00\x00\x0a1234567890"
with open(os.path.join(INVALID_DIR, "st-err-04-bad-magic.cbeframe"), "wb") as f:
    f.write(v_err04)

# 13. st-err-05-sequence-gap.cbeframe (Seq 0 then Seq 2)
v_err05 = make_frame(0x01, 0, TV_A) + make_frame(0x01, 2, TV_B)
with open(os.path.join(INVALID_DIR, "st-err-05-sequence-gap.cbeframe"), "wb") as f:
    f.write(v_err05)

# 14. st-err-06-sequence-overflow.cbeframe (Seq UINT32_MAX followed by another frame)
v_err06 = make_frame(0x01, 0xFFFFFFFF, TV_A) + make_frame(0x01, 0, TV_B)
with open(os.path.join(INVALID_DIR, "st-err-06-sequence-overflow.cbeframe"), "wb") as f:
    f.write(v_err06)


# Manifest calculation
manifest = {}
for root_dir in (VALID_DIR, BOUNDARIES_DIR, INVALID_DIR):
    rel_group = os.path.basename(root_dir)
    for filename in sorted(os.listdir(root_dir)):
        filepath = os.path.join(root_dir, filename)
        with open(filepath, "rb") as f:
            digest = hashlib.sha256(f.read()).hexdigest()
        manifest[f"{rel_group}/{filename}"] = digest

manifest_path = os.path.join(BASE_DIR, "manifest.json")
with open(manifest_path, "w") as f:
    json.dump(manifest, f, indent=2)
    f.write("\n")

print(f"Successfully generated {len(manifest)} vector files and manifest.json.")
