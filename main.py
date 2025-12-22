import tkinter as tk
from src.gui.gui import PDFToTIFFGUI

def main():
    root = tk.Tk()
    app = PDFToTIFFGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
