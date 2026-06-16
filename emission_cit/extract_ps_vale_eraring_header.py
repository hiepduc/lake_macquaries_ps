#!/usr/bin/env python3

import sys

KEEP_SOURCE_IDS = {
    950,951,952,953,      # Vales Point
    954,955,956,957,
    958,959,960,961       # Eraring
}

NSPEC = 17


def decode_sid(sid):

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

    sid = sid.strip()

    return (
        sid.startswith("E")
        and "999999" in sid
    )


def extract_ps(infile, outfile):

    with open(infile, "r", encoding="latin-1") as f:
        lines = f.readlines()

    out = []

    i = 0

    # --------------------------------------------------
    # Copy header exactly
    # --------------------------------------------------

    while i < len(lines):

        line = lines[i]

        if line.startswith("E"):
            line = "*\n"
            out.append(line)
            break

        out.append(line)
        i += 1

    extracted = 0
    hours = 0

    # --------------------------------------------------
    # Process source records
    # --------------------------------------------------

    while i < len(lines):

        line = lines[i]

        parts = line.split()

        if not (line.startswith("E") and len(parts) > 0):
            i += 1
            continue

        sid = parts[0]

        # ------------------------------------------
        # Hour marker
        # ------------------------------------------

        if is_hour_end(sid):

            out.append(line)

            hours += 1
            i += 1
            continue

        meta = decode_sid(sid)

        if meta is None:

            i += 1
            continue

        src_id = meta["src_id"]

        # save start position
        start = i

        i += 1

        emis_count = 0

        while emis_count < NSPEC and i < len(lines):

            try:
                emis_count += len(lines[i].split())
            except:
                pass

            i += 1

        # ------------------------------------------
        # keep power stations
        # ------------------------------------------

        if src_id in KEEP_SOURCE_IDS:

            out.extend(lines[start:i])

            extracted += 1

    # --------------------------------------------------
    # Write file
    # --------------------------------------------------

    with open(outfile, "w") as f:
        f.writelines(out)

    print()
    print("================================")
    print("Power station extraction complete")
    print("================================")
    print("Input :", infile)
    print("Output:", outfile)
    print("Hours :", hours)
    print("Records extracted:", extracted)
    print("================================")
    print()


if __name__ == "__main__":

    if len(sys.argv) != 3:

        print(
            "Usage:\n"
            "python extract_ps.py input.ems output.ems"
        )

        sys.exit(1)

    extract_ps(
        sys.argv[1],
        sys.argv[2]
    )

