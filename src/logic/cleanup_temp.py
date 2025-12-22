import os
import glob
import shutil

TEMP_DIR = "temp"

def clean_temp():
    """
    Elimina tutti i file temporanei nella cartella temp/.
    """
    if os.path.exists(TEMP_DIR):
        # elimina tutti i file all'interno di temp
        files = glob.glob(os.path.join(TEMP_DIR, "*"))
        for f in files:
            try:
                os.remove(f)
            except Exception as e:
                print(f"Impossibile eliminare {f}: {e}")
