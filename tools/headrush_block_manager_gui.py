#!/usr/bin/env python3
"""HeadRush NAM Block Manager -- GUI (Windows).

Scans the NAM folder of the pedal's USB drive and writes one touch-screen "block" preset per model
(Anxiety OD, Anxiety OD V2, 82 LEAD 800 Bright) with the real model name, so the knob position (Drive 0..100)
selects the model.  Version 2.1 adds an optional step that makes the .nam files smaller (see nam_minify.py):
the same float32 weights written with the shortest text, which the pedal parses faster.

Rebuilt from the 2.0 executable; behaviour of the original screens and of the block files is unchanged.
Standard library only (nam_minify.py must sit next to this file).
"""
import json
import os
import re
import shutil
import string
import sys
import uuid
from pathlib import Path

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nam_minify  # noqa: E402

try:  # crisp text on Windows high-DPI screens
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

APP_TITLE = "HeadRush NAM Block Manager"
APP_VERSION = "2.1 (Win11 Edition)"
BACKUP_FOLDER = "NAM_originales"          # next to NAM/, so the pedal never scans it as models

AMP_CHILD_ORDER = ["TremSync", "DoubleStates", "Type", "Bright", "Treble", "Mid", "MidFreq", "Bass", "Presence",
                   "GainA", "GainB", "TremSpeed", "TremDepth", "Master", "Tremolo"]


def amp_block(idx):
    """Block content of the 82 LEAD 800 Bright amp preset; TremDepth carries the model index."""
    def knob(v):
        return {"type": 0, "value": v}

    def sw(on=False):
        return {"state": on, "type": 1}

    children = {
        "Bass": knob(50), "Bright": sw(), "DoubleStates": {"state": False, "type": 3},
        "GainA": knob(50), "GainB": knob(50), "Master": knob(50), "Mid": knob(50), "MidFreq": knob(1610),
        "Presence": knob(50), "Treble": knob(50), "TremDepth": knob(idx), "TremSpeed": knob(6),
        "TremSync": sw(), "Tremolo": sw(), "Type": {"string": "82 LEAD 800 Bright", "type": 4},
    }
    return {"data": {"Amp": {"childorder": list(AMP_CHILD_ORDER), "children": children}},
            "info": {"version": "1.0.9"}}


def pedal_block(target_key, idx, level, tone):
    """Block content of an Anxiety OD preset; Drive carries the model index."""
    return {"data": {target_key: {"childorder": ["Level", "Drive", "Tone", "Hi-Lo"], "children": {
        "Drive": {"type": 0, "value": idx}, "Hi-Lo": {"state": False, "type": 1},
        "Level": {"type": 0, "value": level}, "Tone": {"type": 0, "value": tone}}}},
        "info": {"version": "1.0.9"}}


def clean_model_name(stem):
    return re.sub(r"^\d+\s*[-_.]\s*", "", stem)


class HeadRushBlockManager(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_TITLE} v{APP_VERSION}")
        self.geometry("860x800")
        self.minsize(780, 660)
        self.bg_color = "#18181b"
        self.card_bg = "#27272a"
        self.card_border = "#3f3f46"
        self.fg_color = "#f4f4f5"
        self.fg_muted = "#a1a1aa"
        self.accent_color = "#0284c7"
        self.accent_hover = "#0369a1"
        self.success_color = "#10b981"
        self.warning_color = "#f59e0b"
        self.configure(bg=self.bg_color)
        self.setup_styles()
        self.detected_models = []
        self.current_drive = tk.StringVar(value="")
        self.custom_nam_path = tk.StringVar(value="")
        self.custom_blocks_path = tk.StringVar(value="")
        self.opt_anxiety1 = tk.BooleanVar(value=True)
        self.opt_anxiety2 = tk.BooleanVar(value=True)
        self.opt_amp = tk.BooleanVar(value=True)
        self.opt_clean_old = tk.BooleanVar(value=True)
        self.opt_backup = tk.BooleanVar(value=True)
        self.opt_prefix_idx = tk.BooleanVar(value=True)
        self.opt_minify = tk.BooleanVar(value=True)
        self.opt_minify_backup = tk.BooleanVar(value=True)
        self.val_level = tk.IntVar(value=50)
        self.val_tone = tk.IntVar(value=50)
        self.build_ui()
        self.detect_headrush_drives()

    # ------------------------------------------------------------------ look
    def setup_styles(self):
        self.style = ttk.Style(self)
        self.style.theme_use("clam")
        self.style.configure(".", background=self.bg_color, foreground=self.fg_color, font=("Segoe UI", 10))
        self.style.configure("TFrame", background=self.bg_color)
        self.style.configure("Card.TFrame", background=self.card_bg, relief="flat")
        self.style.configure("TLabel", background=self.bg_color, foreground=self.fg_color, font=("Segoe UI", 10))
        self.style.configure("Card.TLabel", background=self.card_bg, foreground=self.fg_color, font=("Segoe UI", 10))
        self.style.configure("Muted.TLabel", background=self.card_bg, foreground=self.fg_muted, font=("Segoe UI", 9))
        self.style.configure("Title.TLabel", background=self.bg_color, foreground="#38bdf8", font=("Segoe UI", 16, "bold"))
        self.style.configure("CardHeader.TLabel", background=self.card_bg, foreground="#38bdf8",
                             font=("Segoe UI", 11, "bold"))
        self.style.configure("TCombobox", fieldbackground="#3f3f46", background="#3f3f46", foreground="#ffffff")
        self.style.map("TCombobox", fieldbackground=[("readonly", "#3f3f46")], foreground=[("readonly", "#ffffff")])
        self.style.configure("TCheckbutton", background=self.card_bg, foreground=self.fg_color, font=("Segoe UI", 10))
        self.style.map("TCheckbutton", background=[("active", self.card_bg)])
        self.style.configure("Treeview", background="#1e1e24", foreground="#f4f4f5", fieldbackground="#1e1e24",
                             rowheight=26, font=("Segoe UI", 9))
        self.style.configure("Treeview.Heading", background="#33333d", foreground="#38bdf8", relief="flat",
                             font=("Segoe UI", 9, "bold"))
        self.style.map("Treeview", background=[("selected", self.accent_color)], foreground=[("selected", "#ffffff")])
        self.style.configure("Horizontal.TProgressbar", background="#0ea5e9", troughcolor="#27272a")

    def _button(self, parent, text, command, primary=False):
        if primary:
            return tk.Button(parent, text=text, bg="#0284c7", fg="#ffffff", activebackground="#0369a1",
                             activeforeground="#ffffff", relief="flat", font=("Segoe UI", 11, "bold"),
                             command=command, padx=20, pady=8, cursor="hand2")
        return tk.Button(parent, text=text, bg="#3f3f46", fg="#ffffff", activebackground="#52525b",
                         activeforeground="#ffffff", relief="flat", font=("Segoe UI", 9), command=command,
                         padx=8, pady=2)

    def _card(self, expand=False):
        card = ttk.Frame(self, style="Card.TFrame", padding=12)
        if expand:
            card.pack(fill="both", expand=True, padx=20, pady=6)
        else:
            card.pack(fill="x", padx=20, pady=6)
        head = ttk.Frame(card, style="Card.TFrame")
        head.pack(fill="x", pady=(0, 6))
        return card, head

    def build_ui(self):
        header = ttk.Frame(self)
        header.pack(fill="x", padx=20, pady=(15, 10))
        ttk.Label(header, text="⚡ HeadRush NAM Block Manager", style="Title.TLabel").pack(anchor="w")
        ttk.Label(header, text="Sincronizador inteligente de perfiles NAM a Presets de Bloque táctiles con nombre real",
                  foreground=self.fg_muted).pack(anchor="w")

        # 1. drive
        card, head = self._card()
        ttk.Label(head, text="1. Unidad HeadRush / Rutas de Almacenamiento", style="CardHeader.TLabel").pack(side="left")
        row = ttk.Frame(card, style="Card.TFrame")
        row.pack(fill="x", pady=4)
        ttk.Label(row, text="Unidad detectada:", style="Card.TLabel").pack(side="left", padx=(0, 8))
        self.drive_combo = ttk.Combobox(row, textvariable=self.current_drive, state="readonly", width=35)
        self.drive_combo.pack(side="left", padx=(0, 8))
        self.drive_combo.bind("<<ComboboxSelected>>", lambda e: self.on_drive_selected())
        self._button(row, "🔄 Re-escanear Unidades", self.detect_headrush_drives).pack(side="left", padx=4)
        self._button(row, "📁 Elegir Carpeta Manual...", self.browse_custom_folder).pack(side="left", padx=4)
        self.path_info_lbl = ttk.Label(card, text="Buscando unidad HeadRush...", style="Muted.TLabel")
        self.path_info_lbl.pack(anchor="w", pady=(4, 0))

        # 2. models
        card, head = self._card(expand=True)
        ttk.Label(head, text="2. Modelos NAM Detectados", style="CardHeader.TLabel").pack(side="left")
        self.models_count_lbl = ttk.Label(head, text="0 modelos", style="Muted.TLabel")
        self.models_count_lbl.pack(side="right")
        self._button(head, "🗜 Solo optimizar .nam", self.optimize_only).pack(side="right", padx=(0, 12))
        tree_frame = ttk.Frame(card, style="Card.TFrame")
        tree_frame.pack(fill="both", expand=True)
        columns = ("idx", "knob", "name", "filesize")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=8)
        self.tree.heading("idx", text="#")
        self.tree.heading("knob", text="Paso Drive")
        self.tree.heading("name", text="Nombre del Modelo / Preset")
        self.tree.heading("filesize", text="Tamaño")
        self.tree.column("idx", width=45, anchor="center")
        self.tree.column("knob", width=80, anchor="center")
        self.tree.column("name", width=450, anchor="w")
        self.tree.column("filesize", width=90, anchor="e")
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 3. options
        card, head = self._card()
        ttk.Label(head, text="3. Opciones de Sincronización", style="CardHeader.TLabel").pack(side="left")
        row = ttk.Frame(card, style="Card.TFrame")
        row.pack(fill="x", pady=2)
        for text, var in (("Generar para ANXIETY OD", self.opt_anxiety1),
                          ("Generar para ANXIETY OD V2", self.opt_anxiety2),
                          ("Generar para 82 LEAD 800 (NAM)", self.opt_amp),
                          ("Limpiar bloques obsoletos en HeadRush", self.opt_clean_old)):
            ttk.Checkbutton(row, text=text, variable=var).pack(side="left", padx=(0, 15))
        ttk.Checkbutton(row, text="Hacer copia de seguridad previa", variable=self.opt_backup).pack(side="left")
        row2 = ttk.Frame(card, style="Card.TFrame")
        row2.pack(fill="x", pady=(6, 2))
        ttk.Checkbutton(row2, text="Optimizar archivos .nam (más pequeños, carga más rápida)",
                        variable=self.opt_minify).pack(side="left", padx=(0, 15))
        ttk.Checkbutton(row2, text="Guardar los originales en " + BACKUP_FOLDER + "\\",
                        variable=self.opt_minify_backup).pack(side="left")
        ttk.Label(card, text="Optimizar reescribe cada .nam con los mismos pesos float32 en el texto más corto: "
                             "el sonido es idéntico y el pedal los interpreta antes. Los nombres no cambian.",
                  style="Muted.TLabel", wraplength=780).pack(anchor="w", pady=(4, 0))

        # action
        action = ttk.Frame(self)
        action.pack(fill="x", padx=20, pady=(6, 15))
        self.progress = ttk.Progressbar(action, orient="horizontal", mode="determinate",
                                        style="Horizontal.TProgressbar")
        self.progress.pack(fill="x", pady=(0, 8))
        btn_row = ttk.Frame(action)
        btn_row.pack(fill="x")
        self.status_lbl = ttk.Label(btn_row, text="Listo para sincronizar.", foreground=self.fg_muted)
        self.status_lbl.pack(side="left", anchor="w")
        self.sync_btn = self._button(btn_row, "⚡ SINCRONIZAR BLOQUES EN HEADRUSH", self.run_synchronization,
                                     primary=True)
        self.sync_btn.pack(side="right")

    # ---------------------------------------------------------------- drives
    def get_available_drives(self):
        drives = []
        try:
            bitmask = ctypes.windll.kernel32.GetLogicalDrives()
            for letter in string.ascii_uppercase:
                if bitmask & 1:
                    drives.append(f"{letter}:\\")
                bitmask >>= 1
        except Exception:
            pass
        return drives

    def detect_headrush_drives(self):
        drives = self.get_available_drives()
        options = []
        default_choice = ""
        for d in drives:
            try:
                has_nam = (Path(d) / "NAM").is_dir()
                has_blocks = (Path(d) / "Blocks").is_dir()
                label = d
                if has_nam and has_blocks:
                    label = f"{d} (HeadRush Gigboard detectada ★)"
                    if not default_choice or d.upper().startswith("D:"):
                        default_choice = label
                elif d.upper().startswith("D:"):
                    label = f"{d} (Unidad D:)"
                    if not default_choice:
                        default_choice = label
                options.append((label, d))
            except Exception:
                continue
        if not options:
            options = [("D:\\ (Unidad D por defecto)", "D:\\")]
            default_choice = options[0][0]
        self.drive_options = options
        self.drive_combo["values"] = [opt[0] for opt in options]
        if default_choice:
            self.drive_combo.set(default_choice)
        elif options:
            self.drive_combo.set(options[0][0])
        self.on_drive_selected()

    def get_selected_drive_root(self):
        sel = self.drive_combo.get()
        for label, root in self.drive_options:
            if label == sel:
                return root
        if len(sel) >= 2 and sel[1] == ":":
            return sel[:3]
        return "D:\\"

    def browse_custom_folder(self):
        folder = filedialog.askdirectory(title="Selecciona la carpeta raíz de tu HeadRush o carpeta con archivos NAM")
        if not folder:
            return
        path = Path(folder)
        root = str(path.parent) if path.name.upper() == "NAM" else str(path)
        custom_label = f"{root} (Carpeta seleccionada)"
        self.drive_options.insert(0, (custom_label, root))
        self.drive_combo["values"] = [opt[0] for opt in self.drive_options]
        self.drive_combo.set(custom_label)
        self.on_drive_selected()

    def on_drive_selected(self):
        root = Path(self.get_selected_drive_root())
        nam_dir = root / "NAM"
        blocks_dir = root / "Blocks"
        status_text = []
        if nam_dir.is_dir():
            status_text.append(f"✓ Carpeta NAM: {nam_dir}")
        else:
            status_text.append(f"⚠ Carpeta NAM no encontrada en {nam_dir} (puedes crearla o elegir otra carpeta)")
        if blocks_dir.is_dir():
            status_text.append(f"✓ Carpeta Blocks: {blocks_dir}")
        else:
            status_text.append(f"• Carpeta Blocks se creará automáticamente en {blocks_dir}")
        self.path_info_lbl.config(text="  |  ".join(status_text))
        self.scan_models(nam_dir)

    # ---------------------------------------------------------------- models
    def scan_models(self, nam_dir: Path):
        self.detected_models.clear()
        for row in self.tree.get_children():
            self.tree.delete(row)
        if not nam_dir.is_dir():
            self.models_count_lbl.config(text="0 modelos (carpeta no encontrada)", foreground=self.warning_color)
            return
        files = []
        try:
            for item in nam_dir.iterdir():
                if not item.is_file():
                    continue
                name = item.name
                if name.startswith("._") or name.startswith("."):
                    continue
                if item.suffix.lower() not in (".nam", ".nam2"):
                    continue
                files.append(item)
        except Exception as e:
            self.models_count_lbl.config(text=f"Error al leer: {e}", foreground=self.warning_color)
            return
        files.sort(key=lambda p: p.name)
        self.detected_models = files
        count = len(files)
        if count == 0:
            self.models_count_lbl.config(text="0 modelos encontrados en D:\\NAM", foreground=self.warning_color)
            self.status_lbl.config(text="Copia tus archivos .nam en la carpeta NAM de la Gigboard.")
        elif count <= 101:
            self.models_count_lbl.config(text=f"{count} modelos encontrados (todos caben en Drive 0%..{count - 1}%)",
                                         foreground=self.success_color)
            self.status_lbl.config(text=f"{count} modelos listos para sincronizar.")
        else:
            self.models_count_lbl.config(text=f"{count} modelos (Atención: los primeros 101 cubrirán 0%..100%)",
                                         foreground=self.warning_color)
            self.status_lbl.config(text=f"Atención: {count} archivos. Los primeros 101 se asignarán a Drive 0%..100%.")
        for idx, fpath in enumerate(files):
            clean_name = clean_model_name(fpath.stem)
            display_name = f"{idx:03d} - {clean_name}" if self.opt_prefix_idx.get() else clean_name
            knob_str = f"{idx}%" if idx <= 100 else "Fuera de rango (>100%)"
            size_kb = f"{fpath.stat().st_size / 1024:.1f} KB"
            tag = "warn" if idx > 100 else "ok"
            self.tree.insert("", "end", values=(f"{idx:03d}", knob_str, display_name, size_kb), tags=(tag,))
        self.tree.tag_configure("warn", foreground="#f87171")
        self.tree.tag_configure("ok", foreground="#f4f4f5")

    # -------------------------------------------------------------- optimize
    def _nam_only(self):
        return [str(p) for p in self.detected_models if p.suffix.lower() == ".nam"]

    def optimize_models(self, root, use_backup):
        """Minify the detected .nam files in place; updates the progress bar. Returns nam_minify's stats."""
        files = self._nam_only()
        backup_dir = str(Path(root) / BACKUP_FOLDER) if use_backup else None

        def progress(i, total, name):
            self.progress["value"] = 100.0 * i / max(1, total)
            if name:
                self.status_lbl.config(text=f"Optimizando: {name} ({i + 1}/{total})...", foreground=self.fg_muted)
            self.update_idletasks()

        return nam_minify.optimize_files(files, backup_dir, progress)

    @staticmethod
    def _optimize_summary(r, use_backup, root):
        mb = lambda n: f"{n / 1e6:.2f} MB"
        text = f"• Modelos optimizados: {r['changed']} ({mb(r['before'])} → {mb(r['after'])})"
        if r["changed"] and use_backup:
            text += f"\n• Originales guardados en {Path(root) / BACKUP_FOLDER}"
        if r["skipped"]:
            text += f"\n• Sin cambios: {r['skipped']}"
            for n, why in r["skipped_info"][:8]:
                text += f"\n   - {n}: {why}"
        if r["errors"]:
            text += "\n• No se pudieron optimizar (se dejaron como estaban):\n" + "\n".join(
                f"   - {n}: {m}" for n, m in r["errors"][:8])
        return text

    def optimize_only(self):
        if not self._nam_only():
            messagebox.showwarning("Sin Modelos", "No hay archivos .nam en la carpeta seleccionada.")
            return
        root = self.get_selected_drive_root()
        use_backup = self.opt_minify_backup.get()
        if not messagebox.askyesno("Optimizar modelos",
                                   f"Se reescribirán {len(self._nam_only())} archivos .nam con el mismo sonido y menor tamaño."
                                   + ("\nLos originales se guardarán en " + str(Path(root) / BACKUP_FOLDER) + "." if use_backup
                                      else "\nNo se guardará copia de los originales.") + "\n\n¿Continuar?"):
            return
        self.sync_btn.config(state="disabled")
        try:
            r = self.optimize_models(root, use_backup)
            self.progress["value"] = 100
            self.status_lbl.config(text="Optimización completada.", foreground=self.success_color)
            messagebox.showinfo("Optimización completada", self._optimize_summary(r, use_backup, root))
            self.on_drive_selected()
        except Exception as e:
            messagebox.showerror("Error", f"Ocurrió un error durante la optimización:\n{e}")
            self.status_lbl.config(text=f"Error: {e}", foreground=self.warning_color)
        finally:
            self.sync_btn.config(state="normal")

    # ------------------------------------------------------------------ sync
    def run_synchronization(self):
        if not self.detected_models:
            messagebox.showwarning("Sin Modelos", "No hay archivos .nam en la carpeta seleccionada.\n\n"
                                   "Asegúrate de conectar la Gigboard en modo USB Transfer y que existan archivos .nam "
                                   "en la carpeta NAM.")
            return
        root = Path(self.get_selected_drive_root())
        blocks_dir = root / "Blocks"
        targets = []
        if self.opt_anxiety1.get():
            targets.append(("ANXIETY OD", "Anxiety OD", "pedal"))
        if self.opt_anxiety2.get():
            targets.append(("ANXIETY OD V2", "Anxiety OD V2", "pedal"))
        if self.opt_amp.get():
            targets.append(("AMP", "82 LEAD 800 Bright", "amp"))
        if not targets:
            messagebox.showwarning("Sin Destino", "Debes seleccionar al menos un tipo de bloque "
                                   "(Anxiety OD, Anxiety OD V2 o 82 LEAD 800).")
            return
        confirm_msg = f"Se van a sincronizar {len(self.detected_models)} modelos en:\n"
        for t_folder, _t_key, _kind in targets:
            confirm_msg += f"  - {blocks_dir / t_folder}\n"
        if self.opt_clean_old.get():
            confirm_msg += "\nSe eliminarán presets obsoletos para evitar desajustes con los archivos eliminados."
        if self.opt_backup.get():
            confirm_msg += "\nSe creará una copia de seguridad automática antes de limpiar."
        if self.opt_minify.get() and self._nam_only():
            confirm_msg += f"\nSe optimizarán los {len(self._nam_only())} archivos .nam (mismo sonido, menor tamaño)."
            if self.opt_minify_backup.get():
                confirm_msg += f"\nOriginales en {root / BACKUP_FOLDER}."
        confirm_msg += "\n\n¿Deseas continuar?"
        if not messagebox.askyesno("Confirmar Sincronización", confirm_msg):
            return

        self.sync_btn.config(state="disabled")
        self.progress["value"] = 0
        optimize_text = ""
        try:
            if self.opt_minify.get() and self._nam_only():
                r = self.optimize_models(root, self.opt_minify_backup.get())
                optimize_text = self._optimize_summary(r, self.opt_minify_backup.get(), root) + "\n"
                self.progress["value"] = 0
            total_steps = len(targets) * min(len(self.detected_models), 101)
            step = 0
            created_count = 0
            backup_created = False
            for t_folder, target_key, kind in targets:
                dest = blocks_dir / t_folder
                dest.mkdir(parents=True, exist_ok=True)
                if self.opt_backup.get() and dest.exists():
                    existing_blocks = list(dest.glob("*.block"))
                    if existing_blocks:
                        backup_dir = blocks_dir / f"_backup_{t_folder}"
                        backup_dir.mkdir(parents=True, exist_ok=True)
                        for b in existing_blocks:
                            try:
                                shutil.copy2(b, backup_dir / b.name)
                            except Exception:
                                pass
                        backup_created = True
                if self.opt_clean_old.get() and dest.exists():
                    for old_b in dest.glob("*.block"):
                        try:
                            old_b.unlink()
                        except Exception:
                            pass
                for idx, fpath in enumerate(self.detected_models):
                    if idx > 100:
                        break
                    clean_name = clean_model_name(fpath.stem)
                    block_filename = f"{idx:03d} - {clean_name}.block"
                    block_path = dest / block_filename
                    if kind == "amp":
                        inner_dict = amp_block(idx)
                    else:
                        inner_dict = pedal_block(target_key, idx, self.val_level.get(), self.val_tone.get())
                    outer_dict = {"content": json.dumps(inner_dict, separators=(",", ":")),
                                  "id": str(uuid.uuid4()), "readonly": False, "type": t_folder}
                    with open(block_path, "w", encoding="utf-8") as out_f:
                        json.dump(outer_dict, out_f, indent=2)
                    created_count += 1
                    step += 1
                    self.progress["value"] = (step / total_steps) * 100
                    self.status_lbl.config(text=f"Generando: {block_filename}...")
                    self.update_idletasks()
            self.status_lbl.config(text="¡Sincronización completada con éxito!", foreground=self.success_color)
            self.progress["value"] = 100
            success_text = "¡Operación finalizada con éxito!\n\n"
            success_text += f"• Se generaron {created_count} archivos de bloque en HeadRush.\n"
            if backup_created:
                success_text += f"• Se creó copia de seguridad en {blocks_dir / '_backup_*'}\n"
            success_text += optimize_text
            success_text += ("\nYa puedes expulsar con seguridad el USB desde Windows y usar tus amplificadores por su "
                             "nombre real en la Gigboard.")
            messagebox.showinfo("Completado", success_text)
            if optimize_text:
                self.on_drive_selected()            # sizes changed: refresh the list
        except Exception as e:
            messagebox.showerror("Error", f"Ocurrió un error durante la sincronización:\n{e}")
            self.status_lbl.config(text=f"Error: {e}", foreground=self.warning_color)
        finally:
            self.sync_btn.config(state="normal")


if __name__ == "__main__":
    app = HeadRushBlockManager()
    app.mainloop()
