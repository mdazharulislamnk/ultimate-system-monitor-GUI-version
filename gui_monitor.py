"""
SYSTEM MONITOR PRO - GUI EDITION (TEXT-RICH VERSION)
Author: Md. Azharul Islam
License: MIT
Description:
    A professional, high-performance system monitoring dashboard built with Python.
    It uses 'CustomTkinter' for a modern, dark-themed UI and 'psutil' for real-time
    hardware statistics including CPU (per-core), RAM, Swap, Storage, and Network.

    Key Features:
    - Full control over window size and position.
    - Real-time tracking with dynamic color-coded progress bars.
    - Multi-threaded architecture for non-blocking UI (smooth animations).
    - Responsive grid layout that adapts to content.
"""

# ==========================================
# 📚 LIBRARIES & MODULES
# ==========================================
import customtkinter as ctk  # The main GUI library (Modern wrapper for Tkinter)
import psutil                # (Process & System Utilities) Fetches CPU, RAM, Disk, Net info
import threading             # Allows running tasks (like Ping) in parallel without freezing the app
import socket                # Used to create network connections for the Ping test
import platform              # Retrieves system info like Hostname and OS type
import time                  # Used for measuring time intervals (latency)
from datetime import datetime # Used to format the System Uptime string

# ==========================================
# ⚙️ CONFIGURATION (USER SETTINGS)
# ==========================================
APP_TITLE = "System Monitor Pro By Azhar"

# --- WINDOW CONTROL ---
# Define the Width and Height of the application window
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 900

# Define the starting position on the screen (Pixels from Top-Left corner)
# X = Distance from Left, Y = Distance from Top
WINDOW_X = 100
WINDOW_Y = 100

REFRESH_RATE = 1000          # How often the UI updates (in milliseconds). 1000ms = 1 second.

# --- COLORS (THEME) ---
# A Cyberpunk/Professional Dark Theme palette
COLOR_BG = "#1a1a1a"          # Dark background color
COLOR_FRAME = "#2b2b2b"       # Slightly lighter color for widget containers
COLOR_TEXT_HEADER = "#3B8ED0" # Blue color for section titles
COLOR_TEXT_NORMAL = "#FFFFFF" # White color for standard text
COLOR_TEXT_DIM = "#A0A0A0"    # Grey color for less important details
COLOR_GOOD = "#2CC985"        # Green color (Safe/Low usage)
COLOR_WARN = "#F2A33C"        # Orange color (Warning/Medium usage)
COLOR_CRIT = "#E04F5F"        # Red color (Critical/High usage)

# ==========================================
# 🔧 HELPER FUNCTIONS
# ==========================================

def get_size(bytes, suffix="B"):
    """
    Converts a raw byte number (e.g., 1073741824) into a human-readable string (e.g., "1.00 GB").
    It iteratively divides by 1024 to find the appropriate unit (KB, MB, GB, TB).
    """
    factor = 1024
    for unit in ["", "K", "M", "G", "T", "P"]:
        if bytes < factor:
            return f"{bytes:.2f}{unit}{suffix}"
        bytes /= factor

def get_color_by_usage(percent):
    """
    Determines the color of a progress bar based on the usage percentage.
    - Less than 50%: Green (Good)
    - 50% to 79%: Orange (Warning)
    - 80% and above: Red (Critical)
    """
    if percent < 50: return COLOR_GOOD
    if percent < 80: return COLOR_WARN
    return COLOR_CRIT

# ==========================================
# 🚀 MAIN APPLICATION CLASS
# ==========================================

class SystemMonitorApp(ctk.CTk):
    """
    The main application class inheriting from customtkinter.
    This class manages the window, layout, and update logic.
    """
    def __init__(self):
        super().__init__()

        # --- Window Setup ---
        self.title(APP_TITLE)
        
        # Geometry Format: "WidthxHeight+X_Position+Y_Position"
        # This sets both the size and the position on the screen.
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}+{WINDOW_X}+{WINDOW_Y}")
        
        # Theme Settings
        ctk.set_appearance_mode("Dark")       # Forces the app into Dark Mode
        ctk.set_default_color_theme("blue")   # Sets the default accent color for widgets

        # --- State Variables ---
        # self.old_net_io stores the network counters from the *previous* second.
        # We subtract current counters from this to calculate speed (Bytes per second).
        self.old_net_io = psutil.net_io_counters()
        
        # Stores the ping result calculated by the background thread.
        self.ping_latency = 0 
        
        # --- Grid Layout Configuration ---
        # We use a 2-column grid layout for the main content.
        # weight=1 tells the column to expand to fill available space.
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        # The row containing the scrollable frame should expand.
        self.grid_rowconfigure(1, weight=1)

        # 1. HEADER SECTION (Top Banner)
        self.create_header_section()

        # 2. SCROLLABLE CONTENT AREA
        # A container that allows scrolling if content exceeds the window height.
        # This is crucial for machines with many CPU cores or Drives.
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=10, pady=10)
        self.scroll_frame.grid_columnconfigure(0, weight=1)
        self.scroll_frame.grid_columnconfigure(1, weight=1)

        # 3. CREATE WIDGET SECTIONS
        # These methods build the specific UI panels for each resource.
        self.create_cpu_section()
        self.create_memory_section()
        self.create_storage_section()
        self.create_network_section()

        # --- Start Background Tasks ---
        self.start_ping_thread() # Starts the non-blocking network checker
        self.update_ui_loop()    # Starts the recursive timer to refresh data

    # ---------------------------------------------------------
    # UI SECTIONS CONSTRUCTION
    # ---------------------------------------------------------

    def create_header_section(self):
        """Creates the top banner displaying the App Title and Hostname."""
        self.header_frame = ctk.CTkFrame(self, corner_radius=15, fg_color=COLOR_FRAME)
        self.header_frame.grid(row=0, column=0, columnspan=2, padx=15, pady=(15, 5), sticky="ew")
        
        # Title Label
        self.lbl_title = ctk.CTkLabel(
            self.header_frame, 
            text=f"💻 {APP_TITLE}  |  Host: {platform.node()}", 
            font=("Roboto", 20, "bold"), 
            text_color=COLOR_TEXT_HEADER
        )
        self.lbl_title.pack(pady=(10, 0))
        
        # Uptime Label (Text will be updated dynamically)
        self.lbl_uptime = ctk.CTkLabel(
            self.header_frame, 
            text="System Uptime: ...", 
            font=("Consolas", 13), 
            text_color=COLOR_TEXT_DIM
        )
        self.lbl_uptime.pack(pady=(0, 10))

    def create_cpu_section(self):
        """Builds the CPU monitoring panel."""
        self.cpu_frame = ctk.CTkFrame(self.scroll_frame, corner_radius=10, fg_color=COLOR_FRAME)
        self.cpu_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        
        # Section Header Container
        header_box = ctk.CTkFrame(self.cpu_frame, fg_color="transparent")
        header_box.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(header_box, text="CPU METRICS", font=("Arial", 16, "bold"), text_color=COLOR_TEXT_HEADER).pack(side="left")
        
        # Total Usage Label (Now shows Used vs Free)
        self.lbl_cpu_val = ctk.CTkLabel(header_box, text="Used: 0% | Free: 100%", font=("Arial", 12, "bold"))
        self.lbl_cpu_val.pack(side="right", padx=10)
        
        # Total Usage Bar
        self.prog_cpu = ctk.CTkProgressBar(self.cpu_frame, height=15)
        self.prog_cpu.pack(fill="x", padx=15, pady=5)
        
        # Frequency Label
        self.lbl_cpu_freq = ctk.CTkLabel(self.cpu_frame, text="Clock: 0 MHz", text_color=COLOR_TEXT_DIM, font=("Consolas", 12))
        self.lbl_cpu_freq.pack(anchor="w", padx=15)

        # Per-Core Grid Title
        ctk.CTkLabel(self.cpu_frame, text="Logical Cores", font=("Arial", 12, "bold")).pack(pady=(15, 5))
        
        # Container for Core Bars
        self.cores_inner_frame = ctk.CTkFrame(self.cpu_frame, fg_color="transparent")
        self.cores_inner_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.core_widgets = []
        # Loop through available cores (Max 32 to keep UI clean, though psutil fetches all)
        for i in range(min(psutil.cpu_count(), 32)):
            # Create a sub-frame for each core to hold Label + Bar together
            f = ctk.CTkFrame(self.cores_inner_frame, fg_color="transparent")
            f.grid(row=i//4, column=i%4, padx=5, pady=2, sticky="ew")
            
            # Core Label (e.g., "Core 1: 50%") - Updated naming from #01 to Core 1
            lbl = ctk.CTkLabel(f, text=f"Core {i+1}: 0%", font=("Consolas", 11), width=80, anchor="w")
            lbl.pack(side="left")
            
            # Core Bar
            bar = ctk.CTkProgressBar(f, height=6, width=50)
            bar.pack(side="left", padx=5)
            
            # Store references so we can update them later
            self.core_widgets.append((lbl, bar))

    def create_memory_section(self):
        """Builds the RAM and Swap monitoring panel."""
        self.mem_frame = ctk.CTkFrame(self.scroll_frame, corner_radius=10, fg_color=COLOR_FRAME)
        self.mem_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        
        ctk.CTkLabel(self.mem_frame, text="MEMORY (RAM & SWAP)", font=("Arial", 16, "bold"), text_color=COLOR_TEXT_HEADER).pack(pady=10)
        
        # --- Physical RAM ---
        self.lbl_ram_title = ctk.CTkLabel(self.mem_frame, text="Physical RAM", font=("Arial", 13, "bold"))
        self.lbl_ram_title.pack(anchor="w", padx=15)
        
        # Detailed Text (Used / Total / Free)
        self.lbl_ram_text = ctk.CTkLabel(self.mem_frame, text="Total: 0GB | Used: 0GB | Free: 0GB", font=("Consolas", 11))
        self.lbl_ram_text.pack(anchor="w", padx=15)
        
        self.prog_ram = ctk.CTkProgressBar(self.mem_frame, height=15)
        self.prog_ram.pack(fill="x", padx=15, pady=5)
        
        ctk.CTkLabel(self.mem_frame, text="").pack(pady=2) # Spacer

        # --- Swap Memory ---
        self.lbl_swap_title = ctk.CTkLabel(self.mem_frame, text="Virtual Memory (Swap)", font=("Arial", 13, "bold"), text_color=COLOR_TEXT_HEADER)
        self.lbl_swap_title.pack(anchor="w", padx=15)
        
        self.lbl_swap_text = ctk.CTkLabel(self.mem_frame, text="Total: 0GB | Used: 0GB | Free: 0GB", font=("Consolas", 11))
        self.lbl_swap_text.pack(anchor="w", padx=15)
        
        self.prog_swap = ctk.CTkProgressBar(self.mem_frame, height=15)
        self.prog_swap.pack(fill="x", padx=15, pady=5)

    def create_storage_section(self):
        """Builds the Disk Usage panel."""
        self.disk_frame = ctk.CTkFrame(self.scroll_frame, corner_radius=10, fg_color=COLOR_FRAME)
        self.disk_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        
        ctk.CTkLabel(self.disk_frame, text="STORAGE DRIVES", font=("Arial", 16, "bold"), text_color=COLOR_TEXT_HEADER).pack(pady=10)
        
        # Container to hold dynamic drive list
        self.drives_container = ctk.CTkFrame(self.disk_frame, fg_color="transparent")
        self.drives_container.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Dictionary to keep track of created drive widgets { "C:\\": (bar, label) }
        self.drive_widgets = {} 

    def create_network_section(self):
        """Builds the Network Traffic and Latency panel."""
        self.net_frame = ctk.CTkFrame(self.scroll_frame, corner_radius=10, fg_color=COLOR_FRAME)
        self.net_frame.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")
        
        ctk.CTkLabel(self.net_frame, text="NETWORK TRAFFIC", font=("Arial", 16, "bold"), text_color=COLOR_TEXT_HEADER).pack(pady=10)
        
        # Ping Display
        self.lbl_ping = ctk.CTkLabel(self.net_frame, text="Ping: -- ms", font=("Consolas", 16, "bold"))
        self.lbl_ping.pack(pady=10)
        
        # Speed Grid (Download/Upload)
        self.net_grid = ctk.CTkFrame(self.net_frame, fg_color="transparent")
        self.net_grid.pack(fill="x", padx=20)
        
        # Download Stats
        self.lbl_down_val = ctk.CTkLabel(self.net_grid, text="0.00 KB/s", font=("Consolas", 20, "bold"), text_color=COLOR_GOOD)
        self.lbl_down_val.grid(row=0, column=0, padx=20)
        ctk.CTkLabel(self.net_grid, text="⬇ DOWNLOAD", font=("Arial", 10)).grid(row=1, column=0)
        
        # Upload Stats
        self.lbl_up_val = ctk.CTkLabel(self.net_grid, text="0.00 KB/s", font=("Consolas", 20, "bold"), text_color=COLOR_WARN)
        self.lbl_up_val.grid(row=0, column=1, padx=20)
        ctk.CTkLabel(self.net_grid, text="⬆ UPLOAD", font=("Arial", 10)).grid(row=1, column=1)

    # ---------------------------------------------------------
    # DATA GATHERING & LOGIC
    # ---------------------------------------------------------

    def get_system_uptime(self):
        """Calculates and returns system uptime as a string."""
        boot = datetime.fromtimestamp(psutil.boot_time())
        return str(datetime.now() - boot).split('.')[0]

    def start_ping_thread(self):
        """
        Runs the Ping check in a background thread.
        This prevents the GUI from freezing while waiting for a network response.
        """
        def check_ping_logic():
            while True:
                try:
                    st = time.time()
                    # Create a standard TCP socket
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(1.0) # Timeout after 1 second
                    s.connect(("8.8.8.8", 53)) # Connect to Google DNS
                    s.close()
                    # Calculate duration
                    self.ping_latency = (time.time() - st) * 1000
                except:
                    self.ping_latency = -1 # Indicates failure/offline
                
                time.sleep(1) # Wait 1 second before checking again
        
        # Daemon thread ensures it closes when the app closes
        thread = threading.Thread(target=check_ping_logic, daemon=True)
        thread.start()

    # ---------------------------------------------------------
    # MAIN UPDATE LOOP
    # ---------------------------------------------------------

    def update_ui_loop(self):
        """
        The core loop that runs every second.
        It gathers new data and updates the GUI widgets.
        """
        
        # --- 1. UPDATE CPU ---
        cpu_pct = psutil.cpu_percent()
        cpu_free = 100 - cpu_pct
        
        # Update Total Load Text (Show Used & Free)
        self.lbl_cpu_val.configure(text=f"Used: {cpu_pct}% | Free: {cpu_free:.1f}%")
        
        # Update Frequency
        self.lbl_cpu_freq.configure(text=f"Clock: {psutil.cpu_freq().current:.0f} MHz")
        
        # Update Main Bar
        self.prog_cpu.set(cpu_pct / 100)
        self.prog_cpu.configure(progress_color=get_color_by_usage(cpu_pct))
        
        # Update Individual Core Bars
        cores = psutil.cpu_percent(percpu=True)
        for i, usage in enumerate(cores):
            if i < len(self.core_widgets):
                lbl, bar = self.core_widgets[i]
                # Updated text to show "Core 1: 50%"
                lbl.configure(text=f"Core {i+1}: {usage:.0f}%") 
                bar.set(usage / 100)
                bar.configure(progress_color=get_color_by_usage(usage))

        # --- 2. UPDATE RAM & SWAP ---
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        # Detailed Text like CLI
        self.lbl_ram_text.configure(text=f"Total: {get_size(mem.total)} | Used: {get_size(mem.used)} ({mem.percent}%) | Free: {get_size(mem.available)}")
        self.prog_ram.set(mem.percent / 100)
        self.prog_ram.configure(progress_color=get_color_by_usage(mem.percent))
        
        self.lbl_swap_text.configure(text=f"Total: {get_size(swap.total)} | Used: {get_size(swap.used)} ({swap.percent}%)")
        self.prog_swap.set(swap.percent / 100)
        self.prog_swap.configure(progress_color=get_color_by_usage(swap.percent))

        # --- 3. UPDATE STORAGE (DYNAMIC) ---
        partitions = psutil.disk_partitions()
        
        for p in partitions:
            try:
                # Filter out CD-ROMs or inaccessible drives
                if 'cdrom' in p.opts or p.fstype == '': continue
                
                usage = psutil.disk_usage(p.mountpoint)
                drive_name = p.device
                
                # Check if we already created a widget for this drive
                if drive_name not in self.drive_widgets:
                    # Create container frame
                    f = ctk.CTkFrame(self.drives_container, fg_color="transparent")
                    f.pack(fill="x", pady=5)
                    
                    # Drive Name Label (e.g., C:\)
                    lbl_name = ctk.CTkLabel(f, text=drive_name, width=50, anchor="w", font=("Arial", 12, "bold"))
                    lbl_name.pack(side="left")
                    
                    # Progress Bar
                    bar = ctk.CTkProgressBar(f)
                    bar.pack(side="left", fill="x", expand=True, padx=10)
                    
                    # Details Label
                    lbl_det = ctk.CTkLabel(f, text="", font=("Consolas", 11), width=200, anchor="e")
                    lbl_det.pack(side="right")
                    
                    self.drive_widgets[drive_name] = (bar, lbl_det)

                # Update the widget with new data
                bar, lbl_det = self.drive_widgets[drive_name]
                bar.set(usage.percent / 100)
                bar.configure(progress_color=get_color_by_usage(usage.percent))
                # Text format: "45% (450GB / 1000GB)"
                lbl_det.configure(text=f"{usage.percent}% ({get_size(usage.used)} / {get_size(usage.total)})")
                
            except: continue

        # --- 4. UPDATE NETWORK ---
        new_net = psutil.net_io_counters()
        # Calculate Speed: (Current Total - Previous Total)
        ds = new_net.bytes_recv - self.old_net_io.bytes_recv
        us = new_net.bytes_sent - self.old_net_io.bytes_sent
        self.old_net_io = new_net
        
        self.lbl_down_val.configure(text=f"{get_size(ds)}/s")
        self.lbl_up_val.configure(text=f"{get_size(us)}/s")

        # Update Ping with Colors
        if self.ping_latency == -1:
            self.lbl_ping.configure(text="Ping: Offline ❌", text_color=COLOR_CRIT)
        else:
            p_color = COLOR_GOOD if self.ping_latency < 100 else COLOR_WARN
            self.lbl_ping.configure(text=f"Ping (Google): {self.ping_latency:.0f} ms", text_color=p_color)

        # --- 5. UPDATE UPTIME ---
        self.lbl_uptime.configure(text=f"System Uptime: {self.get_system_uptime()}")

        # Schedule the function to run again in REFRESH_RATE milliseconds
        self.after(REFRESH_RATE, self.update_ui_loop)

# --- ENTRY POINT ---
if __name__ == "__main__":
    app = SystemMonitorApp()
    app.mainloop()