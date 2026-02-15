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

		self.pannel_name = 'Authorization'
		# Ensure dashboard_panel exists
		if not hasattr(self.ui, 'user_panels'):

			self.ui.user_panel = tb.LabelFrame(self.ui, text="User", bootstyle="info")
			self.ui.user_panel.place(relx=0, rely=0, relheight=1, relwidth=1)
			self.ui.user_panels = tb.Notebook(self.ui.user_panel)
			self.ui.user_panels.place(relx=0, rely=0, relheight=1, relwidth=1)

			# frame = tb.Frame(self.tab)
			# self.frames[name] = frame
			# self.tab.add(frame, text=name)

		self.ui.auth_panel = tb.Frame(self.ui.user_panels)
		self.ui.user_panels.add(self.ui.auth_panel, text=self.pannel_name)

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
			# --- Outer scrollable container ---
			outer = tb.Frame(self.TNV_TAB, padding=0)
			self.TNV_TAB.add(outer, text=strategy)

			# Canvas + Scrollbar
			canvas = tk.Canvas(
				outer,
				highlightthickness=0,
				bd=0,
			)
			vscroll = tb.Scrollbar(outer, orient="vertical", command=canvas.yview)
			canvas.configure(yscrollcommand=vscroll.set)

			# Inner scrollable frame
			scroll_frame = tb.Frame(canvas, padding=(4, 2))
			scroll_frame.bind(
				"<Configure>",
				lambda e, c=canvas: c.configure(scrollregion=c.bbox("all")),
			)

			# canvas.create_window((0, 0), window=scroll_frame, anchor="nw")

			# canvas.pack(side="left", fill="both", expand=True)
			# vscroll.pack(side="right", fill="y")
			canvas.create_window((0, 0), window=scroll_frame, anchor="nw")

			# --- 💡 修复：首先打包滚动条以保留空间 ---
			vscroll.pack(side="right", fill="y")  # <-- 这一行上移
			canvas.pack(side="left", fill="both", expand=True)
			# Mouse wheel scrolling
			scroll_frame.bind(
				"<Enter>",
				lambda e, c=canvas: c.bind_all(
					"<MouseWheel>", lambda ev: c.yview_scroll(int(-1 * (ev.delta / 120)), "units")
				),
			)
			scroll_frame.bind("<Leave>", lambda e, c=canvas: c.unbind_all("<MouseWheel>"))

			self.frames[strategy] = scroll_frame

	def create_each_algos(self):
		tiny_font = ("Segoe UI", 9)

		for strategy in self.algo_groups:
			frame = self.frames[strategy]
			row = 0

			for algo, item in self.algos[strategy].items():
				lbl = tb.Label(frame, text=algo, cursor="hand2", padding=(0, 0), font=tiny_font)
				lbl.grid(sticky="w", column=0, row=row, padx=(1, 2), pady=(0, 1))

				def toggle(var=item[ACTIVE]):
					var.set(0 if var.get() else 1)
				lbl.bind("<Button-1>", lambda e, var=item[ACTIVE]: toggle(var))

				tb.Checkbutton(frame, variable=item[ACTIVE], bootstyle="round-toggle").grid(
					sticky="w", column=1, row=row, padx=(0, 2), pady=(0, 1), ipady=0
				)

				tb.Label(frame, text="×", padding=(0, 0), font=tiny_font).grid(
					sticky="e", column=2, row=row, padx=(0, 1), pady=(0, 1)
				)
				tb.Entry(frame, textvariable=item[MULTIPLIER], width=3, font=tiny_font).grid(
					sticky="w", column=3, row=row, padx=(0, 2), pady=(0, 1), ipady=0
				)

				tb.Label(frame, text="Agg:", padding=(0, 0), font=tiny_font).grid(
					sticky="e", column=4, row=row, padx=(0, 1), pady=(0, 1)
				)
				tb.Checkbutton(frame, variable=item[PASSIVE], bootstyle="round-toggle").grid(
					sticky="w", column=5, row=row, padx=(0, 1), pady=(0, 1), ipady=0
				)

				row += 1

			tb.Button(frame, text="Save", width=6, command=self.save_all).grid(
				sticky="w", column=0, row=row, padx=(1, 2), pady=(3, 1)
			)
			tb.Button(frame, text="Revert", width=6, command=self.load_all).grid(
				sticky="w", column=2, row=row, padx=(1, 2), pady=(3, 1)
			)
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

	def order_confirmation(self,basket_name,orders):

		#print("RECEVING:",basket_name,orders)


			## PARSE IT AND RE PARSE IT. ? ADD RISK TO IT. 

		name = basket_name


		for i in self.algo_groups:
			for algo,item in self.algos[i].items():
				#print(algo,name,algo in name,item[ACTIVE].get())
				if algo == name[:len(algo)] and item[ACTIVE].get()==True:

					multiplier= item[MULTIPLIER].get()
					for key in orders.keys():
						orders[key]['share'] = orders[key]['share']*multiplier
					
					return True,orders,item[PASSIVE].get(),multiplier,algo
					
		return False,None,0,1,''


if __name__ == '__main__':
	root = tb.Window(themename='flatly')
	root.title('GoodTrade AMS')
	root.geometry('340x800')
	dashboard = authorization(root)
	root.mainloop()