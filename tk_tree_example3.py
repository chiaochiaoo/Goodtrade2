import tkinter as tk
from tkinter import ttk
import ttkbootstrap as tb
import random

def generate_random_data(num_rows=10):
    """
    Generates a list of random data to populate the Treeviews.
    Each tuple in the list represents a row of data.
    """
    data = []
    for i in range(1, num_rows + 1):
        _id = i
        algo = f"Algo_{random.choice(['Alpha', 'Beta', 'Gamma', 'Delta'])}{random.randint(100, 999)}"
        status = random.choice(["Active", "Paused", "Error", "Completed", "Pending"])
        position = random.choice(["Long", "Short", "Flat"])
        unreal = round(random.uniform(-10000.00, 10000.00), 2)
        real = round(random.uniform(-5000.00, 5000.00), 2)
        plus25 = random.randint(0, 15)
        minus25 = random.randint(0, 15)
        plus50 = random.randint(0, 8)
        minus50 = random.randint(0, 8)
        flatten = random.choice(["Yes", "No"])
        a_flat = random.choice(["Enabled", "Disabled"])

        data.append((_id, algo, status, position, unreal, real, plus25, minus25, plus50, minus50, flatten, a_flat))
    return data

def create_treeview_window_bootstrap():
    """
    Creates the main Tkinter window and sets up three ttkbootstrap Treeview widgets,
    each with distinct font sizes and overall dimensions, populated with random data.
    """
    # Initialize the main window using ttkbootstrap.Window for themed widgets
    window = tb.Window(themename="superhero") # 'superhero' is a dark, modern theme.
                                              # Other options: 'flatly', 'cosmo', 'darkly', 'litera', etc.
    window.title("Scalable Treeviews with Random Data (ttkbootstrap)")
    window.geometry("1400x1200") # Set a larger window size to accommodate bigger Treeviews

    # Define the headers for the Treeview columns
    headers = ["#", "Algo", "Status", "Position", "Unreal", "Real", "+25", "-25", "+50", "-50", "Flatten", "A-Flat"]

    # --- Configure Custom Styles for Each Treeview's Font Sizes ---
    # Create a ttk.Style object to define custom styles
    style = tb.Style()
    style.configure("Large.Treeview", font=("Arial", 12),rowheight=20)
    style.configure("Large.Treeview.Heading", font=("Arial", 19, "bold"))
    
    # Style for Treeview 1: Smallest font size for both rows and headings
    style.configure("Small.Treeview", font=("Arial", 10)) # Font for the actual data rows
    style.configure("Small.Treeview.Heading", font=("Arial", 11, "bold")) # Font for the column headers

    # Style for Treeview 2: Medium font size for both rows and headings
    style.configure("Medium.Treeview", font=("Arial", 14))
    style.configure("Medium.Treeview.Heading", font=("Arial", 15, "bold"))

    # Style for Treeview 3: Largest font size for both rows and headings
    style.configure("Large.Treeview", font=("Arial", 12),rowheight=20)
    style.configure("Large.Treeview.Heading", font=("Arial", 19, "bold"))



    # --- Treeview 1: Smallest overall size ---
    # Label indicating the Treeview's characteristics
    label1 = ttk.Label(window, text="Larger Small Treeview (Font 10, Height 6)", font=("Arial", 14), bootstyle="primary")
    label1.pack(pady=5)
    # Create the Treeview widget
    tree1 = tb.Treeview(window,
                        columns=headers,
                        show="headings", # Only show column headings, not a default first column
                        height=12,        # Number of rows visible without scrolling
                        style="Small.Treeview", # Apply the custom font style
                        bootstyle="info") # Apply a ttkbootstrap theme style (e.g., striped rows)

    # Configure column headings and widths for Treeview 1
    for col in headers:
        tree1.heading(col, text=col) # Set the text for each column header
        tree1.column(col, width=80, anchor="center") # Set column width and alignment
    tree1.pack(pady=5, fill="x", padx=10) # Pack the Treeview into the window

    # --- Treeview 2: Medium overall size ---
    label2 = ttk.Label(window, text="Larger Medium Treeview (Font 14, Height 9)", font=("Arial", 18), bootstyle="success")
    label2.pack(pady=5)
    tree2 = tb.Treeview(window,
                        columns=headers,
                        show="headings",
                        height=9,
                        style="Medium.Treeview",
                        bootstyle="primary-striped")
    for col in headers:
        tree2.heading(col, text=col)
        tree2.column(col, width=110, anchor="center")
    tree2.pack(pady=5, fill="x", padx=10)

    # --- Treeview 3: Largest overall size ---
    label3 = ttk.Label(window, text="Extra Large Treeview (Font 18, Height 12)", font=("Arial", 22), bootstyle="danger")
    label3.pack(pady=5)
    tree3 = tb.Treeview(window,
                        columns=headers,
                        show="headings",
                        height=24,
                        style="Large.Treeview",
                        bootstyle="warning-striped")
    for col in headers:
        tree3.heading(col, text=col)
        tree3.column(col, width=140, anchor="center")
    tree3.pack(pady=5, fill="x", padx=10)

    # --- Populate Treeviews with Random Data ---
    # Generate enough random rows to fill the largest Treeview
    random_data = generate_random_data(num_rows=15)

    # Insert the generated data into each Treeview
    for item in random_data:
        tree1.insert("", "end", values=item) # "" for top-level item, "end" to append at the end
        tree2.insert("", "end", values=item)
        tree3.insert("", "end", values=item)

    # Start the Tkinter event loop
    window.mainloop()

if __name__ == "__main__":
    create_treeview_window_bootstrap()