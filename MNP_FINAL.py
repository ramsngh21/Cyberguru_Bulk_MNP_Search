import requests
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import re
import json
import time
import threading

# Set your icon path here (use raw string r"..." to avoid escape errors)
ICON_PATH = r"C:\Users\Ram\Downloads\Python Projects Ram Singh\MNP\MNP.ico"

class MNPChecker:
    def __init__(self, root):
        self.root = root
        self.root.title("MNP Checker Ram")

        # Set the window icon safely
        try:
            self.root.iconbitmap(ICON_PATH)
        except Exception as e:
            print(f"Warning: Could not set icon: {e}")

        # Variables
        self.cooldown = 3.0  # Initial cooldown in seconds
        self.min_cooldown = 2.0
        self.max_cooldown = 10.0
        self.running = False
        self.stop_flag = False

        # UI Elements
        self.setup_ui()

        # Data tracking for retries
        self.retry_counts = {}
        self.results = []

    def setup_ui(self):
        # Cookie entry
        tk.Label(self.root, text="Enter your ci_session cookie:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.cookie_entry = tk.Entry(self.root, width=60)
        self.cookie_entry.grid(row=0, column=1, padx=5, pady=5)

        # Numbers input
        tk.Label(self.root, text="Phone Numbers (comma or newline separated):").grid(row=1, column=0, sticky=tk.NW, padx=5, pady=5)
        self.number_text = tk.Text(self.root, width=40, height=8)
        self.number_text.grid(row=1, column=1, padx=5, pady=5)

        # Buttons
        self.run_button = tk.Button(self.root, text="Run Bulk Search", command=self.start_search)
        self.run_button.grid(row=2, column=0, columnspan=2, pady=10)

        self.stop_button = tk.Button(self.root, text="Stop", state=tk.DISABLED, command=self.stop_search)
        self.stop_button.grid(row=2, column=2, padx=5)

        self.save_button = tk.Button(self.root, text="Save Results", command=self.save_results)
        self.save_button.grid(row=3, column=2, padx=5)

        self.load_button = tk.Button(self.root, text="Load Numbers", command=self.load_numbers)
        self.load_button.grid(row=4, column=2, padx=5)

        self.export_button = tk.Button(self.root, text="Export to Excel", command=self.export_to_excel)
        self.export_button.grid(row=5, column=2, padx=5)

        self.copy_button = tk.Button(self.root, text="Copy All Results", command=self.copy_results)
        self.copy_button.grid(row=6, column=2, padx=5)

        # Progress label and bar
        self.progress_label = tk.Label(self.root, text="Progress: 0 / 0")
        self.progress_label.grid(row=3, column=0, sticky=tk.W, padx=5)

        self.countdown_label = tk.Label(self.root, text="Cooldown: 0.0s")
        self.countdown_label.grid(row=3, column=1, sticky=tk.W, padx=5)

        self.progressbar = ttk.Progressbar(self.root, length=400)
        self.progressbar.grid(row=4, column=0, columnspan=2, padx=5, pady=5)

        # Output table
        columns = ("Attempt", "Number", "Operator", "Circle Code", "Circle Name", "Ported")
        self.tree = ttk.Treeview(self.root, columns=columns, show="headings", height=15)
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120)
        self.tree.grid(row=7, column=0, columnspan=3, padx=5, pady=5)

        # Scrollable output text for logs
        self.output_text = scrolledtext.ScrolledText(self.root, width=80, height=10)
        self.output_text.grid(row=8, column=0, columnspan=3, padx=5, pady=5)

    def start_search(self):
        if self.running:
            return
        ci_session_token = self.cookie_entry.get().strip()
        if not ci_session_token:
            messagebox.showerror("Input Error", "Please enter your ci_session cookie.")
            return

        numbers_text = self.number_text.get("1.0", tk.END).strip()
        if not numbers_text:
            messagebox.showerror("Input Error", "Please enter at least one phone number.")
            return

        self.numbers = [n.strip() for n in re.split(r"[,\n]", numbers_text) if n.strip()]
        if not self.numbers:
            messagebox.showerror("Input Error", "Please enter valid phone numbers.")
            return

        self.session = requests.Session()
        self.session.cookies.set("ci_session", ci_session_token, domain="guru.cyberyodha.org")

        self.running = True
        self.stop_flag = False
        self.run_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.output_text.delete(1.0, tk.END)
        self.clear_table()
        self.retry_counts.clear()
        self.results.clear()
        self.progressbar["maximum"] = len(self.numbers)
        self.progressbar["value"] = 0
        self.progress_label.config(text=f"Progress: 0 / {len(self.numbers)}")
        self.cooldown = 3.0

        threading.Thread(target=self.run_bulk_search, daemon=True).start()

    def stop_search(self):
        self.stop_flag = True
        self.output_text.insert(tk.END, "Stopping search after current request...\n")
        self.stop_button.config(state=tk.DISABLED)

    def run_bulk_search(self):
        url = "https://guru.cyberyodha.org/request/singlemnp"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        idx = 0
        while idx < len(self.numbers):
            if self.stop_flag:
                break

            number = self.numbers[idx]
            attempt = self.retry_counts.get(number, 0) + 1
            self.retry_counts[number] = attempt

            self.output_text.insert(tk.END, f"Checking {idx+1}/{len(self.numbers)} Attempt {attempt}: {number}\n")
            self.output_text.see(tk.END)

            start_time = time.time()
            try:
                response = self.session.post(url, data={"number": number}, headers=headers)
                duration = time.time() - start_time
                self.adjust_cooldown(duration)

                self.output_text.insert(tk.END, f"Response code: {response.status_code}\n")
                self.output_text.see(tk.END)

                if response.status_code == 200:
                    match = re.search(r"JSON\.parse\('(\[.*?\])'\)", response.text)
                    if match:
                        json_str = match.group(1).replace("\\\"", "\"").replace("\\'", "'")
                        try:
                            data = json.loads(json_str)
                            # data is list of rows, each row a list
                            for row in data:
                                # Expected row structure:
                                # [Number, Operator, Circle Code, Circle Name, Ported]
                                if len(row) == 5:
                                    number_, operator, circle_code, circle_name, ported = row
                                else:
                                    # fallback if unexpected structure
                                    number_ = operator = circle_code = circle_name = ported = "Invalid Data"

                                values = (attempt, number_, operator, circle_code, circle_name, ported)
                                self.insert_row(values)
                            self.results.append((number, data, attempt))
                            idx += 1  # success - move to next number
                        except json.JSONDecodeError as e:
                            self.output_text.insert(tk.END, f"JSON decode error for number {number}: {e}\n")
                            self.output_text.see(tk.END)
                            self.output_text.insert(tk.END, f"Retrying number {number} after cooldown due to JSON error.\n")
                            self.output_text.see(tk.END)
                            self.wait_cooldown()
                    else:
                        self.output_text.insert(tk.END, f"No JSON found for number {number}. Waiting cooldown and retrying indefinitely...\n")
                        self.output_text.see(tk.END)
                        self.wait_cooldown()
                else:
                    self.output_text.insert(tk.END, f"Failed request for number {number} with status {response.status_code}\n")
                    self.output_text.see(tk.END)
                    self.insert_row((attempt, number, f"Error {response.status_code}", "", "", ""))
                    self.results.append((number, None, attempt))
                    idx += 1
            except Exception as e:
                self.output_text.insert(tk.END, f"Error during request for {number}: {e}\n")
                self.output_text.see(tk.END)
                self.insert_row((attempt, number, "Exception", "", "", ""))
                self.results.append((number, None, attempt))
                idx += 1

            self.progressbar["value"] = idx
            self.progress_label.config(text=f"Progress: {idx} / {len(self.numbers)}")

        self.output_text.insert(tk.END, "Bulk search completed.\n")
        self.output_text.see(tk.END)
        self.running = False
        self.run_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.countdown_label.config(text="Cooldown: 0.0s")

    def wait_cooldown(self):
        for remaining in range(int(self.cooldown * 10), 0, -1):
            if self.stop_flag:
                break
            self.countdown_label.config(text=f"Cooldown: {remaining / 10:.1f}s")
            time.sleep(0.1)
        self.countdown_label.config(text="Cooldown: 0.0s")

    def adjust_cooldown(self, last_duration):
        # Adjust cooldown based on last request time, bounded by min and max cooldown
        new_cooldown = max(self.min_cooldown, min(self.max_cooldown, last_duration + 1))
        if abs(new_cooldown - self.cooldown) > 0.1:
            self.output_text.insert(tk.END, f"Adjusting cooldown: {self.cooldown:.1f}s -> {new_cooldown:.1f}s\n")
            self.output_text.see(tk.END)
            self.cooldown = new_cooldown

    def insert_row(self, values):
        self.tree.insert("", "end", values=values)
        self.root.update_idletasks()

    def clear_table(self):
        for row in self.tree.get_children():
            self.tree.delete(row)

    def save_results(self):
        if not self.results:
            messagebox.showinfo("Info", "No results to save.")
            return
        filepath = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if not filepath:
            return
        try:
            save_data = [{"number": r[0], "data": r[1], "attempt": r[2]} for r in self.results]
            with open(filepath, "w") as f:
                json.dump(save_data, f, indent=4)
            messagebox.showinfo("Saved", f"Results saved to {filepath}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save file: {e}")

    def load_numbers(self):
        filepath = filedialog.askopenfilename(filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if not filepath:
            return
        try:
            with open(filepath, "r") as f:
                content = f.read()
            self.number_text.delete(1.0, tk.END)
            self.number_text.insert(tk.END, content)
            messagebox.showinfo("Loaded", "Phone numbers loaded successfully.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load file: {e}")

    def export_to_excel(self):
        try:
            import pandas as pd
        except ImportError:
            messagebox.showerror("Error", "Please install pandas to use Excel export feature:\npip install pandas openpyxl")
            return

        if not self.results:
            messagebox.showinfo("Info", "No results to export.")
            return

        filepath = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel files", "*.xlsx")])
        if not filepath:
            return

        try:
            # Build a list of dicts to export
            export_data = []
            for row_id in self.tree.get_children():
                row = self.tree.item(row_id)["values"]
                export_data.append({
                    "Attempt": row[0],
                    "Number": row[1],
                    "Operator": row[2],
                    "Circle Code": row[3],
                    "Circle Name": row[4],
                    "Ported": row[5],
                })
            df = pd.DataFrame(export_data)
            df.to_excel(filepath, index=False)
            messagebox.showinfo("Exported", f"Results exported to {filepath}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export Excel file: {e}")

    def copy_results(self):
        if not self.results:
            messagebox.showinfo("Info", "No results to copy.")
            return

        all_text = ""
        for row_id in self.tree.get_children():
            row = self.tree.item(row_id)["values"]
            all_text += "\t".join(str(cell) for cell in row) + "\n"

        self.root.clipboard_clear()
        self.root.clipboard_append(all_text)
        messagebox.showinfo("Copied", "All results copied to clipboard.")

if __name__ == "__main__":
    root = tk.Tk()
    app = MNPChecker(root)
    root.mainloop()
