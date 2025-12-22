import tkinter as tk
from tkinter import ttk, messagebox
import threading
from tkinter import filedialog
from pypdf import PdfReader
from pathlib import Path
from PIL import Image, ImageTk
import fitz
from functools import partial

from src.utils.config import load_config, save_config, INVALID_CHARS, FORNITORI_FILE, DOP_DIR, INPUT_DIR, CERTIFICATI_DIR, BASE_DIR

from src.worker import ConversionWorker

# ================== GUI ==================
class PDFToTIFFGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF → TIFF Converter")
        self.root.geometry("900x800")
        self.root.minsize(850, 750)
        self._center_window()

        # Variabili
        self.fornitore_var = tk.StringVar(value="Seleziona")
        self.ddt_var = tk.StringVar()

        self.import_mode = tk.StringVar(value="all")
        self.single_pdf_path = tk.StringVar()

        self.split_mode = tk.StringVar(value="none")
        self.custom_split_var = tk.StringVar()

        self.dop_var = tk.BooleanVar(value=False)
        self.dop_path = tk.StringVar()

        self._build_ui()
        self.fornitori = self.load_fornitori()

        self.pdf_doc = None       # documento PDF corrente
        self.pdf_page_index = 0   # pagina corrente

        self._setup_style()
        self._setup_preview_responsive()

    # ---------- GESTIONE FORNITORI ----------
    def load_fornitori(self):
        if not FORNITORI_FILE.exists():
            return []
        with open(FORNITORI_FILE, "r", encoding="utf-8") as f:
            return sorted([line.strip() for line in f if line.strip()])

    def save_fornitori(self, fornitori):
        with open(FORNITORI_FILE, "w", encoding="utf-8") as f:
            for nome in sorted(fornitori):
                f.write(nome + "\n")

    def _load_fornitori_combobox(self):
        self.fornitore_combo["values"] = self.load_fornitori()

    # ---------- STILE ----------
    def _setup_style(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TLabel", font=("Segoe UI", 10))
        style.configure("Header.TLabel", font=("Segoe UI", 11, "bold"))
        style.configure("TButton", font=("Segoe UI", 10), padding=6)
        style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"), padding=8)
        style.configure("TCheckbutton", font=("Segoe UI", 10))
        style.configure("green.Horizontal.TProgressbar", troughcolor = 'white', background = 'green')

    # ---------- COSTRUZIONE UI ----------
    def _build_ui(self):
        main_frame = ttk.Frame(self.root, padding=15)
        main_frame.pack(fill="both", expand=True)
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)


        # ---------- FRAME SINISTRA: OPZIONI ----------
        left_frame = ttk.Frame(main_frame)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        left_frame.columnconfigure(0, weight=0)

        # ---------- FRAME DESTRA: ANTEPRIMA PDF ----------
        right_frame = ttk.Frame(main_frame)
        right_frame.grid(row=0, column=1, sticky="nsew")
        right_frame.rowconfigure(0, weight=1)
        right_frame.columnconfigure(0, weight=1)

        # ---------- FRAME ANTEPRIMA ----------
        self.pdf_canvas = tk.Canvas(right_frame, bg="lightgray", highlightthickness=2, highlightbackground="black")
        self.pdf_canvas.grid(row=0, column=0, sticky="nsew")

        # Pulsanti navigazione PDF
        nav_frame = ttk.Frame(right_frame)
        nav_frame.grid(row=1, column=0, pady=5)
        self.prev_page_btn = ttk.Button(nav_frame, text="<< Pagina precedente", command=self._prev_pdf_page)
        self.prev_page_btn.pack(side="left", padx=5)
        self.next_page_btn = ttk.Button(nav_frame, text="Pagina successiva >>", command=self._next_pdf_page)
        self.next_page_btn.pack(side="left", padx=5)

        # Event per ridimensionamento canvas
        self.pdf_canvas.bind("<Configure>", self._resize_pdf_preview)

        # Header
        ttk.Label(left_frame, text="Conversione PDF → TIFF", style="Header.TLabel")\
            .grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 15))

        try:
            icon_path = BASE_DIR / "assets" / "settings.png"
            img = Image.open(icon_path)
            img = img.resize((24, 24), Image.Resampling.LANCZOS)  # ridimensiona se serve
            self.settings_icon = ImageTk.PhotoImage(img)
        except Exception as e:
            print("Errore caricamento icona impostazioni:", e)
            self.settings_icon = None

        settings_btn = ttk.Button(
            left_frame,
            image=self.settings_icon,
            command=self._open_settings,
            style="Toolbutton"
        )
        settings_btn.grid(row=0, column=3, sticky="e", pady=(0, 15))

        # ===== FORNITORE / DDT =====
        self.fornitori = self.load_fornitori()

        ttk.Label(left_frame, text="Fornitore").grid(row=1, column=0, sticky="w")

        self.fornitore_var = tk.StringVar()
        self.fornitore_combo = ttk.Combobox(
            left_frame,
            textvariable=self.fornitore_var,
            values=self.fornitori,
            width=45,
            state="readonly"
        )
        self.fornitore_combo.grid(row=1, column=1, padx=(10, 2), sticky="w")
        self.fornitore_combo.set("Seleziona")

        ttk.Button(left_frame, text="+", width=2,
                   command=self._add_fornitore_popup)\
            .grid(row=1, column=2, sticky="w")

        ttk.Button(left_frame, text="-", width=2,
                   command=self._edit_fornitore)\
            .grid(row=1, column=3, sticky="w")

        ttk.Label(left_frame, text="DDT").grid(row=2, column=0, sticky="w", pady=(10,0))
        self.ddt_entry = ttk.Entry(left_frame, textvariable=self.ddt_var, width=20)
        self.ddt_entry.grid(row=2, column=1, padx=10, sticky="w", columnspan=3)

        # ===== IMPORT PDF =====
        ttk.Separator(left_frame).grid(row=3, column=0, columnspan=4, sticky="ew", pady=15)

        self.import_mode = tk.StringVar(value="all")
        ttk.Radiobutton(left_frame, text="Importa tutti i PDF dalla cartella input",
                        variable=self.import_mode, value="all").grid(row=4, column=0, columnspan=3, sticky="w")
        ttk.Radiobutton(left_frame, text="Importa un solo PDF",
                        variable=self.import_mode, value="single").grid(row=5, column=0, sticky="w")

        self.single_pdf_path = tk.StringVar()
        self.single_pdf_entry = ttk.Entry(left_frame, textvariable=self.single_pdf_path, width=50)
        self.single_pdf_entry.grid(row=5, column=1, columnspan=2, padx=10, sticky="w")

        self.single_pdf_button = ttk.Button(left_frame, text="Sfoglia", command=self._choose_single_pdf)
        self.single_pdf_button.grid(row=5, column=3, sticky="w")

        self.import_mode.trace_add("write", self._update_import_mode)
        self.import_mode.trace_add("write", self._update_griglia_state)
        self._update_import_mode()  # stato iniziale

        # ===== SPLIT =====
        ttk.Separator(left_frame).grid(row=6, column=0, columnspan=4, sticky="ew", pady=15)

        ttk.Label(left_frame, text="Divisione PDF", style="Header.TLabel")\
            .grid(row=7, column=0, sticky="w")

        ttk.Radiobutton(
            left_frame, text="Nessuna divisione",
            variable=self.split_mode, value="none"
        ).grid(row=8, column=0, sticky="w")

        ttk.Radiobutton(
            left_frame, text="Dividi una pagina per file",
            variable=self.split_mode, value="single"
        ).grid(row=9, column=0, sticky="w")

        ttk.Radiobutton(
            left_frame, text="Divisione personalizzata (es. 1-3,4-5,6)",
            variable=self.split_mode, value="custom"
        ).grid(row=10, column=0, sticky="w")

        self.custom_split_entry = ttk.Entry(
            left_frame, textvariable=self.custom_split_var, width=30
        )
        self.custom_split_entry.grid(row=10, column=1, padx=10, sticky="w")
        self.custom_split_entry.state(["disabled"])

        # aggiorna stato entry split
        self.split_mode.trace_add("write", self._update_split_state)
        self.split_mode.trace_add("write", self._update_griglia_state)
        self._update_split_state()

        # ===== DOP =====
        ttk.Separator(left_frame).grid(row=11, column=0, columnspan=4, sticky="ew", pady=15)

        self.dop_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            left_frame, text="Unisci DOP",
            variable=self.dop_var
        ).grid(row=12, column=0, sticky="w")

        self.dop_entry = ttk.Entry(left_frame, textvariable=self.dop_path, width=50)
        self.dop_entry.grid(row=12, column=1, columnspan=2, padx=10, sticky="w")

        self.dop_button = ttk.Button(
            left_frame, text="Sfoglia DOP",
            command=self._choose_dop_file
        )
        self.dop_button.grid(row=12, column=3, sticky="w")

        self.dop_var.trace_add("write", self._update_dop_state)
        self.dop_var.trace_add("write", self._update_griglia_state)
        self._update_dop_state()

        # ===== GRIGLIA DOP PER PAGINA =====
        ttk.Separator(left_frame).grid(row=13, column=0, columnspan=4, sticky="ew", pady=15)

        ttk.Label(left_frame, text="DOP per pagina", style="Header.TLabel")\
            .grid(row=14, column=0, sticky="w")

        ttk.Label(left_frame, text="Pagina (es. 1,5,7,..)")\
            .grid(row=15, column=0, sticky="w")

        ttk.Label(left_frame, text="File associato")\
            .grid(row=15, column=1, sticky="w")

        self.page_entries = []
        self.file_entries = []
        self.griglia_buttons = []

        for i in range(5):
            row = 16 + i

            page_entry = ttk.Entry(left_frame, width=10)
            page_entry.grid(row=row, column=0, pady=3, sticky="w")

            file_var = tk.StringVar()
            file_entry = ttk.Entry(left_frame, textvariable=file_var, width=45)
            file_entry.grid(row=row, column=1, columnspan=2, pady=3, padx=10, sticky="w")

            browse_btn = ttk.Button(
                left_frame, text="Sfoglia",
                command=lambda v=file_var: self._choose_generic_file(v)
            )
            browse_btn.grid(row=row, column=3, sticky="w")

            self.page_entries.append(page_entry)
            self.file_entries.append(file_var)
            self.griglia_buttons.append(browse_btn)

        self._update_griglia_state()

        # ===== AVVIO + PROGRESS =====
        ttk.Separator(left_frame).grid(row=21, column=0, columnspan=4, sticky="ew", pady=20)
        self.progress = ttk.Progressbar(left_frame, length=850, mode="determinate", style = "green.Horizontal.TProgressbar")
        self.progress.grid(row=22, column=0, columnspan=4, pady=10)

        ttk.Button(left_frame, text="Avvia conversione", style="Accent.TButton",
                   command=self._start_conversion).grid(row=23, column=0, columnspan=4, pady=10)
        self.start_button = ttk.Button(left_frame, text="Avvia conversione", style="Accent.TButton", command=self._start_conversion)
        self.start_button.grid(row=23, column=0, columnspan=4, pady=10)
        
    # ---------- CENTRA FINESTRA ----------
    def _center_window(self):
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    # ----- FUNZIONI PER PDF -----
    def _setup_preview_responsive(self):
        self.preview_threshold = 900  # larghezza minima per mostrare anteprima
        self.root.bind("<Configure>", self._on_resize)

    def _on_resize(self, event):
        if event.width >= self.preview_threshold:
            self._show_preview()
        else:
            self._hide_preview()

    def _show_preview(self):
        # mostra il frame con anteprima
        self.pdf_canvas.master.grid()  # riattacca right_frame

        # ridisegna l'ultimo PDF caricato se ce n'è uno
        if self.pdf_doc:
            self._show_pdf_page()

    def _hide_preview(self):
        # nascondi il frame con anteprima
        self.pdf_canvas.master.grid_remove()

    def _show_pdf_page(self):
        """Mostra la pagina corrente nel canvas"""
        if not self.pdf_doc:
            return

        try:
            page = self.pdf_doc[self.pdf_page_index]
            # Usa fitz per creare il pixmap in RGB
            pix = page.get_pixmap(colorspace=fitz.csRGB)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            # Ridimensiona mantenendo proporzioni per il canvas
            canvas_width = self.pdf_canvas.winfo_width()
            canvas_height = self.pdf_canvas.winfo_height()

            img_width, img_height = img.size
            ratio = min(canvas_width / img_width, canvas_height / img_height)
            new_size = (int(img_width * ratio), int(img_height * ratio))
            img_resized = img.resize(new_size, Image.Resampling.LANCZOS)

            # Mostra l'immagine sul canvas
            self.tk_pdf_image = ImageTk.PhotoImage(img_resized)
            self.pdf_canvas.delete("all")
            self.pdf_canvas.create_image(
                canvas_width // 2,
                canvas_height // 2,
                image=self.tk_pdf_image,
                anchor="center"
            )

        except Exception as e:
            self.pdf_canvas.delete("all")
            self.pdf_canvas.create_text(
                self.pdf_canvas.winfo_width() // 2,
                self.pdf_canvas.winfo_height() // 2,
                text=f"Errore anteprima:\n{e}",
                fill="black",
                font=("Segoe UI", 12),
                anchor="center"
            )
            print("Errore anteprima PDF:", e)

    def _resize_pdf_preview(self, event=None):
        """Ridimensiona l'immagine PDF per adattarla al canvas"""
        if not hasattr(self, "current_pdf_image"):
            return

        canvas_width = self.pdf_canvas.winfo_width()
        canvas_height = self.pdf_canvas.winfo_height()

        # Mantieni proporzioni
        img_width, img_height = self.current_pdf_image.size
        ratio = min(canvas_width / img_width, canvas_height / img_height)
        new_size = (int(img_width * ratio), int(img_height * ratio))

        resized_img = self.current_pdf_image.resize(new_size, Image.ANTIALIAS)
        self.tk_pdf_image = ImageTk.PhotoImage(resized_img)
        self.pdf_canvas.delete("all")  # pulisci canvas
        self.pdf_canvas.create_image(canvas_width // 2, canvas_height // 2, image=self.tk_pdf_image, anchor="center")

    def _load_pdf_preview(self, pdf_path):
        """Carica il PDF selezionato e mostra la prima pagina"""
        try:
            self.pdf_doc = fitz.open(pdf_path)
            self.pdf_page_index = 0
            self._show_pdf_page()
        except Exception as e:
            self.pdf_doc = None
            self.pdf_canvas.delete("all")
            self.pdf_canvas.create_text(
                self.pdf_canvas.winfo_width() // 2,
                self.pdf_canvas.winfo_height() // 2,
                text=f"Errore anteprima:\n{e}",
                fill="black",
                font=("Segoe UI", 12),
                anchor="center"
            )
            print("Errore anteprima PDF:", e)

    def _next_pdf_page(self):
        if self.pdf_doc and self.pdf_page_index < len(self.pdf_doc) - 1:
            self.pdf_page_index += 1
            self._show_pdf_page()

    def _prev_pdf_page(self):
        if self.pdf_doc and self.pdf_page_index > 0:
            self.pdf_page_index -= 1
            self._show_pdf_page()

    # ---------- POPUP AGGIUNGI FORNITORE ----------
    def _add_fornitore_popup(self):
        popup = tk.Toplevel(self.root)
        popup.title("Nuovo fornitore")
        popup.geometry("330x150")
        popup.resizable(False, False)
        popup.transient(self.root)
        popup.grab_set()

        # ---------- CENTRA POPUP SULLO SCHERMO ----------
        popup.update_idletasks()  # forza aggiornamento dimensioni
        width = popup.winfo_width()
        height = popup.winfo_height()
        screen_width = popup.winfo_screenwidth()
        screen_height = popup.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        popup.geometry(f"{width}x{height}+{x}+{y}")

        ttk.Label(popup, text="Nome fornitore:").pack(pady=(15, 5))

        var = tk.StringVar()
        entry = ttk.Entry(popup, textvariable=var, width=34)
        entry.pack()
        entry.focus()

        frame = ttk.Frame(popup)
        frame.pack(pady=15)

        def conferma():
            nome = var.get().strip().upper()

            if not nome:
                messagebox.showerror("Errore", "Nome non valido", parent=popup)
                return

            if any(c in INVALID_CHARS for c in nome):
                messagebox.showerror(
                    "Errore",
                    f"Caratteri non validi:\n{INVALID_CHARS}",
                    parent=popup
                )
                return

            if nome in self.fornitori:
                messagebox.showwarning(
                    "Attenzione",
                    "Fornitore già presente",
                    parent=popup
                )
                return

            self.fornitori.append(nome)
            self.fornitori.sort()
            self.save_fornitori(self.fornitori)

            self.fornitore_combo["values"] = self.fornitori
            self.fornitore_combo.set(nome)

            popup.destroy()

        ttk.Button(frame, text="Conferma", command=conferma)\
            .grid(row=0, column=0, padx=5)
        ttk.Button(frame, text="Annulla", command=popup.destroy)\
            .grid(row=0, column=1, padx=5)

        popup.bind("<Return>", lambda e: conferma())
        popup.bind("<Escape>", lambda e: popup.destroy())

    # ---------- ELIMINA FORNITORE ----------
    def _edit_fornitore(self):
        nome_corrente = self.fornitore_var.get()

        if nome_corrente not in self.fornitori:
            return

        popup = tk.Toplevel(self.root)
        popup.title("Modifica fornitore")
        popup.geometry("330x150")
        popup.resizable(False, False)
        popup.transient(self.root)
        popup.grab_set()

        # ---------- CENTRA POPUP SULLO SCHERMO ----------
        popup.update_idletasks()  # forza aggiornamento dimensioni
        width = popup.winfo_width()
        height = popup.winfo_height()
        screen_width = popup.winfo_screenwidth()
        screen_height = popup.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        popup.geometry(f"{width}x{height}+{x}+{y}")

        ttk.Label(popup, text="Nome fornitore:").pack(pady=(15, 5))

        var = tk.StringVar(value=nome_corrente)
        entry = ttk.Entry(popup, textvariable=var, width=34)
        entry.pack()
        entry.focus()

        frame = ttk.Frame(popup)
        frame.pack(pady=15)

        def conferma():
            nuovo_nome = var.get().strip().upper()

            if not nuovo_nome:
                messagebox.showerror("Errore", "Nome non valido", parent=popup)
                return

            if any(c in INVALID_CHARS for c in nuovo_nome):
                messagebox.showerror(
                    "Errore",
                    f"Caratteri non validi:\n{INVALID_CHARS}",
                    parent=popup
                )
                return

            if nuovo_nome != nome_corrente and nuovo_nome in self.fornitori:
                messagebox.showwarning(
                    "Attenzione",
                    "Fornitore già presente",
                    parent=popup
                )
                return

            # Aggiorna lista fornitori
            idx = self.fornitori.index(nome_corrente)
            self.fornitori[idx] = nuovo_nome
            self.fornitori.sort()
            self.save_fornitori(self.fornitori)

            self.fornitore_combo["values"] = self.fornitori
            self.fornitore_combo.set(nuovo_nome)

            popup.destroy()

        def elimina():
            if messagebox.askyesno(
                "Conferma eliminazione",
                f"Eliminare il fornitore:\n\n{nome_corrente} ?",
                parent=popup
            ):
                self.fornitori.remove(nome_corrente)
                self.save_fornitori(self.fornitori)
                self.fornitore_combo["values"] = self.fornitori
                self.fornitore_combo.set("Seleziona")
                popup.destroy()

        ttk.Button(frame, text="Conferma", command=conferma).grid(row=0, column=0, padx=5)
        ttk.Button(frame, text="Annulla", command=popup.destroy).grid(row=0, column=2, padx=5)
        ttk.Button(frame, text="Elimina", command=elimina).grid(row=0, column=1, padx=5)

        popup.bind("<Return>", lambda e: conferma())
        popup.bind("<Escape>", lambda e: popup.destroy())

    #---------- MENU IMPOSTAZIONI --------------
    def _open_settings(self):
        cfg = load_config()

        settings = tk.Toplevel(self.root)
        settings.title("Impostazioni")
        settings.geometry("500x300")
        settings.resizable(False, False)
        settings.transient(self.root)
        settings.grab_set()

        frame = ttk.Frame(settings, padding=15)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Percorsi", style="Header.TLabel")\
            .grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 15))

        # ---------- VARIABILI ----------
        input_var = tk.StringVar(value=cfg["INPUT_DIR"])
        dop_var = tk.StringVar(value=cfg["DOP_DIR"])
        cert_var = tk.StringVar(value=cfg["CERTIFICATI_DIR"])

        def browse(var):
            path = filedialog.askdirectory(initialdir=BASE_DIR)
            if not path:
                return

            p = Path(path)

            try:
                # se possibile, salva relativo
                rel = p.relative_to(BASE_DIR)
                var.set(rel.as_posix())
            except ValueError:
                # altrimenti salva assoluto
                var.set(str(p))

        # ---------- RIGHE ----------
        rows = [
            ("Cartella Input PDF", input_var),
            ("Cartella DOP", dop_var),
            ("Cartella Certificati", cert_var)
        ]

        for i, (label, var) in enumerate(rows, start=1):
            ttk.Label(frame, text=label).grid(row=i, column=0, sticky="w", pady=5)
            ttk.Entry(frame, textvariable=var, width=45)\
                .grid(row=i, column=1, padx=5)
            ttk.Button(frame, text="Sfoglia",
                    command=lambda v=var: browse(v))\
                .grid(row=i, column=2)

        ttk.Separator(frame).grid(row=10, column=0, columnspan=3, sticky="ew", pady=15)

        def salva():
            if not input_var.get().strip():
                messagebox.showerror("Errore", "Cartella Input non valida")
                return

            if not cert_var.get().strip():
                messagebox.showerror("Errore", "Cartella Certificati non valida")
                return

            save_config({
                "INPUT_DIR": input_var.get().strip(),
                "DOP_DIR": dop_var.get().strip(),
                "CERTIFICATI_DIR": cert_var.get().strip()
            })

            messagebox.showinfo("Riavvio necessario", "Le modifiche saranno applicate al prossimo avvio.")

        btn_frame_settings = ttk.Frame(frame)
        btn_frame_settings.grid(row=11, column=0, columnspan=3, pady=10)

        ttk.Button(btn_frame_settings, text="Salva", command=salva)\
            .pack(side="left", padx=10)

        ttk.Button(btn_frame_settings, text="Annulla", command=settings.destroy)\
            .pack(side="left", padx=10)

    # ---------- CALLBACKS FILE DIALOG ----------
    def _choose_single_pdf(self):
        path = filedialog.askopenfilename(
            initialdir=INPUT_DIR,
            filetypes=[("PDF", "*.pdf")]
        )
        if path:
            self.single_pdf_path.set(path)
            self._load_pdf_preview(path)

    def _choose_dop_file(self):
        path = filedialog.askopenfilename(
            initialdir=DOP_DIR,
            filetypes=[("PDF", "*.pdf")]
        )
        if path:
            self.dop_path.set(path)

    def _choose_generic_file(self, var):
        path = filedialog.askopenfilename(
            initialdir="DOP",  # cartella di partenza per i file DOP
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        if path:
            var.set(path)

    # ---------- GESTIONE STATO DINAMICO ----------
    def _update_import_mode(self, *args):
        if self.import_mode.get() == "single":
            self.single_pdf_entry.state(["!disabled"])
            self.single_pdf_button.state(["!disabled"])
        else:
            self.single_pdf_entry.state(["disabled"])
            self.single_pdf_button.state(["disabled"])
            self.pdf_canvas.delete("all")

    def _update_split_state(self, *args):
        if self.split_mode.get() == "custom":
            self.custom_split_entry.state(["!disabled"])
        else:
            self.custom_split_entry.state(["disabled"])

    def _update_dop_state(self, *args):
        if self.dop_var.get():
            self.dop_entry.state(["!disabled"])
            self.dop_button.state(["!disabled"])
        else:
            self.dop_entry.state(["disabled"])
            self.dop_button.state(["disabled"])

    def _update_griglia_state(self, *args):
        enabled = (
            self.dop_var.get() and
            self.split_mode.get() != "none" and
            self.import_mode.get() == "single"
        )

        state = "!disabled" if enabled else "disabled"

        for entry in self.page_entries:
            entry.state([state])

        for btn in self.griglia_buttons:
            btn.state([state])

    def _parse_griglia_dop(self, total_pages):
        """
        Ritorna un dizionario:
        { numero_pagina (int) : percorso_dop (str) }
        """
        mapping = {}

        for page_entry, dop_var in zip(self.page_entries, self.file_entries):
            pages_text = page_entry.get().strip()
            dop_path = dop_var.get().strip()

            if not pages_text or not dop_path:
                continue

            try:
                pages = [int(p.strip()) for p in pages_text.split(",")]
            except ValueError:
                raise ValueError(f"Pagine non valide: {pages_text}")

            for p in pages:
                if p < 1 or p > total_pages:
                    raise ValueError(
                        f"Pagina {p} non valida.\n"
                        f"Il PDF ha {total_pages} pagine."
                    )
                mapping[p] = dop_path

        return mapping

    # ---------------- CONVERSIONE ----------------

    def _start_conversion(self):
        if not self._validate_inputs():
            return

        self.start_button.state(["disabled"])
        self.progress["value"] = 0

        threading.Thread(
            target=self._run_worker,
            daemon=True
        ).start()

    def _run_worker(self):
        try:
            worker = ConversionWorker(progress_cb=self._on_progress)

            # ----------------- Gestione dop_map -----------------
            dop_map = None
            if (
                self.dop_var.get() and
                self.split_mode.get() != "none" and
                self.import_mode.get() == "single"
            ):
                # Leggi il PDF selezionato per sapere quante pagine ha
                pdf_path = self.single_pdf_path.get()
                if not pdf_path:
                    raise ValueError("Seleziona un PDF singolo per usare DOP per pagina")
                
                reader = PdfReader(pdf_path)
                total_pages = len(reader.pages)

                # Analizza la griglia DOP
                dop_map = self._parse_griglia_dop(total_pages)

            # ----------------- Conversione -----------------
            worker.convert(
                pdf_files=self._get_pdf_list(),
                output_dir=self._get_output_dir(),
                split_mode=self.split_mode.get(),
                custom_ranges=self.custom_split_var.get(),
                dop_active=self.dop_var.get(),
                dop_file=self.dop_path.get() or None,
                dop_map=dop_map
            )

            self.root.after(
                0,
                lambda: messagebox.showinfo("Fatto", "Conversione completata")
            )

        except Exception as e:
            self.root.after(
                0,
                partial(messagebox.showerror, "Errore", str(e))
            )
        finally:
            self.root.after(0, self._reset_ui)

    def _on_progress(self, current, total):
        self.root.after(0, lambda: self._update_progress(current, total))

    def _update_progress(self, current, total):
        self.progress["maximum"] = total
        self.progress["value"] = current

    def _reset_ui(self):
        self.start_button.state(["!disabled"])

    # ---------------- UTILS ----------------

    def _validate_inputs(self):
        if self.fornitore_var.get() == "Seleziona":
            messagebox.showerror("Errore", "Seleziona un fornitore")
            return False

        if not self.ddt_var.get().strip():
            messagebox.showerror("Errore", "Inserisci il DDT")
            return False

        return True

    def _get_pdf_list(self):
        if self.import_mode.get() == "single":
            return [self.single_pdf_path.get()]
        return [str(p) for p in INPUT_DIR.glob("*.pdf")]

    def _get_output_dir(self):
        path = CERTIFICATI_DIR / self.fornitore_var.get() / self.ddt_var.get()
        path.mkdir(parents=True, exist_ok=True)
        return path
