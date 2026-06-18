#!/usr/bin/env python3
"""
Remove selected power station sources from EDMS/CIT file.

Features
--------
- Removes Eraring & Vales Point sources
- Preserves original CIT formatting exactly
- Preserves hour boundary markers
- Preserves original emission line structure (8+9 species)
- Handles malformed records safely
"""

import sys

# =====================================================
# CONFIG
# =====================================================

REMOVE_SOURCE_IDS = {

    # Vales Point
    950, 951, 952, 953,

    # Eraring
    954, 955, 956, 957,
    958, 959, 960, 961

}

NSPEC = 17

# =====================================================
# HELPERS
# =====================================================

def decode_sid(sid):
    """
    Decode EDMS source identifier

    Format:
    EHHXXXYYYSSSSS

    Returns:
        dict or None
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
            "src_id": int(sid[9:])
        }

    except Exception:

        return None


def is_hour_end(sid):
    """
    Detect hour-end marker.

    Example:
    E00999999
    E01999999
    """

    sid = sid.strip()

    return (
        sid.startswith("E")
        and "999999" in sid
    )


def read_emissions(lines, i, nspec):
    """
    Read emission block while preserving
    original formatting.

    Returns:
        emissions
        raw_lines
        next_index
    """

    emis = []
    raw_lines = []

    while i < len(lines) and len(emis) < nspec:

        raw_lines.append(lines[i])

        try:
            emis.extend(
                [float(x) for x in lines[i].split()]
            )
        except Exception:
            pass

        i += 1

    return emis[:nspec], raw_lines, i


# =====================================================
# MAIN
# =====================================================

def clean_cit(infile, outfile):

    with open(
        infile,
        "r",
        encoding="latin-1",
        errors="ignore"
    ) as f:

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

        # ------------------------------------------------
        # Process only source records
        # ------------------------------------------------

        if line.startswith("E") and len(parts) > 0:

            sid = parts[0].strip()

            # --------------------------------------------
            # Hour marker
            # --------------------------------------------

            if is_hour_end(sid):

                out.append(line)

                hours += 1
                i += 1

                continue

            meta = decode_sid(sid)

            # --------------------------------------------
            # Malformed
            # --------------------------------------------

            if meta is None:

                print(
                    f"WARNING: malformed SID skipped: {sid}"
                )

                bad += 1

                out.append(line)

                i += 1

                continue

            src_id = meta["src_id"]

            # --------------------------------------------
            # REMOVE SOURCE
            # --------------------------------------------

            if src_id in REMOVE_SOURCE_IDS:

                print(
                    f"Removing source "
                    f"{sid} (ID={src_id})"
                )

                removed += 1

                i += 1

                _, _, i = read_emissions(
                    lines,
                    i,
                    NSPEC
                )

                continue

            # --------------------------------------------
            # KEEP SOURCE
            # --------------------------------------------

            out.append(line)

            i += 1

            _, raw_lines, i = read_emissions(
                lines,
                i,
                NSPEC
            )

            # preserve original formatting
            out.extend(raw_lines)

            kept += 1

        else:

            out.append(line)

            i += 1

    # =================================================
    # WRITE OUTPUT
    # =================================================

    with open(
        outfile,
        "w",
        encoding="latin-1"
    ) as f:

        f.writelines(out)

    # =================================================
    # SUMMARY
    # =================================================

    print("\n==============================")
    print("CIT CLEANING SUMMARY")
    print("==============================")
    print(f"Input file      : {infile}")
    print(f"Output file     : {outfile}")
    print(f"Hour markers    : {hours}")
    print(f"Sources removed : {removed}")
    print(f"Sources kept    : {kept}")
    print(f"Malformed       : {bad}")
    print("==============================\n")


# =====================================================
# RUN
# =====================================================

if __name__ == "__main__":

    if len(sys.argv) != 3:

        print(
            "Usage:\n"
            "  python remove_ps.py input.cit output.cit"
        )

        sys.exit(1)

    clean_cit(
        sys.argv[1],
        sys.argv[2]
    )

