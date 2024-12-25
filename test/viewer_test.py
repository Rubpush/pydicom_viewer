import pytest
import tkinter as tk
from pathlib import Path
import numpy as np
import pydicom

# Import your viewer class - adjust the import path as needed
from viewer import DicomViewer


@pytest.fixture
def viewer():
    """Create a fresh instance of DicomViewer for each test"""
    root = tk.Tk()
    viewer = DicomViewer(root)
    yield viewer
    root.destroy()


class TestDicomViewer:
    def test_initial_state(self, viewer):
        """Test the initial state of the viewer"""
        assert viewer.dicom_data is None
        assert viewer.current_slice == 0
        assert viewer.slices is None
        assert float(viewer.slice_slider.get()) == 0

    def test_load_dicom_series(self, viewer, get_pancreas_ct_data):
        """Test loading DICOM series from the test data"""
        data_path = get_pancreas_ct_data

        # Load the test data
        loaded_data = viewer.load_dicom_series(str(data_path))

        # Basic checks
        assert loaded_data is not None
        assert isinstance(loaded_data, list)
        assert len(loaded_data) > 0
        assert isinstance(loaded_data[0], np.ndarray)

    def test_preprocess_dicom(self, viewer, get_pancreas_ct_data):
        """Test DICOM preprocessing"""
        data_path = get_pancreas_ct_data

        # Load a single DICOM file for testing
        test_file = next(data_path.glob('*.dcm'))
        dicom_file = pydicom.dcmread(str(test_file))

        # Test preprocessing
        processed_data = viewer.preprocess_dicom(dicom_file)
        assert isinstance(processed_data, np.ndarray)
        assert processed_data.ndim == 2  # Should be 2D image

    def test_clear_viewer(self, viewer, get_pancreas_ct_data):
        """Test clearing the viewer"""
        # First load some data
        viewer.load_dicom_series(str(get_pancreas_ct_data))

        # Then clear it
        viewer.clear_viewer()

        # Check if everything is reset
        assert viewer.dicom_data is None
        assert viewer.current_slice == 0
        assert viewer.slices is None
        assert float(viewer.slice_slider.get()) == 0
        assert viewer.slice_label.cget("text") == "Slice: 0/0"

    def test_update_slice(self, viewer, get_pancreas_ct_data):
        """Test slice updating"""
        # Load data
        viewer.load_dicom_series(str(get_pancreas_ct_data))
        initial_slice = viewer.current_slice

        # Move to next slice
        viewer.slice_slider.set(initial_slice + 1)
        viewer.update_slice()

        assert viewer.current_slice == initial_slice + 1
        assert viewer.slice_label.cget("text") == f"Slice: {initial_slice + 2}/{viewer.slices}"

    def test_invalid_dicom_directory(self, viewer, tmp_path):
        """Test handling of invalid DICOM directory"""
        # Create an empty temporary directory
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        # Try to load from empty directory
        result = viewer.load_dicom_series(str(empty_dir))
        assert result is None

    def test_menu_existence(self, viewer):
        """Test that menu items exist and are properly configured"""
        file_menu = viewer.file_menu

        # Check menu items
        assert "Load DICOM" in file_menu.entrycget(0, "label")
        assert "Clear Viewer" in file_menu.entrycget(1, "label")
        assert "Exit" in file_menu.entrycget(3, "label")  # Index 3 due to separator

    @pytest.mark.parametrize("slice_number", [0, 1, -1])
    def test_slice_boundary_conditions(self, viewer, get_pancreas_ct_data, slice_number):
        """Test viewer behavior with different slice numbers"""
        # Load data
        viewer.load_dicom_series(str(get_pancreas_ct_data))
        total_slices = viewer.slices

        if slice_number == -1:
            slice_number = total_slices - 1

        # Set slice if within bounds
        if 0 <= slice_number < total_slices:
            viewer.slice_slider.set(slice_number)
            viewer.update_slice()
            assert viewer.current_slice == slice_number
            assert viewer.slice_label.cget("text") == f"Slice: {slice_number + 1}/{total_slices}"


class TestDicomViewerIntegration:
    def test_full_workflow(self, viewer, get_pancreas_ct_data):
        """Test a complete workflow of loading, navigating, and clearing data"""
        # Initial state
        assert viewer.dicom_data is None

        # Load data
        data_path = get_pancreas_ct_data
        viewer.load_dicom_series(str(data_path))
        assert viewer.dicom_data is not None
        initial_slices = viewer.slices

        # Navigate through slices
        middle_slice = initial_slices // 2
        viewer.slice_slider.set(middle_slice)
        viewer.update_slice()
        assert viewer.current_slice == middle_slice

        # Clear viewer
        viewer.clear_viewer()
        assert viewer.dicom_data is None
        assert viewer.current_slice == 0