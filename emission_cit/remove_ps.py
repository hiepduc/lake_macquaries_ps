#!/usr/bin/env python3
"""
Hour-aware CIT point source cleaner

Features:
- Removes Eraring & Vales Point power stations
- Handles EDMS/CIT malformed IDs
- Recognises hour boundary markers (Ehh999999...)
- Preserves full emission structure
"""

import sys

# -----------------------------
# CONFIG
# -----------------------------

REMOVE_SOURCE_IDS = set([
    # Vales Point
    950, 951, 952, 953,

    # Eraring
    954, 955, 956, 957,
    958, 959, 960, 961
])

NSPEC = 17


# -----------------------------
# HELPERS
# -----------------------------

def decode_sid(sid):
    """
    Decode EDMS/CIT ID: EHHXXXYYYSSSSS
    Returns None if invalid
    """
    sid = sid.strip()

    if not sid.startswith("E"):
        return None

    if len(sid) < 10:
        return None

    try:
        return {
            "hour": int(sid[1:3]),
            "x": int(sid[3:6]),
            "y": int(sid[6:9]),
            "src_id": int(sid[9:]) if sid[9:].isdigit() else None
        }
    except:
        return None


def is_hour_end(sid):
    """
    Detect hour termination marker:
    EHH999999...
    """
    sid = sid.strip()
    return sid.startswith("E") and "999999" in sid


def read_emissions(lines, i, nspec):
    """
    Read multi-line emission block safely
    """
    emis = []

    while len(emis) < nspec and i < len(lines):
        try:
            emis.extend([float(x) for x in lines[i].split()])
        except:
            pass
        i += 1

    return emis[:nspec], i


# -----------------------------
# MAIN PROCESS
# -----------------------------

def clean_cit(infile, outfile):
    """
    Hour-aware CIT cleaner
    """

    with open(infile, "r", encoding="latin-1") as f:
        lines = f.readlines()

    out = []

    i = 0
    removed = 0
    kept = 0
    bad = 0
    hours = 0

    while i < len(lines):
        line = lines[i]
        parts = line.split()

        # -------------------------------------------------
        # Only process E-lines
        # -------------------------------------------------
        if line.startswith("E") and len(parts) > 0:
            sid = parts[0].strip()

            meta = decode_sid(sid)

            # -----------------------------
            # Hour end marker
            # -----------------------------
            if is_hour_end(sid):
                out.append(line)
                hours += 1
                i += 1
                continue

            # -----------------------------
            # malformed SID
            # -----------------------------
            if meta is None or meta["src_id"] is None:
                print(f"Skipping malformed SID: {repr(sid)}")
                bad += 1
                i += 1
                continue

            src_id = meta["src_id"]

            # -----------------------------
            # REMOVE POWER STATIONS
            # -----------------------------
            if src_id in REMOVE_SOURCE_IDS:
                print(f"Removing source: {sid} (ID={src_id})")
                removed += 1

                i += 1
                _, i = read_emissions(lines, i, NSPEC)
                continue

            # -----------------------------
            # KEEP SOURCE
            # -----------------------------
            else:
                out.append(line)
                i += 1

                emis, i = read_emissions(lines, i, NSPEC)

                for j in range(0, len(emis), 8):
                    chunk = emis[j:j+8]
                    out.append(" ".join(f"{v:.3E}" for v in chunk) + "\n")

                kept += 1

        else:
            out.append(line)
            i += 1

    # -----------------------------
    # WRITE OUTPUT
    # -----------------------------
    with open(outfile, "w") as f:
        f.writelines(out)

    # -----------------------------
    # SUMMARY
    # -----------------------------
    print("\n===== SUMMARY =====")
    print(f"Input file : {infile}")
    print(f"Output file: {outfile}")
    print(f"Hours processed   : {hours}")
    print(f"Sources removed   : {removed}")
    print(f"Sources kept      : {kept}")
    print(f"Malformed skipped : {bad}")
    print("===================\n")


# -----------------------------
# RUN
# -----------------------------

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python remove_ps.py input_file output_file")
        sys.exit(1)

    clean_cit(sys.argv[1], sys.argv[2])
