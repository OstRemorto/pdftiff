from pypdf import PdfReader, PdfWriter
import os

TEMP_DIR = "temp"
os.makedirs(TEMP_DIR, exist_ok=True)


def check_orientation(pdf_path, password=None):
    try:
        reader = PdfReader(pdf_path, strict=False)

        if reader.is_encrypted:
            if password:
                reader.decrypt(password)
            else:
                return None

        writer = PdfWriter()

        for i, page in enumerate(reader.pages, start=1):
            box = page.cropbox
            width = float(box.width)
            height = float(box.height)

            rotation = page.get("/Rotate", 0) % 360

            # dimensioni reali della pagina
            if rotation in (90, 270):
                actual_width, actual_height = height, width
            else:
                actual_width, actual_height = width, height

            # se landscape → ruota a portrait
            if actual_width > actual_height:
                page.rotate(90)   # ✅ UNIVERSALE
                print(f"Pagina {i}: ruotata")
            else:
                print(f"Pagina {i}: OK")

            writer.add_page(page)

        base = os.path.splitext(os.path.basename(pdf_path))[0]
        output_path = os.path.join(TEMP_DIR, f"{base}_fixed.pdf")

        with open(output_path, "wb") as f:
            writer.write(f)

        return output_path

    except Exception as e:
        print(f"❌ Errore orientamento PDF: {e}")
        return None
