from pypdf import PdfReader, PdfWriter
import os

TEMP_DIR = "temp"
os.makedirs(TEMP_DIR, exist_ok=True)

def split_pdf(pdf_path, custom_ranges=None):
    reader = PdfReader(pdf_path, strict=False)
    total_pages = len(reader.pages)
    output_files = []

    base = os.path.splitext(os.path.basename(pdf_path))[0]

    # 🔹 SPLIT STANDARD
    if not custom_ranges:
        for i, page in enumerate(reader.pages, start=1):
            writer = PdfWriter()
            writer.add_page(page)

            out = os.path.join(TEMP_DIR, f"{base}_page{i}.pdf")
            with open(out, "wb") as f:
                writer.write(f)

            output_files.append(out)

        return output_files

    # 🔹 SPLIT PERSONALIZZATO
    ranges = parse_page_ranges(custom_ranges, total_pages)

    for idx, (start, end) in enumerate(ranges, start=1):
        writer = PdfWriter()
        for p in range(start - 1, end):
            writer.add_page(reader.pages[p])

        out = os.path.join(
            TEMP_DIR, f"{base}_part{idx}_{start}-{end}.pdf"
        )

        with open(out, "wb") as f:
            writer.write(f)

        output_files.append(out)

    return output_files

def parse_page_ranges(ranges_text, total_pages):
    """
    '1-3,4-5,6' → [(1,3),(4,5),(6,6)]
    """
    used_pages = set()
    ranges = []

    for part in ranges_text.split(","):
        part = part.strip()

        if "-" in part:
            a, b = part.split("-", 1)
            start, end = int(a), int(b)
            if start > end:
                raise ValueError(f"Intervallo non valido: {part}")
        else:
            start = end = int(part)

        if start < 1 or end > total_pages:
            raise ValueError(
                f"Pagine non valide ({total_pages} totali): {part}"
            )

        for p in range(start, end + 1):
            if p in used_pages:
                raise ValueError(f"Pagina {p} duplicata o sovrapposta")
            used_pages.add(p)

        ranges.append((start, end))

    return ranges
