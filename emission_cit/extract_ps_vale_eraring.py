#!/usr/bin/env python3
"""
Extract power station sources from a CIT point-source emission file.

Extracts:

Vales Point:
    950, 951, 952, 953

Eraring:
    954, 955, 956, 957,
    958, 959, 960, 961

Output remains in original CIT format.

Usage:
    python extract_ps.py input.ems output.ems
"""

import sys

# ----------------------------------------------------------
# POWER STATION SOURCE IDS
# ----------------------------------------------------------

KEEP_SOURCE_IDS = set([

    # Vales Point
    950, 951, 952, 953,

    # Eraring
    954, 955, 956, 957,
    958, 959, 960, 961
])

# Number of species in CIT file
NSPEC = 17

# ----------------------------------------------------------
# HELPERS
# ----------------------------------------------------------

def decode_sid(sid):
    """
    Decode EDMS/CIT ID

    Format:
        EHHXXXYYYSSSSS

    Returns dictionary or None
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

    except:
        return None


def is_hour_end(sid):
    """
    Detect hour marker

    Example:
        E0199999900000
    """

    sid = sid.strip()

    return (
        sid.startswith("E")
        and "999999" in sid
    )


def read_emissions(lines, i, nspec):
    """
    Read multi-line emission block.
    """

    emis = []

    while len(emis) < nspec and i < len(lines):

        try:
            emis.extend(
                [float(x) for x in lines[i].split()]
            )
        except:
            pass

        i += 1

    return emis[:nspec], i


# ----------------------------------------------------------
# MAIN
# ----------------------------------------------------------

def extract_sources(infile, outfile):

    with open(infile, "r", encoding="latin-1") as f:
        lines = f.readlines()

    out = []

    i = 0

    extracted = 0
    skipped = 0
    malformed = 0
    hours = 0

    while i < len(lines):

        line = lines[i]

        parts = line.split()

        # --------------------------------------------------
        # Process E-records
        # --------------------------------------------------

        if line.startswith("E") and len(parts) > 0:

            sid = parts[0].strip()

            # ----------------------------------------------
            # Hour boundary marker
            # ----------------------------------------------

            if is_hour_end(sid):

                out.append(line)

                hours += 1
                i += 1

                continue

            # ----------------------------------------------
            # Decode source ID
            # ----------------------------------------------

            meta = decode_sid(sid)

            if meta is None:

                malformed += 1
                i += 1

                continue

            src_id = meta["src_id"]

            # Read emission block
            i += 1

            emis, i = read_emissions(
                lines,
                i,
                NSPEC
            )

            # ----------------------------------------------
            # Keep only power stations
            # ----------------------------------------------

            if src_id in KEEP_SOURCE_IDS:

                out.append(line)

                for j in range(0, len(emis), 8):

                    chunk = emis[j:j+8]

                    out.append(
                        " ".join(
                            f"{v:.3E}"
                            for v in chunk
                        ) + "\n"
                    )

                extracted += 1

            else:

                skipped += 1

        else:

            i += 1

    # ------------------------------------------------------
    # Write output
    # ------------------------------------------------------

    with open(outfile, "w") as f:
        f.writelines(out)

    # ------------------------------------------------------
    # Summary
    # ------------------------------------------------------

    print("\n====================================")
    print("POWER STATION EXTRACTION COMPLETE")
    print("====================================")
    print(f"Input file      : {infile}")
    print(f"Output file     : {outfile}")
    print(f"Hours processed : {hours}")
    print(f"Records kept    : {extracted}")
    print(f"Records skipped : {skipped}")
    print(f"Malformed       : {malformed}")
    print("====================================\n")


# ----------------------------------------------------------
# RUN
# ----------------------------------------------------------

if __name__ == "__main__":

    if len(sys.argv) != 3:

        print(
            "Usage:\n"
            "    python extract_ps.py input.ems output.ems"
        )

        sys.exit(1)

    extract_sources(
        sys.argv[1],
        sys.argv[2]
    )

