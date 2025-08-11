import os
import json
import tkinter as tk
import ttkbootstrap as tb
from ttkbootstrap.constants import *

ACTIVE = 0
MULTIPLIER = 1
PASSIVE = 2
DESCRIPTION = 3

class sim_test:
    def __init__(self, ui):
        self.ui = ui


        self.pannel_name = 'TMS-SIMs'
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


if __name__ == '__main__':
    root = tb.Window(themename='flatly')
    root.title('GoodTrade AMS')
    root.geometry('340x800')
    dashboard = sim_test(root)
    root.mainloop()