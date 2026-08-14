import ttkbootstrap as tb
from Manager import Manager
from logging_module import *
from Manager import force_close_port  # if needed
from flask import Flask, request

EMS_ADDRESS = "127.0.0.1"

def main():
    # kill port if needed
    force_close_port(4440)

    root = tb.Window(themename="flatly")
    root.title("GoodTrade AMS 08-14")

    root.geometry("1870x1280")

    m = Manager(root, EMS_ADDRESS)

    message("System Initialized", NOTIFICATION)

    root.mainloop()

if __name__ == "__main__":
    main()