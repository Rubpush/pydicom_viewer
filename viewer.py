import tkinter as tk
from tkinter import ttk, filedialog
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import pydicom
import numpy as np


class DicomViewer:
    def __init__(self, root):
        self.root = root
        self.root.title("DICOM Viewer")

        # Instance variables
        self.dicom_data = None
        self.current_slice = 0
        self.slices = None

        # Setup the menu bar
        self.setup_menu()

        # Setup the UI
        self.setup_ui()

    def setup_menu(self):
        """Setup the menu bar with File menu"""
        # Create menu bar
        self.menu_bar = tk.Menu(self.root)
        self.root.config(menu=self.menu_bar)

        # Create File menu
        self.file_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="File", menu=self.file_menu)

        # Add menu items
        self.file_menu.add_command(label="Load DICOM", command=self.load_dicom)
        self.file_menu.add_command(label="Clear Viewer", command=self.clear_viewer)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Exit", command=self.root.quit)

    def clear_viewer(self):
        """Clear the current DICOM data and reset the viewer"""
        self.dicom_data = None
        self.current_slice = 0
        self.slices = None

        # Reset slider
        self.slice_slider.configure(to=0)
        self.slice_slider.set(0)

        # Clear the display
        self.ax.clear()
        self.ax.axis('off')
        self.canvas.draw()

        # Reset slice label
        self.slice_label.configure(text="Slice: 0/0")

    def setup_ui(self):
        # Create main frame
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Create matplotlib figure
        self.fig = Figure(figsize=(6, 6))
        self.ax = self.fig.add_subplot(111)

        # Create canvas
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.main_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Create slider
        self.slice_slider = ttk.Scale(
            self.main_frame,
            from_=0,
            to=0,
            orient=tk.HORIZONTAL,
            command=self.update_slice
        )
        self.slice_slider.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)

        # # Create load button
        # self.load_button = ttk.Button(
        #     self.main_frame,
        #     text="Load DICOM",
        #     command=self.load_dicom
        # )
        # self.load_button.grid(row=2, column=0, sticky=(tk.W), pady=5)

        # Add slice number label
        self.slice_label = ttk.Label(self.main_frame, text="Slice: 0/0")
        self.slice_label.grid(row=2, column=1, sticky=(tk.E), pady=5)

        # Configure grid weights
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.columnconfigure(1, weight=1)

    def load_dicom(self):
        """Load DICOM data from a directory"""
        directory = filedialog.askdirectory()
        if directory:
            try:
                # Load all DICOM files in the directory
                self.dicom_data = self.load_dicom_series(directory)
                if self.dicom_data is not None:
                    self.slices = len(self.dicom_data)
                    # Update slider range
                    self.slice_slider.configure(to=self.slices - 1)
                    # Display first slice
                    self.current_slice = 0
                    self.update_display()
            except Exception as e:
                tk.messagebox.showerror("Error", f"Error loading DICOM: {str(e)}")

    def load_dicom_series(self, directory):
        """Load and preprocess DICOM series from directory"""
        # This method can be extended to handle different DICOM series formats
        try:
            # Get all DICOM files in directory
            import os
            dicom_files = [
                pydicom.dcmread(os.path.join(directory, f))
                for f in os.listdir(directory)
                if f.endswith('.dcm')
            ]

            # Sort by instance number if available
            dicom_files.sort(key=lambda x: x.InstanceNumber)

            # Convert to numpy array for faster display
            return [self.preprocess_dicom(dcm) for dcm in dicom_files]
        except Exception as e:
            print(f"Error loading DICOM series: {str(e)}")
            return None

    def preprocess_dicom(self, dicom_file):
        """Preprocess DICOM data for display"""
        # Convert to Hounsfield Units (HU) if CT scan
        try:
            intercept = dicom_file.RescaleIntercept
            slope = dicom_file.RescaleSlope
            data = dicom_file.pixel_array * slope + intercept
            return data
        except:
            # If not CT or missing attributes, return pixel array directly
            return dicom_file.pixel_array

    def update_slice(self, event=None):
        """Update display when slider is moved"""
        if self.dicom_data is not None:
            self.current_slice = int(self.slice_slider.get())
            self.update_display()

    def update_display(self):
        """Update the image display"""
        if self.dicom_data is not None:
            # Clear previous image
            self.ax.clear()

            # Display current slice
            self.ax.imshow(
                self.dicom_data[self.current_slice],
                cmap='gray'
            )

            # Update slice label
            self.slice_label.configure(
                text=f"Slice: {self.current_slice + 1}/{self.slices}"
            )

            # Remove axis labels
            self.ax.axis('off')

            # Update canvas
            self.canvas.draw()


def main():
    root = tk.Tk()
    app = DicomViewer(root)
    root.mainloop()


if __name__ == "__main__":
    main()