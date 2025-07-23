import tkinter as tk
from tkinter import ttk
import time

class SplashScreen:
    def __init__(self, root, loading_time=3):
        self.root = root
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        
        splash_width = 400
        splash_height = 200
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        x = (screen_width // 2) - (splash_width // 2)
        y = (screen_height // 2) - (splash_height // 2)
        self.root.geometry(f'{splash_width}x{splash_height}+{x}+{y}')
        
        # Add content
        ttk.Label(self.root, text="Voice Transcriber for Roblox", font=('Helvetica', 14, 'bold')).pack(pady=20)
        ttk.Label(self.root, text="Loading...", font=('Helvetica', 12)).pack()
        
        self.progress = ttk.Progressbar(self.root, mode='indeterminate')
        self.progress.pack(pady=20, padx=40, fill='x')
        self.progress.start()
        
        self.loading_time = loading_time
        self.start_time = time.time()
        
    def update(self):
        if time.time() - self.start_time >= self.loading_time:
            self.root.destroy()
            return False
        return True