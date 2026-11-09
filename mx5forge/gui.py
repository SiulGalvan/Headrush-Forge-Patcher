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
        self.minsize(640, 640)
        self.q = queue.Queue()
        self.busy = False
        self.instances = tk.IntVar(value=2)
        self.bridge = tk.BooleanVar(value=True)
        self.design = tk.BooleanVar(value=False)
        self.own_file = tk.BooleanVar(value=False)
        self.src = tk.StringVar()
        self.racks = tk.StringVar()
        self.out = tk.StringVar(value=os.path.abspath(os.path.join(os.path.expanduser("~"), "MX5Forge")))
        self._ui()
        self._sync()
        self.after(100, self._pump)

    def _ui(self):
        pad = dict(padx=10, pady=4)
        ttk.Label(self, text="HeadRush MX5 - firmware 2.7", font=("TkDefaultFont", 13, "bold")).pack(anchor="w", **pad)
        ttk.Label(self, text="Builds a patched copy of the official updater on your own computer. Nothing from "
                             "HeadRush is shipped with this tool.", wraplength=600).pack(anchor="w", **pad)

        f = ttk.LabelFrame(self, text="NAM mod")
        f.pack(fill="x", **pad)
        ttk.Radiobutton(f, text="2 instances - Anxiety OD becomes the NAM pedal; Anxiety OD V2 and the original pedal "
                                "art stay as they are", variable=self.instances, value=2, command=self._sync).pack(anchor="w", padx=8, pady=2)
        ttk.Radiobutton(f, text="Up to 4 instances - Anxiety OD and Anxiety OD V2 both become NAM pedals "
                                "(V2 loses its original sound)", variable=self.instances, value=4, command=self._sync).pack(anchor="w", padx=8, pady=2)

        f = ttk.LabelFrame(self, text="Add-ons")
        f.pack(fill="x", **pad)
        ttk.Checkbutton(f, text="MX5 Bridge (USB-MIDI bridge for MX-Edit)", variable=self.bridge).pack(anchor="w", padx=8, pady=2)
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

        f = ttk.LabelFrame(self, text="Official firmware")
        f.pack(fill="x", **pad)
        ttk.Checkbutton(f, text="Use a file I already have (updater .zip/.exe, folder or Update.img) "
                                "- otherwise it is downloaded from inMusic", variable=self.own_file, command=self._sync).pack(anchor="w", padx=8, pady=2)
        r3 = ttk.Frame(f)
        r3.pack(fill="x", padx=24, pady=2)
        self.e_src = ttk.Entry(r3, textvariable=self.src)
        self.e_src.pack(side="left", fill="x", expand=True)
        self.b_src = ttk.Button(r3, text="Browse...", command=self._pick_file)
        self.b_src.pack(side="left", padx=4)

        f = ttk.LabelFrame(self, text="Output folder")
        f.pack(fill="x", **pad)
        r4 = ttk.Frame(f)
        r4.pack(fill="x", padx=8, pady=4)
        ttk.Entry(r4, textvariable=self.out).pack(side="left", fill="x", expand=True)
        ttk.Button(r4, text="Browse...", command=lambda: self._pick_dir(self.out)).pack(side="left", padx=4)

        self.btn = ttk.Button(self, text="Build updater", command=self._start)
        self.btn.pack(**pad)
        self.bar = ttk.Progressbar(self, mode="determinate", maximum=100)
        self.bar.pack(fill="x", **pad)
        self.log = tk.Text(self, height=12, state="disabled", wrap="word")
        self.log.pack(fill="both", expand=True, **pad)
        ttk.Label(self, text="Unofficial. Flashing modified firmware can brick your device - at your own risk. "
                             "Recovery: hold footswitches 1 + 2 while powering on.", wraplength=600,
                  foreground="#a00").pack(anchor="w", **pad)

    def _sync(self):
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
                             self._say, self._progress)
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
