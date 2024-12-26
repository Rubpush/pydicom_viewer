from PyQt6 import QtCore, QtWidgets, QtGui
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from pathlib import Path
import sys
from loguru import logger

from dicom_models import DicomProcessor, Study


class ImageCanvas(FigureCanvasQTAgg):
    def __init__(self, parent=None, width=6, height=6):
        fig = Figure(figsize=(width, height))
        self.axes = fig.add_subplot(111)
        super().__init__(fig)
        self.setParent(parent)

    def update_image(self, image):
        self.axes.clear()
        self.axes.imshow(image, cmap='gray')
        self.axes.axis('off')
        self.draw()


class LogWidget(QtWidgets.QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)

    def write(self, text):
        self.append(text)


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.studies = {}  # Dict[study_uid, Study]
        self.current_study_uid = None
        self.current_series_uid = None
        self.current_slice = 0

        self.setup_ui()
        self.setup_logging()
        logger.info("DICOM Viewer initialized")

    def setup_ui(self):
        self.setWindowTitle("DICOM Viewer")
        self.resize(1400, 800)

        # Central widget
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        layout = QtWidgets.QHBoxLayout(central_widget)

        # Left panel for image
        left_panel = QtWidgets.QVBoxLayout()

        # Study selector
        study_layout = QtWidgets.QHBoxLayout()
        study_layout.addWidget(QtWidgets.QLabel("Study:"))
        self.study_combo = QtWidgets.QComboBox()
        self.study_combo.currentIndexChanged.connect(self.change_study)
        study_layout.addWidget(self.study_combo)
        left_panel.addLayout(study_layout)

        # Series selector
        series_layout = QtWidgets.QHBoxLayout()
        series_layout.addWidget(QtWidgets.QLabel("Series:"))
        self.series_combo = QtWidgets.QComboBox()
        self.series_combo.currentIndexChanged.connect(self.change_series)
        series_layout.addWidget(self.series_combo)
        left_panel.addLayout(series_layout)

        # Image canvas
        self.canvas = ImageCanvas(self)
        left_panel.addWidget(self.canvas)

        # Slice navigation
        slice_layout = QtWidgets.QHBoxLayout()
        self.slice_slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.slice_slider.valueChanged.connect(self.update_slice)
        self.slice_label = QtWidgets.QLabel("Slice: 0/0")
        slice_layout.addWidget(self.slice_slider)
        slice_layout.addWidget(self.slice_label)
        left_panel.addLayout(slice_layout)

        # Right panel for metadata and log
        right_panel = QtWidgets.QVBoxLayout()

        # Patient Information
        self.patient_info = QtWidgets.QTextEdit()
        self.patient_info.setReadOnly(True)
        self.patient_info.setMaximumHeight(100)
        right_panel.addWidget(QtWidgets.QLabel("Patient Information:"))
        right_panel.addWidget(self.patient_info)

        # Study Information
        self.study_info = QtWidgets.QTextEdit()
        self.study_info.setReadOnly(True)
        self.study_info.setMaximumHeight(100)
        right_panel.addWidget(QtWidgets.QLabel("Study Information:"))
        right_panel.addWidget(self.study_info)

        # Series Information
        self.series_info = QtWidgets.QTextEdit()
        self.series_info.setReadOnly(True)
        self.series_info.setMaximumHeight(150)
        right_panel.addWidget(QtWidgets.QLabel("Series Information:"))
        right_panel.addWidget(self.series_info)

        # Image Information
        self.image_info = QtWidgets.QTextEdit()
        self.image_info.setReadOnly(True)
        self.image_info.setMaximumHeight(150)
        right_panel.addWidget(QtWidgets.QLabel("Image Information:"))
        right_panel.addWidget(self.image_info)

        # Add a separator line
        separator = QtWidgets.QFrame()
        separator.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        separator.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        separator.setLineWidth(1)
        right_panel.addSpacing(10)
        right_panel.addWidget(separator)
        right_panel.addSpacing(10)

        # Log display
        self.log_widget = LogWidget()
        right_panel.addWidget(QtWidgets.QLabel("Log:"))
        right_panel.addWidget(self.log_widget)

        # Add panels to main layout
        layout.addLayout(left_panel, stretch=2)
        layout.addLayout(right_panel, stretch=1)

        # Setup menu
        self.setup_menu()

    def setup_menu(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("File")

        load_action = QtGui.QAction("Load DICOM", self)
        load_action.triggered.connect(self.load_dicom)
        file_menu.addAction(load_action)

        exit_action = QtGui.QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

    def setup_logging(self):
        logger.remove()
        logger.add(self.log_widget.write, format="{time:HH:mm:ss} | {message}")

    def format_patient_info(self, study: Study) -> str:
        patient = study.metadata.patient_metadata
        return f"""
Patient Name: {patient.patient_name}
Patient ID: {patient.patient_id}
Birth Date: {patient.patient_birth_date}
Sex: {patient.patient_sex}
Age: {patient.patient_age}
Weight: {patient.patient_weight:.1f}
""".strip()

    def format_study_info(self, study: Study) -> str:
        metadata = study.metadata
        return f"""
Study Instance UID: {metadata.study_instance_uid}
Study Date: {metadata.study_date}
Study Time: {metadata.study_time}
Study Description: {metadata.study_description}
Study ID: {metadata.study_id}
Accession Number: {metadata.accession_number}
Referring Physician: {metadata.referring_physician_name}
""".strip()

    def format_series_info(self, series_metadata) -> str:
        return f"""
Series Instance UID: {series_metadata.series_description}
Series Number: {series_metadata.series_number}
Series Description: {series_metadata.series_description}
Modality: {series_metadata.modality}
Body Part: {series_metadata.body_part_examined}
Protocol: {series_metadata.protocol_name}
Patient Position: {series_metadata.patient_position}
Device: {series_metadata.manufacturers_model_name}
Device S/N: {series_metadata.device_serial_number}
""".strip()

    def format_image_info(self, image_metadata) -> str:
        spacing_str = ', '.join(
            f'{x:.2f}' for x in image_metadata.pixel_spacing) if image_metadata.pixel_spacing else 'N/A'
        return f"""
Instance Number: {image_metadata.instance_number}
Acquisition Number: {image_metadata.acquisition_number}
Slice Location: {image_metadata.slice_location:.2f}
Slice Thickness: {image_metadata.slice_thickness:.2f}
Window Center: {image_metadata.window_center:.1f}
Window Width: {image_metadata.window_width:.1f}
Image Size: {image_metadata.rows}x{image_metadata.columns}
Pixel Spacing: {spacing_str}
""".strip()

    def load_dicom(self):
        directory = QtWidgets.QFileDialog.getExistingDirectory(self, "Select DICOM Directory")
        if directory:
            logger.info(f"Loading DICOM from {directory}")
            self.studies = DicomProcessor.load_dicom_studies(Path(directory))

            if self.studies:
                # Update study selector
                self.study_combo.clear()
                for study_uid, study in self.studies.items():
                    desc = f"Study {study.metadata.study_date}: {study.metadata.study_description}"
                    self.study_combo.addItem(desc, study_uid)

                # Load first study
                self.change_study(0)
                logger.info(f"Loaded {len(self.studies)} studies successfully")
            else:
                logger.error("No DICOM studies found in directory")

    def change_study(self, index):
        if index >= 0 and self.studies:
            study_uid = self.study_combo.itemData(index)
            self.current_study_uid = study_uid
            study = self.studies[study_uid]

            # Update series selector
            self.series_combo.clear()
            for series_uid, series in study.series.items():
                desc = f"Series {series.metadata.series_number}: {series.metadata.series_description}"
                self.series_combo.addItem(desc, series_uid)

            # Update study and patient information
            self.patient_info.setText(self.format_patient_info(study))
            self.study_info.setText(self.format_study_info(study))

            # Load first series
            if study.series:
                self.change_series(0)

    def change_series(self, index):
        if index >= 0 and self.current_study_uid:
            series_uid = self.series_combo.itemData(index)
            self.current_series_uid = series_uid
            study = self.studies[self.current_study_uid]
            series = study.series[series_uid]

            # Update slider
            num_slices = len(series.image_metadata)
            self.slice_slider.setMaximum(num_slices - 1)
            self.slice_slider.setValue(0)
            self.slice_label.setText(f"Slice: 1/{num_slices}")

            # Update series information
            self.series_info.setText(self.format_series_info(series.metadata))

            # Show first slice
            self.update_slice(0)

    def update_slice(self, slice_idx):
        if not (self.current_study_uid and self.current_series_uid):
            return

        study = self.studies[self.current_study_uid]
        series = study.series[self.current_series_uid]

        self.current_slice = slice_idx
        total_slices = len(series.image_metadata)
        self.slice_label.setText(f"Slice: {slice_idx + 1}/{total_slices}")

        # Update image
        normalized_image = DicomProcessor.normalize_image(series.pixel_data[slice_idx])
        self.canvas.update_image(normalized_image)

        # Update image metadata
        self.image_info.setText(self.format_image_info(series.image_metadata[slice_idx]))


def main():
    app = QtWidgets.QApplication(sys.argv)
    viewer = MainWindow()
    viewer.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()