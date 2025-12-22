from pypdf import PdfReader, PdfWriter
import os

TEMP_DIR = "temp"
os.makedirs(TEMP_DIR, exist_ok=True)

def merge_dop(pages_pdfs, dop_pdf_path):
    """
    Unisce il PDF DOP a tutti i PDF presenti nella lista.
    Salva i file in temp/.
    """
    if not dop_pdf_path:
        # Se non c'è DOP, restituisci i PDF originali
        return pages_pdfs.copy()

    merged_pdfs = []

    for pdf_path in pages_pdfs:
        writer = PdfWriter()

        # Aggiunge il PDF originale
        reader = PdfReader(pdf_path)
        for page in reader.pages:
            writer.add_page(page)

        # Aggiunge il PDF DOP
        dop_reader = PdfReader(dop_pdf_path)
        for page in dop_reader.pages:
            writer.add_page(page)

        base = os.path.splitext(os.path.basename(pdf_path))[0]
        merged_path = os.path.join(TEMP_DIR, f"{base}_merged.pdf")
        with open(merged_path, "wb") as f:
            writer.write(f)

        merged_pdfs.append(merged_path)

    return merged_pdfs

def merge_dop_per_pagina(pages_pdfs, default_dop, dop_map):
    """
    Unisce PDF DOP a singole pagine specifiche.
    
    pages_pdfs: lista PDF pagine singole
    default_dop: DOP globale (può essere None)
    dop_map: {pagina (int): dop_path}
    """
    merged_pdfs = []

    for idx, pdf_path in enumerate(pages_pdfs, start=1):
        writer = PdfWriter()

        # PDF pagina
        reader = PdfReader(pdf_path)
        for page in reader.pages:
            writer.add_page(page)

        # Scegli il DOP da unire: specifico o default
        dop_to_use = dop_map.get(idx, default_dop)
        if dop_to_use:
            dop_reader = PdfReader(dop_to_use)
            for page in dop_reader.pages:
                writer.add_page(page)

        base = os.path.splitext(os.path.basename(pdf_path))[0]
        merged_path = os.path.join(TEMP_DIR, f"{base}_merged.pdf")

        with open(merged_path, "wb") as f:
            writer.write(f)

        merged_pdfs.append(merged_path)

    return merged_pdfs
