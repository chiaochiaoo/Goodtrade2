import os
import json
import tkinter as tk
import ttkbootstrap as tb
from ttkbootstrap.constants import *

ACTIVE = 0
MULTIPLIER = 1
PASSIVE = 2
DESCRIPTION = 3

class authorization:
    def __init__(self, ui):
        self.ui = ui
        self.TNV_TAB = tb.Notebook(self.ui.auth_panel)
        self.TNV_TAB.place(relx=0.01, rely=0.01, relheight=0.97, relwidth=0.97)

        self.frames = {}
        self.algo_groups = []
        self.algos = {}

        self.load_algo_tabs()
        self.create_algo_tabs()
        self.create_each_algos()
        self.load_all()

        # Inject these into main UI so save/load calls still work
        self.ui.algo_groups = self.algo_groups
        self.ui.algos = self.algos
        self.ui.save_all = self.save_all
        self.ui.load_all = self.load_all

    def load_algo_tabs(self):
        dir_name = "custom_algos"
        directory = os.fsencode(dir_name)
        for file in os.listdir(directory):
            filename = os.fsdecode(file)
            if filename.endswith(".txt"):
                strategy = filename[:-4]
                self.algo_groups.append(strategy)
                self.algos[strategy] = {}
                with open(os.path.join(dir_name, filename)) as f:
                    lines = f.read().splitlines()
                for line in lines:
                    if ":" in line:
                        key, description = line.split(":", 1)
                    else:
                        key, description = line, ""
                    self.algos[strategy][key] = [
                        tk.BooleanVar(value=0),
                        tk.IntVar(value=1),
                        tk.BooleanVar(value=0),
                        tk.StringVar(value=description),
                    ]

    def create_algo_tabs(self):
        for strategy in self.algo_groups:
            self.frames[strategy] = tk.Frame(self.TNV_TAB)
            self.TNV_TAB.add(self.frames[strategy], text=strategy)

    def create_each_algos(self):
        for strategy in self.algo_groups:
            frame = self.frames[strategy]
            row = 1
            col = 0
            for algo, item in self.algos[strategy].items():
                label = tb.Label(frame, text=algo, cursor="hand2")
                label.grid(sticky="w", column=col, row=row)

                def toggle(var=item[ACTIVE]):
                    var.set(0 if var.get() else 1)

                label.bind("<Button-1>", lambda e, var=item[ACTIVE]: toggle(var))

                tb.Checkbutton(frame, variable=item[ACTIVE]).grid(sticky="w", column=col + 1, row=row)
                tb.Label(frame, text="Multiplier:").grid(sticky="w", column=col + 2, row=row)
                tb.Entry(frame, textvariable=item[MULTIPLIER], width=3).grid(sticky="w", column=col + 3, row=row)
                tb.Label(frame, text="Aggressive:").grid(sticky="w", column=col + 4, row=row)
                tb.Checkbutton(frame, variable=item[PASSIVE]).grid(sticky="w", column=col + 5, row=row)
                row += 1
            tb.Button(frame, text="Save Config", command=self.save_all).grid(sticky="w", column=col, row=row)
            tb.Button(frame, text="Revert Config", command=self.load_all).grid(sticky="w", column=col + 2, row=row)

    def save_all(self):
        for tab in self.algo_groups:
            try:
                d = {}
                for algo, item in self.algos[tab].items():
                    d[algo] = [v.get() for v in item]
                with open(f'custom_algos_config/{tab}_setting.json', 'w') as fp:
                    json.dump(d, fp)
            except Exception as e:
                print(f"Saving error in {tab}:", e)

    def load_all(self):
        for tab in self.algo_groups:
            try:
                with open(f'custom_algos_config/{tab}_setting.json', 'r') as myfile:
                    d = json.load(myfile)
                for key, item in d.items():
                    try:
                        self.algos[tab][key][ACTIVE].set(item[ACTIVE])
                        self.algos[tab][key][PASSIVE].set(item[PASSIVE])
                        self.algos[tab][key][MULTIPLIER].set(item[MULTIPLIER])
                    except Exception as e:
                        print(f"Loading error for {key} in {tab}:", e)
            except Exception as e:
                print(f"Loading config failed for {tab}:", e)
