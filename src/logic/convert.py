import subprocess
import os
from pypdf import PdfReader, PdfWriter, PageObject

TEMP_DIR = "temp"
os.makedirs(TEMP_DIR, exist_ok=True)

def fix_pdf_mediabox(pdf_path):
    """
    Ripara PDF con MediaBox mancante o invalida.
    Ritorna il percorso del PDF corretto (stesso file se non serve modifiche, altrimenti temp/fixed.pdf)
    """
    reader = PdfReader(pdf_path)
    needs_fix = False

    # Controlla se almeno una pagina ha MediaBox invalida
    for page in reader.pages:
        try:
            mb = page.mediabox
            if not mb or len(mb) != 4:
                needs_fix = True
                break
        except Exception:
            needs_fix = True
            break

    if not needs_fix:
        return os.path.abspath(pdf_path)

    # Creazione PDF corretto
    writer = PdfWriter()
    for page in reader.pages:
        try:
            mb = page.mediabox
            if not mb or len(mb) != 4:
                raise Exception
            writer.add_page(page)
        except Exception:
            # Crea nuova pagina A4 vuota e copia contenuti (se possibile)
            new_page = PageObject.create_blank_page(width=595, height=842)
            try:
                for content_page in page.get_contents():
                    new_page.merge_page(page)
            except Exception:
                pass  # se la pagina è totalmente corrotta, la lasciamo vuota
            writer.add_page(new_page)

    fixed_path = os.path.join(TEMP_DIR, f"{os.path.basename(pdf_path)}_fixed.pdf")
    with open(fixed_path, "wb") as f:
        writer.write(f)

    print(f"[INFO] PDF riparato: {pdf_path} → {fixed_path}")
    return os.path.abspath(fixed_path)



def pdf_to_tiff(pdf_path, output_path):
    """
    Converte un PDF in TIFF usando Ghostscript.
    output_path deve essere il percorso completo con nome.tiff
    """
    # Ripara PDF se necessario
    pdf_path = fix_pdf_mediabox(pdf_path)

    # Ghostscript: Windows 'gswin64c', Linux/Mac 'gs'
    cmd = [
        "gswin64c",
        "-dBATCH",
        "-dNOPAUSE",
        "-sDEVICE=tiff24nc",
        "-r300",
        f"-sOutputFile={output_path}",
        pdf_path
    ]
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"[ERRORE] Conversione fallita per {pdf_path}: {e}")
