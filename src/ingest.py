"""
Phase 2: Ingest + clean (validation + reconciliation).

Reads every PDF in data/raw/ and writes data/processed/blocks.jsonl, one block
per line: {"source", "page", "type" ("prose"|"table"), "content"}.

Prose and tables are extracted as SEPARATE streams so tables survive as Markdown.
Guards: corrupt files, scanned/image-only PDFs, false-positive tables, ligature
junk, block-schema checks, and a SOURCE-vs-TARGET word-count reconciliation that
proves no content was silently lost or duplicated.

Run:
    python src/ingest.py
"""

import json
import re
import sys
import unicodedata
from pathlib import Path

import pdfplumber

sys.path.append(str(Path(__file__).parent.parent))
import config  # noqa: E402

# --- validation thresholds (tune as you learn your corpus) ---------------
MIN_TABLE_ROWS = 2
MIN_TABLE_COLS = 2
MIN_TABLE_FILL = 0.40        # min fraction of non-empty cells for a real table
MIN_CHARS_PER_PAGE = 50      # below this avg -> probably scanned/image-only
COVERAGE_LOW = 0.80          # warn if target keeps < 80% of source words (data loss)
COVERAGE_HIGH = 1.10         # warn if target > 110% of source words (duplication)

_BOILERPLATE = [
    re.compile(r"^\s*\d+\s*$"),                       # bare page number
    re.compile(r"consumer financial protection bureau", re.I),
    re.compile(r"^\s*version\s+\d", re.I),
    re.compile(r"SMALL ENTITY COMPLIANCE GUIDE: MORTGAGE SERVICING RULES", re.I),  # running footer
]
_WORD = re.compile(r"\w+")


# --- helpers -------------------------------------------------------------
def normalize_unicode(text: str) -> str:
    return unicodedata.normalize("NFKC", text)


def count_words(text: str) -> int:
    """Count word tokens, ignoring Markdown punctuation like | and ---.
    Same tokenizer is used on source and target so the comparison is fair."""
    return len(_WORD.findall(normalize_unicode(text)))


def clean_text(text: str) -> str:
    text = normalize_unicode(text)
    kept = [
        line for line in text.splitlines()
        if not any(p.search(line) for p in _BOILERPLATE)
    ]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(kept)).strip()


def validate_table(grid) -> bool:
    rows = [r for r in grid if any(c not in (None, "") for c in r)]
    if len(rows) < MIN_TABLE_ROWS:
        return False
    width = max((len(r) for r in rows), default=0)
    if width < MIN_TABLE_COLS:
        return False
    total = sum(len(r) for r in rows)
    filled = sum(1 for r in rows for c in r if c not in (None, ""))
    return total > 0 and (filled / total) >= MIN_TABLE_FILL


def table_to_markdown(grid) -> str:
    rows = [
        ["" if c is None else normalize_unicode(str(c)).replace("\n", " ").strip()
         for c in row]
        for row in grid
        if any(c not in (None, "") for c in row)
    ]
    if not rows:
        return ""
    width = max(len(r) for r in rows)
    rows = [(r + [""] * width)[:width] for r in rows]
    header, body = rows[0], rows[1:]
    md = "| " + " | ".join(header) + " |\n"
    md += "| " + " | ".join("---" for _ in header) + " |\n"
    for r in body:
        md += "| " + " | ".join(r) + " |\n"
    return md.strip()


def _outside_tables(obj, bboxes) -> bool:
    h_mid = (obj["x0"] + obj["x1"]) / 2
    v_mid = (obj["top"] + obj["bottom"]) / 2
    for x0, top, x1, bottom in bboxes:
        if x0 <= h_mid < x1 and top <= v_mid < bottom:
            return False
    return True


def validate_block(block: dict) -> bool:
    if set(block) != {"source", "page", "type", "content"}:
        return False
    if block["type"] not in ("prose", "table"):
        return False
    return isinstance(block["content"], str) and bool(block["content"].strip())


# --- per-file ingestion --------------------------------------------------
def ingest_pdf(pdf_path: Path) -> dict:
    """Returns blocks + stats incl. source_words (the reconciliation baseline)."""
    blocks, empty_pages, n_chars, source_words = [], 0, 0, 0

    with pdfplumber.open(pdf_path) as pdf:
        n_pages = len(pdf.pages)
        for page_num, page in enumerate(pdf.pages, start=1):
            # SOURCE baseline: everything pdfplumber can read on this page,
            # before any filtering/cleaning. This is our "rows in" control total.
            raw_full = page.extract_text() or ""
            source_words += count_words(raw_full)

            page_has_content = False
            kept_bboxes = []
            for table in page.find_tables():
                grid = table.extract()
                if not validate_table(grid):
                    continue
                md = table_to_markdown(grid)
                if not md:
                    continue
                kept_bboxes.append(table.bbox)
                blocks.append({"source": pdf_path.name, "page": page_num,
                               "type": "table", "content": md})
                n_chars += len(md)
                page_has_content = True

            try:
                prose_raw = page.filter(
                    lambda o: _outside_tables(o, kept_bboxes)
                ).extract_text() or ""
            except Exception:
                prose_raw = raw_full

            prose = clean_text(prose_raw)
            if prose:
                blocks.append({"source": pdf_path.name, "page": page_num,
                               "type": "prose", "content": prose})
                n_chars += len(prose)
                page_has_content = True

            if not page_has_content:
                empty_pages += 1

    return {"blocks": blocks, "n_pages": n_pages, "empty_pages": empty_pages,
            "n_chars": n_chars, "source_words": source_words}


def main() -> None:
    pdfs = sorted(config.DATA_RAW.glob("*.pdf"))
    if not pdfs:
        print(f"❌ No PDFs found in {config.DATA_RAW}. Download the corpus first.")
        sys.exit(1)

    config.DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    out_path = config.DATA_PROCESSED / "blocks.jsonl"

    all_blocks, skipped, warnings = [], [], []
    tot_source_words = tot_target_words = 0

    for pdf_path in pdfs:
        print(f"Ingesting {pdf_path.name} ...")
        try:
            r = ingest_pdf(pdf_path)
        except Exception as e:
            skipped.append((pdf_path.name, f"could not open/parse: {e}"))
            print(f"   ⚠️  skipped ({e})")
            continue

        if r["n_pages"] == 0:
            skipped.append((pdf_path.name, "0 pages"))
            continue

        # scanned / empty-page detection
        if (r["n_chars"] / r["n_pages"]) < MIN_CHARS_PER_PAGE:
            warnings.append(f"{pdf_path.name}: very low text yield — likely "
                            f"scanned/image-only; needs OCR.")
        if r["empty_pages"]:
            warnings.append(f"{pdf_path.name}: {r['empty_pages']}/{r['n_pages']} "
                            f"pages produced no text.")

        # RECONCILIATION: did the output keep ~all source words, exactly once?
        target_words = sum(count_words(b["content"]) for b in r["blocks"])
        src = r["source_words"]
        coverage = (target_words / src) if src else 0.0
        if src and not (COVERAGE_LOW <= coverage <= COVERAGE_HIGH):
            flag = "DATA LOSS" if coverage < COVERAGE_LOW else "DUPLICATION"
            warnings.append(
                f"{pdf_path.name}: word coverage {coverage:.0%} "
                f"(source {src:,} -> target {target_words:,}) — possible {flag}."
            )
        tot_source_words += src
        tot_target_words += target_words
        all_blocks.extend(r["blocks"])

    valid_blocks = [b for b in all_blocks if validate_block(b)]
    dropped = len(all_blocks) - len(valid_blocks)
    if not valid_blocks:
        print("\n❌ No valid blocks produced. Nothing written. See warnings above.")
        sys.exit(1)

    with out_path.open("w") as f:
        for b in valid_blocks:
            f.write(json.dumps(b) + "\n")

    overall_cov = (tot_target_words / tot_source_words) if tot_source_words else 0.0
    cov_mark = "✅" if COVERAGE_LOW <= overall_cov <= COVERAGE_HIGH else "⚠️"
    n_prose = sum(1 for b in valid_blocks if b["type"] == "prose")
    n_table = sum(1 for b in valid_blocks if b["type"] == "table")

    print("\n" + "=" * 52)
    print("INGESTION REPORT")
    print("=" * 52)
    print(f"  Files processed: {len(pdfs) - len(skipped)}/{len(pdfs)}")
    print(f"  Prose blocks:    {n_prose}")
    print(f"  Table blocks:    {n_table}")
    print(f"  Blocks dropped by schema check: {dropped}")
    print("\n  RECONCILIATION (source vs target word count)")
    print(f"    Source words (raw PDF): {tot_source_words:,}")
    print(f"    Target words (blocks):  {tot_target_words:,}")
    print(f"    Coverage:               {overall_cov:.0%}  {cov_mark}")
    print(f"    (healthy range: {COVERAGE_LOW:.0%}-{COVERAGE_HIGH:.0%}; "
          f"low=data loss, high=duplication)")
    if skipped:
        print("\n  SKIPPED FILES:")
        for name, reason in skipped:
            print(f"    - {name}: {reason}")
    if warnings:
        print("\n  WARNINGS:")
        for w in warnings:
            print(f"    - {w}")
    print(f"\n  Written to: {out_path}")


if __name__ == "__main__":
    main()
