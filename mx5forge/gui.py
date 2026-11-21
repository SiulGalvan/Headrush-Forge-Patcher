"""Small graphical interface (tkinter, in the Python standard library)."""
import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from . import __version__, pipeline


def _open_folder(path):
    try:
        if sys.platform.startswith("win"):
            os.startfile(path)            # noqa
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except OSError:
        pass


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("HeadRush MX5 Forge %s" % __version__)
        self.minsize(660, 560)
        self.geometry("720x760")
        self.q = queue.Queue()
        self.busy = False
        self.model = tk.StringVar(value="mx5")
        self.instances = tk.IntVar(value=2)
        self.bridge = tk.BooleanVar(value=True)
        self.design = tk.BooleanVar(value=False)
        self.engine = tk.StringVar(value="nam-mod")
        self.amp = tk.BooleanVar(value=False)
        self.own_file = tk.BooleanVar(value=False)
        self.src = tk.StringVar()
        self.racks = tk.StringVar()
        self.out = tk.StringVar(value=os.path.abspath(os.path.join(os.path.expanduser("~"), "MX5Forge")))
        self._ui()
        self._sync()
        self.after(100, self._pump)

    def _ui(self):
        pad = dict(padx=10, pady=4)
        # fixed area at the bottom (button, progress, log) packed first so it always stays visible;
        # the settings above it live in a scrollable canvas
        bottom = ttk.Frame(self)
        bottom.pack(side="bottom", fill="x")
        outer = ttk.Frame(self)
        outer.pack(side="top", fill="both", expand=True)
        canvas = tk.Canvas(outer, highlightthickness=0)
        sb = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        body = ttk.Frame(canvas)
        win = canvas.create_window((0, 0), window=body, anchor="nw")
        body.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(win, width=e.width))

        def wheel(e):
            if e.widget is self.log:
                return
            canvas.yview_scroll(-1 if (getattr(e, "delta", 0) > 0 or e.num == 4) else 1, "units")
        for ev in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.bind_all(ev, wheel)
        ttk.Label(body, text="HeadRush MX5 / Pedalboard - firmware 2.7", font=("TkDefaultFont", 13, "bold")).pack(anchor="w", **pad)
        ttk.Label(body, text="Builds a patched copy of the official updater on your own computer. Nothing from "
                             "HeadRush is shipped with this tool.", wraplength=600).pack(anchor="w", **pad)

        f = ttk.LabelFrame(body, text="Device (only used when the official firmware is downloaded)")
        f.pack(fill="x", **pad)
        ttk.Radiobutton(f, text="HeadRush MX5", variable=self.model, value="mx5").pack(anchor="w", padx=8, pady=2)
        ttk.Radiobutton(f, text="HeadRush Pedalboard",
                        variable=self.model, value="pedalboard").pack(anchor="w", padx=8, pady=2)

        f = ttk.LabelFrame(body, text="NAM mod")
        f.pack(fill="x", **pad)
        ttk.Radiobutton(f, text="2 instances - Anxiety OD becomes the NAM pedal; Anxiety OD V2 and the original pedal "
                                "art stay as they are", variable=self.instances, value=2, command=self._sync).pack(anchor="w", padx=8, pady=2)
        ttk.Radiobutton(f, text="Up to 4 instances - Anxiety OD and Anxiety OD V2 both become NAM pedals "
                                "(V2 loses its original sound)", variable=self.instances, value=4, command=self._sync).pack(anchor="w", padx=8, pady=2)

        f = ttk.LabelFrame(body, text="NAM engine")
        f.pack(fill="x", **pad)
        ttk.Radiobutton(f, text="nam-mod 0.1.6 (Original NAM Mod)", variable=self.engine, value="nam-mod",
                        command=self._sync).pack(anchor="w", padx=8, pady=2)
        ttk.Radiobutton(f, text="NAM Extended (gentler background loading; tested on an MX5)", variable=self.engine,
                        value="extended", command=self._sync).pack(anchor="w", padx=8, pady=2)
        ttk.Radiobutton(f, text="NAM Extended (fair): Extended without the idle-priority background threads (experimental)", variable=self.engine,
                        value="extended-fair", command=self._sync).pack(anchor="w", padx=8, pady=2)
        self.cb_amp = ttk.Checkbutton(f, text="EXPERIMENTAL: NAM amp block (82 LEAD 800 Bright, with its own NAM picture) - Extended only",
                                      variable=self.amp)
        self.cb_amp.pack(anchor="w", padx=24, pady=2)

        f = ttk.LabelFrame(body, text="Add-ons")
        f.pack(fill="x", **pad)
        ttk.Checkbutton(f, text="MX5 Bridge (USB-MIDI bridge for MX-Edit)", variable=self.bridge).pack(anchor="w", padx=8, pady=2)
        ttk.Label(f, text="MX-Edit works while USB audio is off; USB-MIDI is switched off during USB audio "
                          "and comes back a few seconds after it ends.", wraplength=560,
                  foreground="#555").pack(anchor="w", padx=24, pady=1)
        self.cb_design = ttk.Checkbutton(f, text="Pedal design: NAM pedal art + pedal pictures in the signal chain "
                                                 "(with 2 instances Anxiety OD V2 keeps its original art)", variable=self.design, command=self._sync)
        self.cb_design.pack(anchor="w", padx=8, pady=2)
        row = ttk.Frame(f)
        row.pack(fill="x", padx=24, pady=2)
        ttk.Label(row, text="Your rack-module art (folder of PNGs, optional):").pack(anchor="w")
        r2 = ttk.Frame(row)
        r2.pack(fill="x")
        self.e_racks = ttk.Entry(r2, textvariable=self.racks)
        self.e_racks.pack(side="left", fill="x", expand=True)
        self.b_racks = ttk.Button(r2, text="Browse...", command=lambda: self._pick_dir(self.racks))
        self.b_racks.pack(side="left", padx=4)

        f = ttk.LabelFrame(body, text="Official firmware")
        f.pack(fill="x", **pad)
        ttk.Checkbutton(f, text="Use a file I already have (updater .zip/.exe, folder or Update.img) "
                                "- otherwise it is downloaded from inMusic", variable=self.own_file, command=self._sync).pack(anchor="w", padx=8, pady=2)
        r3 = ttk.Frame(f)
        r3.pack(fill="x", padx=24, pady=2)
        self.e_src = ttk.Entry(r3, textvariable=self.src)
        self.e_src.pack(side="left", fill="x", expand=True)
        self.b_src = ttk.Button(r3, text="Browse...", command=self._pick_file)
        self.b_src.pack(side="left", padx=4)

        f = ttk.LabelFrame(body, text="Output folder")
        f.pack(fill="x", **pad)
        r4 = ttk.Frame(f)
        r4.pack(fill="x", padx=8, pady=4)
        ttk.Entry(r4, textvariable=self.out).pack(side="left", fill="x", expand=True)
        ttk.Button(r4, text="Browse...", command=lambda: self._pick_dir(self.out)).pack(side="left", padx=4)

        self.btn = ttk.Button(bottom, text="Build updater", command=self._start)
        self.btn.pack(**pad)
        self.bar = ttk.Progressbar(bottom, mode="determinate", maximum=100)
        self.bar.pack(fill="x", **pad)
        self.log = tk.Text(bottom, height=8, state="disabled", wrap="word")
        self.log.pack(fill="x", **pad)
        ttk.Label(bottom, text="Unofficial. Flashing modified firmware can brick your device - at your own risk. "
                             "Recovery: hold footswitches 1 + 2 while powering on.", wraplength=600,
                  foreground="#a00").pack(anchor="w", **pad)


    def _sync(self):
        ext = self.engine.get() != "nam-mod"
        if not ext:
            self.amp.set(False)
        self.cb_amp.state(["!disabled"] if ext else ["disabled"])
        on = self.design.get()
        for w in (self.e_racks, self.b_racks):
            w.state(["!disabled"] if on else ["disabled"])
        for w in (self.e_src, self.b_src):
            w.state(["!disabled"] if self.own_file.get() else ["disabled"])

    def _pick_dir(self, var):
        d = filedialog.askdirectory(initialdir=var.get() or None)
        if d:
            var.set(d)

    def _pick_file(self):
        f = filedialog.askopenfilename(filetypes=[("Firmware", "*.img *.zip *.exe"), ("All files", "*.*")])
        if f:
            self.src.set(f)

    def _say(self, text):
        self.q.put(("log", text))

    def _progress(self, got, total):
        self.q.put(("bar", got * 100 // max(total, 1)))

    def _start(self):
        if self.busy:
            return
        o = pipeline.Options(self.instances.get(), self.bridge.get(), self.design.get(), self.racks.get() or None,
                             self.src.get() or None if self.own_file.get() else None, self.out.get(),
                             self._say, self._progress, engine=self.engine.get(), amp=self.amp.get(),
                                model=self.model.get())
        if self.own_file.get() and not o.source:
            messagebox.showerror("MX5 Forge", "Choose the firmware file.")
            return
        os.makedirs(o.out_parent, exist_ok=True)
        self.busy = True
        self.btn.state(["disabled"])
        self.bar.configure(mode="indeterminate")
        self.bar.start(15)
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")
        threading.Thread(target=self._work, args=(o,), daemon=True).start()

    def _work(self, o):
        try:
            out, missing = pipeline.build(o)
            self.q.put(("done", (o, out, missing)))
        except pipeline.ERRORS as e:
            self.q.put(("fail", str(e)))
        except Exception as e:           # noqa: unexpected - show it, do not hang the window
            self.q.put(("fail", "%s: %s" % (type(e).__name__, e)))

    def _finish(self):
        self.busy = False
        self.bar.stop()
        self.bar.configure(mode="determinate", value=0)
        self.btn.state(["!disabled"])

    def _pump(self):
        try:
            while True:
                kind, val = self.q.get_nowait()
                if kind == "log":
                    self.log.configure(state="normal")
                    self.log.insert("end", val + "\n")
                    self.log.see("end")
                    self.log.configure(state="disabled")
                elif kind == "bar":
                    self.bar.stop()
                    self.bar.configure(mode="determinate", value=val)
                elif kind == "fail":
                    self._finish()
                    self._say("\nERROR: " + val)
                    messagebox.showerror("MX5 Forge", val)
                elif kind == "done":
                    o, out, missing = val
                    self._finish()
                    self._say("\nDone: %s\n\n%s" % (out, pipeline.hint(o, out)))
                    if missing:
                        self._say("Copy these files from the official updater into that folder: " + ", ".join(missing))
                    if messagebox.askyesno("MX5 Forge", "Updater ready.\n\nOpen the output folder?"):
                        _open_folder(out)
        except queue.Empty:
            pass
        self.after(100, self._pump)


def main():
    App().mainloop()
    return 0
