import glob

from src.logic.check import check_orientation
from src.logic.split import split_pdf
from src.logic.merge import merge_dop, merge_dop_per_pagina
from src.logic.convert import pdf_to_tiff
from src.logic.cleanup_temp import clean_temp

from src.utils.config import INPUT_DIR


class ConversionWorker:
    def __init__(self, progress_cb=None):
        """
        progress_cb: funzione callback (current, total)
        """
        self.progress_cb = progress_cb

    def convert(
        self,
        pdf_files,
        output_dir,
        split_mode="none",
        custom_ranges="",
        dop_active=False,
        dop_file=None,
        dop_map=None
    ):
        try:
            pdfs_final = []

            # 1️⃣ Check orientamento + split
            for pdf in pdf_files:
                checked = check_orientation(pdf)

                if split_mode == "single":
                    pages = split_pdf(checked)

                elif split_mode == "custom":
                    pages = split_pdf(checked, custom_ranges)

                else:
                    pages = [checked]

                pdfs_final.extend(pages)

            # 2️⃣ Merge DOP
            if dop_map:
                pdfs_final = merge_dop_per_pagina(pdfs_final, dop_file, dop_map)
            elif dop_active and dop_file:
                pdfs_final = merge_dop(pdfs_final, dop_file)

            # 3️⃣ Conversione TIFF
            total = len(pdfs_final)

            for idx, pdf in enumerate(pdfs_final, start=1):
                out = output_dir / f"{idx:03d}.tiff"
                pdf_to_tiff(pdf, out)

                if self.progress_cb:
                    self.progress_cb(idx, total)

        finally:
            clean_temp()
