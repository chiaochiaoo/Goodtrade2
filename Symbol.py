import tkinter as tk
import requests


class Symbol:
    def __init__(self,manager,symbol):

        self.manager = manager
        self.symbol_name = symbol

        self.tradable = True

        ## UI s ##
        self.tkvars = {}

        ## DATA ##
        self.ask = 0
        self.bid = 0
        self.bid_change = False
        self.ask_change = False
