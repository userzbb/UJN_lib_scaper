import logging
import os

logger = logging.getLogger("HTTP_Cracker")


def generate_dictionary_file(filepath, gender="ALL", specific_day=None, max_seq=500):
    """
    Generates a password dictionary file based on parameters.
    Format: day_key,password
    """
    days = [specific_day] if specific_day else [f"{d:02d}" for d in range(1, 32)]

    if gender.upper() == "ALL":
        target_genders = ["M", "F"]
    else:
        target_genders = [gender.upper()]

    count = 0
    # Ensure directory exists
    try:
        directory = os.path.dirname(os.path.abspath(filepath))
        if directory:
            os.makedirs(directory, exist_ok=True)
    except Exception as e:
        logger.warning(f"Could not create directory for dictionary: {e}")

    with open(filepath, "w", encoding="utf-8") as f:
        for g in target_genders:
            target_remainder = 1 if g == "M" else 0

            for dd in days:
                day_key = f"{g}_{dd}"

                for seq in range(max_seq):
                    if seq % 2 != target_remainder:
                        continue

                    sss = f"{seq:03d}"
                    for check in range(10):
                        c = str(check)
                        password = f"{dd}{sss}{c}"
                        f.write(f"{day_key},{password}\n")
                        count += 1
    return count


def load_tasks_from_file(filepath, progress_map=None, stats=None):
    """
    Yields (password, day_key) from the dictionary file,
    skipping items that have already been processed according to progress_map.
    Updates `stats['skipped']` if provided.
    """
    if progress_map is None:
        progress_map = {}
    if stats is None:
        stats = {}
    if "skipped" not in stats:
        stats["skipped"] = 0

    # State tracking for skipping: { day_key: {'skipping': bool, 'target': str} }
    skipping_state = {}

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                parts = line.split(",")
                if len(parts) != 2:
                    continue

                day_key, password = parts

                # Initialize skipping state for this day_key if not seen yet
                if day_key not in skipping_state:
                    resume_pw = progress_map.get(day_key)

                    # Legacy fallback logic
                    if not resume_pw and "_" in day_key:
                        g, dd = day_key.split("_")
                        legacy_pw = progress_map.get(dd)
                        if legacy_pw:
                            target_rem = 1 if g == "M" else 0
                            try:
                                if int(legacy_pw[4]) % 2 == target_rem:
                                    resume_pw = legacy_pw
                                    logger.info(
                                        f"[*] Day {dd} ({g}): Found legacy progress {resume_pw}"
                                    )
                            except (IndexError, ValueError):
                                pass

                    if resume_pw:
                        skipping_state[day_key] = {
                            "skipping": True,
                            "target": resume_pw,
                        }
                        logger.info(f"[*] Day {day_key}: Resuming from {resume_pw}")
                    else:
                        skipping_state[day_key] = {"skipping": False, "target": None}

                state = skipping_state[day_key]

                if state["skipping"]:
                    stats["skipped"] += 1
                    if password == state["target"]:
                        state["skipping"] = False
                    continue

                yield password, day_key

    except FileNotFoundError:
        logger.error(f"Dictionary file {filepath} not found.")
        return
