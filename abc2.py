import time
import os
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import difflib
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext


class Watcher:
    def __init__(self, directory_to_watch, stop_callback, output_callback):
        self.DIRECTORY_TO_WATCH = directory_to_watch
        self.observer = Observer()
        self.stop_callback = stop_callback
        self.output_callback = output_callback

    def run(self):
        event_handler = Handler(self.output_callback)
        self.observer.schedule(event_handler, self.DIRECTORY_TO_WATCH, recursive=True)
        self.observer.start()
        try:
            while not self.stop_callback():
                time.sleep(1)
        except KeyboardInterrupt:
            self.observer.stop()
        self.observer.join()

    def stop(self):
        self.observer.stop()


class Handler(FileSystemEventHandler):
    file_snapshots = {}

    def __init__(self, output_callback):
        self.output_callback = output_callback

    @staticmethod
    def get_file_content(path):
        try:
            with open(path, 'r') as file:
                return file.readlines()  # Capture the lines of the file as a list
        except Exception as e:
            return None

    def print_readable_diff(self, old_content, new_content, filepath):
        if old_content is None:
            self.output_callback(f"Old content for {filepath} is missing or unreadable.")
            return
        if new_content is None:
            self.output_callback(f"New content for {filepath} is missing or unreadable.")
            return

        # Compute the diff between the old and new content
        diff = list(difflib.ndiff(old_content, new_content))
        added, removed = [], []

        for line in diff:
            if line.startswith('+ '):
                added.append(line[2:].strip())  # Line added
            elif line.startswith('- '):
                removed.append(line[2:].strip())  # Line removed

        if added or removed:
            self.output_callback(f"\nChanges in {filepath}:")
            if added:
                self.output_callback("Added lines:")
                for line in added:
                    self.output_callback(f"  + {line}")

            if removed:
                self.output_callback("Removed lines:")
                for line in removed:
                    self.output_callback(f"  - {line}")
        else:
            # Only print this if both added and removed are empty
            self.output_callback(f"No content changes detected in {filepath}.")

    def on_modified(self, event):
        if not event.is_directory:
            current_content = self.get_file_content(event.src_path)
            if current_content is None:
                self.output_callback(f"Unable to read the modified file: {event.src_path}")
                return

            # If no previous snapshot exists, initialize it with the current content
            if event.src_path not in self.file_snapshots:
                self.output_callback(f"First modification detected, initializing snapshot for {event.src_path}.")
                self.file_snapshots[event.src_path] = current_content
                self.output_callback("Initial snapshot stored, no content changes to compare yet.")
            else:
                old_content = self.file_snapshots[event.src_path]
                self.output_callback(f"\nModification detected in {event.src_path}:")
                self.print_readable_diff(old_content, current_content, event.src_path)

                # Update the snapshot after comparison
                self.file_snapshots[event.src_path] = current_content


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("File Watcher")

        self.directory = None
        self.watcher_thread = None
        self.watcher = None
        self.stop_flag = False

        self.label = tk.Label(root, text="Select a directory to watch:")
        self.label.pack(pady=10)

        self.select_btn = tk.Button(root, text="Select Directory", command=self.select_directory)
        self.select_btn.pack(pady=5)

        self.start_btn = tk.Button(root, text="Start Watching", command=self.start_watching, state="disabled")
        self.start_btn.pack(pady=5)

        self.stop_btn = tk.Button(root, text="Stop Watching", command=self.stop_watching, state="disabled")
        self.stop_btn.pack(pady=5)

        # Text box to display output
        self.text_area = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=60, height=20)
        self.text_area.pack(pady=10)

    def select_directory(self):
        self.directory = filedialog.askdirectory()
        if self.directory:
            self.start_btn.config(state="normal")
            messagebox.showinfo("Directory Selected", f"Watching directory: {self.directory}")

    def start_watching(self):
        if self.directory:
            self.stop_flag = False
            self.watcher = Watcher(self.directory, self.is_stopped, self.append_output)
            self.watcher_thread = threading.Thread(target=self.watcher.run)
            self.watcher_thread.start()

            self.start_btn.config(state="disabled")
            self.stop_btn.config(state="normal")

    def stop_watching(self):
        if self.watcher:
            self.stop_flag = True
            self.watcher.stop()
            self.watcher_thread.join()

            self.start_btn.config(state="normal")
            self.stop_btn.config(state="disabled")

        # Exit the application
        self.root.quit()


    def is_stopped(self):
        return self.stop_flag

    def append_output(self, text):
        """Append the output to the text area in the GUI."""
        self.text_area.insert(tk.END, text + "\n")
        self.text_area.see(tk.END)  # Auto-scroll to the bottom


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
