import csv
import re
from pymarc import MARCReader

MARC_FILE = "UUBFK-Records.mrc"
OUTPUT_CSV = "call_numbers_pages.csv"

AVG_PAGES_PER_VOLUME = 500   # change this to your preferred average
DEFAULT_VOLUMES = 1          # used when the marker has no number (e.g. just "c.")

# number + volume marker: "3 v.", "2 volumes", "4 cilt", "5 c."
# (?=\W|$) stops "cm" in "24 cm" from matching as "c"
VOLUME_WITH_NUMBER = re.compile(
    r"(\d+)\s*(?:volumes?|v\.?|cilt|c\.?)(?=\W|$)", re.IGNORECASE
)
# marker with no number in front of it, e.g. "c." or "cilt"
VOLUME_NO_NUMBER = re.compile(
    r"(?<![\w])(?:volumes?|v\.|cilt|c\.)(?!\w)", re.IGNORECASE
)



def get_call_number(record):
    """Build the LC call number from field 050 ($a + $b)."""
    field = record.get("050")
    if not field:
        return ""
    parts = field.get_subfields("a", "b")
    return " ".join(p.strip() for p in parts).strip()



def get_pages(record):
    """
    Extract the page count from 300 $a.
    - Multi-volume items ('3 v.', '2 cilt', '5 c.', or a bare 'c.'):
      pages = number of volumes * AVG_PAGES_PER_VOLUME
    - Otherwise: number followed by p / pp / pages, else the largest number.
    Returns (page_count, raw_300a_text).
    """
    field = record.get("300")
    if not field:
        return None, ""

    raw = " ".join(field.get_subfields("a")).strip()
    if not raw:
        return None, raw

    # 1) Volumes with a number
    m = VOLUME_WITH_NUMBER.search(raw)
    if m:
        return int(m.group(1)) * AVG_PAGES_PER_VOLUME, raw

    # 2) Volume marker without a number (e.g. just "c.")
    if VOLUME_NO_NUMBER.search(raw):
        return DEFAULT_VOLUMES * AVG_PAGES_PER_VOLUME, raw

    # 3) Normal single-volume page count
    matches = re.findall(r"(\d+)\s*(?:p\b|pp\b|pages?\b)", raw, re.IGNORECASE)
    if matches:
        return int(matches[-1]), raw

    numbers = [int(n) for n in re.findall(r"\d+", raw)]
    return (max(numbers) if numbers else None), raw



def main():
    count = 0
    with open(MARC_FILE, "rb") as fh, \
         open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as out:

        reader = MARCReader(fh, to_unicode=True, force_utf8=True)
        writer = csv.writer(out)
        writer.writerow(["control_number", "title", "call_number", "pages", "raw_300a"])

        for record in reader:
            if record is None:  # skip unreadable records
                continue

            f001 = record.get("001")
            control_no = f001.data if f001 else ""

            f245 = record.get("245")
            title = " ".join(f245.get_subfields("a", "b")).strip(" /:;,.") if f245 else ""

            call_no = get_call_number(record)
            pages, raw_300 = get_pages(record)

            writer.writerow([control_no, title, call_no, pages or "", raw_300])
            count += 1

    print(f"Done. {count} records written to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
