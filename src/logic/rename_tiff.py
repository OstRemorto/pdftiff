import os
import re


def get_next_index(folder):
    """
    Restituisce il prossimo indice disponibile (int)
    basandosi sui file TIFF presenti nella cartella
    """
    if not os.path.exists(folder):
        return 1

    max_index = 0
    pattern = re.compile(r"(\d{3})\.tiff?$", re.IGNORECASE)

    for filename in os.listdir(folder):
        match = pattern.search(filename)
        if match:
            num = int(match.group(1))
            max_index = max(max_index, num)

    return max_index + 1

def get_tiff_path(base_dir, fornitore, ddt):
    """
    Crea la cartella fornitore/DDT e restituisce
    il path del prossimo TIFF disponibile
    """
    folder = os.path.join(base_dir, fornitore, ddt)
    os.makedirs(folder, exist_ok=True)

    index = get_next_index(folder)
    filename = f"{index:03d}.tiff"

    return os.path.join(folder, filename)
