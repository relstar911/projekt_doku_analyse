import os
import sys
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import threading
import extract_documentation_deep as extractor

class DocumentationAnalyzerUI:
    def __init__(self, root):
        self.root = root
        self.root.title("EDNX Dokumentations-Analyse Tool")
        self.root.geometry("900x700")
        self.root.minsize(900, 700)
        
        # Set color scheme
        self.bg_color = "#f5f5f5"  # Light gray background
        self.accent_color = "#3a7ca5"  # Blue accent
        self.text_color = "#333333"  # Dark text
        self.highlight_color = "#16425b"  # Darker blue for highlights
        self.success_color = "#2e7d32"  # Green for success messages
        self.warning_color = "#f9a825"  # Yellow for warnings
        
        # Apply theme
        self.style = ttk.Style()
        self.style.theme_use('clam')  # Use clam theme as base
        
        # Configure styles
        self.style.configure('TFrame', background=self.bg_color)
        self.style.configure('TLabel', background=self.bg_color, foreground=self.text_color)
        self.style.configure('TButton', background=self.accent_color, foreground='white')
        self.style.map('TButton', background=[('active', self.highlight_color)])
        self.style.configure('Header.TLabel', font=('Arial', 18, 'bold'), foreground=self.highlight_color)
        self.style.configure('Subheader.TLabel', font=('Arial', 14), foreground=self.accent_color)
        self.style.configure('TLabelframe', background=self.bg_color)
        self.style.configure('TLabelframe.Label', background=self.bg_color, foreground=self.accent_color, font=('Arial', 12, 'bold'))
        
        # Configure root
        self.root.configure(bg=self.bg_color)
        
        # Create variables
        self.start_paths = []
        self.output_dir = tk.StringVar(value=os.path.join(os.path.expanduser("~"), "alle_dokumentationen"))
        self.enable_summarization = tk.BooleanVar(value=True)
        self.use_openai = tk.BooleanVar(value=False)
        self.min_summaries = tk.IntVar(value=5)
        self.max_summaries = tk.IntVar(value=10)
        
        # Create UI elements
        self.create_ui()
        
        # Status variables
        self.is_running = False
        self.log_text = ""
        
    def create_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Header with title
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=10)
        
        # Create a stylish text-based header
        title_label = ttk.Label(header_frame, text="EDNX", style="Header.TLabel", font=("Arial", 24, "bold"))
        title_label.pack(side=tk.LEFT, padx=5)
        
        subtitle_label = ttk.Label(header_frame, text="Dokumentations-Analyse Tool", style="Subheader.TLabel")
        subtitle_label.pack(side=tk.LEFT, padx=5)
        
        # Add a horizontal separator
        separator = ttk.Separator(main_frame, orient='horizontal')
        separator.pack(fill=tk.X, pady=10)
        
        # Input paths section
        paths_frame = ttk.LabelFrame(main_frame, text="Eingabeverzeichnisse", padding="15")
        paths_frame.pack(fill=tk.X, pady=10)
        
        # Description
        path_desc = ttk.Label(paths_frame, text="Wählen Sie die zu analysierenden Verzeichnisse aus:")
        path_desc.pack(anchor=tk.W, pady=(0, 10))
        
        # List of paths with modern styling
        paths_list_frame = ttk.Frame(paths_frame)
        paths_list_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.paths_listbox = tk.Listbox(paths_list_frame, height=5, bg="white", 
                                      selectbackground=self.accent_color, 
                                      selectforeground="white",
                                      borderwidth=1, relief=tk.SOLID)
        self.paths_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        paths_scrollbar = ttk.Scrollbar(paths_list_frame, orient="vertical", command=self.paths_listbox.yview)
        paths_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.paths_listbox.config(yscrollcommand=paths_scrollbar.set)
        
        # Buttons for paths with improved styling
        paths_buttons_frame = ttk.Frame(paths_frame)
        paths_buttons_frame.pack(fill=tk.X, pady=10)
        
        # Style for buttons
        self.style.configure('Add.TButton', background=self.accent_color)
        self.style.configure('Remove.TButton', background='#d32f2f')
        
        add_path_button = ttk.Button(paths_buttons_frame, text="Verzeichnis hinzufügen", 
                                    style='Add.TButton', command=self.add_path)
        add_path_button.pack(side=tk.LEFT, padx=5)
        
        remove_path_button = ttk.Button(paths_buttons_frame, text="Verzeichnis entfernen", 
                                       style='Remove.TButton', command=self.remove_path)
        remove_path_button.pack(side=tk.LEFT, padx=5)
        
        # Output directory section
        output_frame = ttk.LabelFrame(main_frame, text="Ausgabeverzeichnis", padding="15")
        output_frame.pack(fill=tk.X, pady=10)
        
        # Description
        output_desc = ttk.Label(output_frame, text="Wählen Sie das Zielverzeichnis für die Analyseergebnisse:")
        output_desc.pack(anchor=tk.W, pady=(0, 10))
        
        # Output directory selection with modern styling
        output_select_frame = ttk.Frame(output_frame)
        output_select_frame.pack(fill=tk.X, expand=True)
        
        output_entry = ttk.Entry(output_select_frame, textvariable=self.output_dir, width=50)
        output_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)
        
        output_btn = ttk.Button(output_select_frame, text="Durchsuchen", command=self.select_output_dir)
        output_btn.pack(side=tk.RIGHT, padx=5, pady=5)
        
        # Options section
        options_frame = ttk.LabelFrame(main_frame, text="Optionen", padding="15")
        options_frame.pack(fill=tk.X, pady=10)
        
        # Create two columns for options
        left_options = ttk.Frame(options_frame)
        left_options.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        right_options = ttk.Frame(options_frame)
        right_options.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5)
        
        # Left column - Summarization options
        sum_header = ttk.Label(left_options, text="KI-Zusammenfassung", font=("Arial", 11, "bold"))
        sum_header.pack(anchor=tk.W, pady=(0, 5))
        
        # Style for checkbuttons
        self.style.configure('TCheckbutton', background=self.bg_color)
        
        summarization_check = ttk.Checkbutton(left_options, text="KI-Zusammenfassung aktivieren", 
                                             variable=self.enable_summarization)
        summarization_check.pack(anchor=tk.W, pady=2)
        
        openai_check = ttk.Checkbutton(left_options, text="OpenAI API verwenden (sonst lokales LLM)", 
                                      variable=self.use_openai)
        openai_check.pack(anchor=tk.W, pady=2)
        
        # Right column - Batch processing options
        batch_header = ttk.Label(right_options, text="Batch-Verarbeitung", font=("Arial", 11, "bold"))
        batch_header.pack(anchor=tk.W, pady=(0, 5))
        
        # Min summaries
        min_frame = ttk.Frame(right_options)
        min_frame.pack(fill=tk.X, pady=2)
        
        min_label = ttk.Label(min_frame, text="Min. Zusammenfassungen pro Lauf:")
        min_label.pack(side=tk.LEFT)
        
        min_spin = ttk.Spinbox(min_frame, from_=1, to=20, width=5, textvariable=self.min_summaries)
        min_spin.pack(side=tk.LEFT, padx=5)
        
        # Max summaries
        max_frame = ttk.Frame(right_options)
        max_frame.pack(fill=tk.X, pady=2)
        
        max_label = ttk.Label(max_frame, text="Max. Zusammenfassungen pro Lauf:")
        max_label.pack(side=tk.LEFT)
        
        max_spin = ttk.Spinbox(max_frame, from_=1, to=50, width=5, textvariable=self.max_summaries)
        max_spin.pack(side=tk.LEFT, padx=5)
        
        # Log section
        log_frame = ttk.LabelFrame(main_frame, text="Log", padding="15")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Log description
        log_desc = ttk.Label(log_frame, text="Fortschritt und Status der Analyse:")
        log_desc.pack(anchor=tk.W, pady=(0, 5))
        
        # Log text widget with modern styling
        log_container = ttk.Frame(log_frame, borderwidth=1, relief=tk.SOLID)
        log_container.pack(fill=tk.BOTH, expand=True)
        
        self.log_text_widget = tk.Text(log_container, wrap=tk.WORD, height=10, 
                                     bg="white", fg=self.text_color,
                                     font=("Consolas", 10),
                                     borderwidth=0)
        self.log_text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        log_scrollbar = ttk.Scrollbar(log_container, orient=tk.VERTICAL, command=self.log_text_widget.yview)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text_widget.config(yscrollcommand=log_scrollbar.set)
        
        # Action buttons with improved styling
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill=tk.X, pady=15)
        
        # Style for action buttons
        self.style.configure('Start.TButton', background=self.success_color, font=("Arial", 11))
        self.style.configure('Stop.TButton', background="#d32f2f", font=("Arial", 11))
        
        self.start_btn = ttk.Button(buttons_frame, text="Analyse starten", 
                                   style="Start.TButton", command=self.start_analysis)
        self.start_btn.pack(side=tk.RIGHT, padx=10, pady=5, ipadx=10, ipady=5)
        
        self.stop_btn = ttk.Button(buttons_frame, text="Abbrechen", 
                                  style="Stop.TButton", command=self.stop_analysis, 
                                  state=tk.DISABLED)
        self.stop_btn.pack(side=tk.RIGHT, padx=10, pady=5, ipadx=10, ipady=5)
    
    def add_path(self):
        path = filedialog.askdirectory(title="Verzeichnis auswählen")
        if path:
            self.start_paths.append(path)
            self.paths_listbox.insert(tk.END, path)
    
    def remove_path(self):
        selected = self.paths_listbox.curselection()
        if selected:
            index = selected[0]
            self.paths_listbox.delete(index)
            self.start_paths.pop(index)
    
    def select_output_dir(self):
        path = filedialog.askdirectory(title="Ausgabeverzeichnis auswählen")
        if path:
            self.output_dir.set(path)
    
    def log(self, message):
        self.log_text += message + "\n"
        self.log_text_widget.delete(1.0, tk.END)
        self.log_text_widget.insert(tk.END, self.log_text)
        self.log_text_widget.see(tk.END)
        self.root.update_idletasks()
    
    def start_analysis(self):
        if not self.start_paths:
            messagebox.showerror("Fehler", "Bitte mindestens ein Eingabeverzeichnis auswählen.")
            return
        
        # Update UI state
        self.is_running = True
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.log_text = ""
        self.log("Analyse wird gestartet...")
        
        # Configure extractor
        extractor.STARTPFADEN = self.start_paths
        extractor.ZIELORDNER = self.output_dir.get()
        extractor.ENABLE_SUMMARIZATION = self.enable_summarization.get()
        extractor.USE_OPENAI = self.use_openai.get()
        extractor.MIN_SUMMARIES_PER_RUN = self.min_summaries.get()
        extractor.MAX_SUMMARIES_PER_RUN = self.max_summaries.get()
        
        # Redirect stdout to capture log
        original_stdout = sys.stdout
        sys.stdout = self
        
        # Run in a separate thread
        self.analysis_thread = threading.Thread(target=self.run_analysis)
        self.analysis_thread.daemon = True
        self.analysis_thread.start()
    
    def run_analysis(self):
        try:
            extractor.main()
            self.root.after(0, self.analysis_complete)
        except Exception as e:
            self.root.after(0, lambda: self.analysis_error(str(e)))
    
    def analysis_complete(self):
        self.is_running = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.log("\nAnalyse abgeschlossen!")
        sys.stdout = sys.__stdout__
        messagebox.showinfo("Fertig", "Dokumentationsanalyse abgeschlossen!")
    
    def analysis_error(self, error_message):
        self.is_running = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.log(f"\nFehler: {error_message}")
        sys.stdout = sys.__stdout__
        messagebox.showerror("Fehler", f"Ein Fehler ist aufgetreten:\n{error_message}")
    
    def stop_analysis(self):
        if self.is_running:
            # We can't really stop the analysis once it's running,
            # but we can restore the UI state
            self.log("\nAnalyse wird abgebrochen...")
            self.is_running = False
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
            sys.stdout = sys.__stdout__
    
    def write(self, text):
        # This method is used to capture stdout
        self.root.after(0, lambda: self.log(text.rstrip()))
        return len(text)
    
    def flush(self):
        # Required for stdout redirection
        pass

def main():
    root = tk.Tk()
    app = DocumentationAnalyzerUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
