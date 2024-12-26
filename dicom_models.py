from pathlib import Path
from typing import Optional, List, Dict, Tuple
from collections import defaultdict
from pydantic import BaseModel, Field
import numpy as np
import SimpleITK as sitk
import pydicom
from loguru import logger


# Existing model classes remain the same
class PatientMetadata(BaseModel):
    """Patient-level metadata"""
    patient_id: str = Field(default="")
    patient_name: str = Field(default="")
    patient_birth_date: str = Field(default="")
    patient_sex: str = Field(default="")
    patient_age: str = Field(default="")
    patient_weight: float = Field(default=0.0)


class StudyMetadata(BaseModel):
    """Study-level metadata"""
    study_instance_uid: str = Field(default="")
    study_date: str = Field(default="")
    study_time: str = Field(default="")
    accession_number: str = Field(default="")
    study_id: str = Field(default="")
    study_description: str = Field(default="")
    referring_physician_name: str = Field(default="")
    patient_metadata: PatientMetadata = Field(default_factory=PatientMetadata)


class SeriesMetadata(BaseModel):
    """Series-level metadata"""
    series_instance_uid: str = Field(default="")
    series_number: int = Field(default=0)
    series_date: str = Field(default="")
    series_time: str = Field(default="")
    series_description: str = Field(default="")
    modality: str = Field(default="")
    body_part_examined: str = Field(default="")
    patient_position: str = Field(default="")
    protocol_name: str = Field(default="")
    manufacturers_model_name: str = Field(default="")
    device_serial_number: str = Field(default="")


class ImageMetadata(BaseModel):
    """Instance-level metadata"""
    sop_instance_uid: str = Field(default="")
    instance_number: int = Field(default=0)
    acquisition_number: int = Field(default=0)
    content_date: str = Field(default="")
    content_time: str = Field(default="")
    image_position: List[float] = Field(default_factory=list)
    image_orientation: List[float] = Field(default_factory=list)
    slice_location: float = Field(default=0.0)
    slice_thickness: float = Field(default=0.0)
    pixel_spacing: List[float] = Field(default_factory=list)
    rows: int = Field(default=0)
    columns: int = Field(default=0)
    window_center: float = Field(default=0.0)
    window_width: float = Field(default=0.0)
    rescale_intercept: float = Field(default=0.0)
    rescale_slope: float = Field(default=1.0)


class Series(BaseModel):
    metadata: SeriesMetadata
    image_metadata: List[ImageMetadata] = Field(default_factory=list)
    pixel_data: np.ndarray

    class Config:
        arbitrary_types_allowed = True


class Study(BaseModel):
    metadata: StudyMetadata
    series: Dict[str, Series] = Field(default_factory=dict)  # series_uid -> Series

    class Config:
        arbitrary_types_allowed = True


class DicomProcessor:
    @staticmethod
    def safe_get(dcm: pydicom.Dataset, tag, default=None):
        """Safely get a DICOM tag value"""
        try:
            value = dcm.get(tag)
            if value is None:
                return default
            return value
        except Exception:
            return default

    @staticmethod
    def extract_patient_metadata(dcm: pydicom.Dataset) -> PatientMetadata:
        """Extract patient-level metadata from a DICOM dataset"""
        try:
            weight = DicomProcessor.safe_get(dcm, "PatientWeight")
            return PatientMetadata(
                patient_id=str(DicomProcessor.safe_get(dcm, "PatientID", "")),
                patient_name=str(DicomProcessor.safe_get(dcm, "PatientName", "")),
                patient_birth_date=str(DicomProcessor.safe_get(dcm, "PatientBirthDate", "")),
                patient_sex=str(DicomProcessor.safe_get(dcm, "PatientSex", "")),
                patient_age=str(DicomProcessor.safe_get(dcm, "PatientAge", "")),
                patient_weight=float(weight) if weight is not None else 0.0
            )
        except Exception as e:
            logger.error(f"Error extracting patient metadata: {e}")
            return PatientMetadata()

    @staticmethod
    def extract_study_metadata(dcm: pydicom.Dataset) -> StudyMetadata:
        """Extract study-level metadata from a DICOM dataset"""
        try:
            return StudyMetadata(
                study_instance_uid=str(DicomProcessor.safe_get(dcm, "StudyInstanceUID", "")),
                study_date=str(DicomProcessor.safe_get(dcm, "StudyDate", "")),
                study_time=str(DicomProcessor.safe_get(dcm, "StudyTime", "")),
                accession_number=str(DicomProcessor.safe_get(dcm, "AccessionNumber", "")),
                study_id=str(DicomProcessor.safe_get(dcm, "StudyID", "")),
                study_description=str(DicomProcessor.safe_get(dcm, "StudyDescription", "")),
                referring_physician_name=str(DicomProcessor.safe_get(dcm, "ReferringPhysicianName", "")),
                patient_metadata=DicomProcessor.extract_patient_metadata(dcm)
            )
        except Exception as e:
            logger.error(f"Error extracting study metadata: {e}")
            return StudyMetadata()

    @staticmethod
    def extract_series_metadata(dcm: pydicom.Dataset) -> SeriesMetadata:
        """Extract series-level metadata from a DICOM dataset"""
        try:
            series_number = DicomProcessor.safe_get(dcm, "SeriesNumber")
            return SeriesMetadata(
                series_instance_uid=str(DicomProcessor.safe_get(dcm, "SeriesInstanceUID", "")),
                series_number=int(series_number) if series_number is not None else 0,
                series_date=str(DicomProcessor.safe_get(dcm, "SeriesDate", "")),
                series_time=str(DicomProcessor.safe_get(dcm, "SeriesTime", "")),
                series_description=str(DicomProcessor.safe_get(dcm, "SeriesDescription", "")),
                modality=str(DicomProcessor.safe_get(dcm, "Modality", "")),
                body_part_examined=str(DicomProcessor.safe_get(dcm, "BodyPartExamined", "")),
                patient_position=str(DicomProcessor.safe_get(dcm, "PatientPosition", "")),
                protocol_name=str(DicomProcessor.safe_get(dcm, "ProtocolName", "")),
                manufacturers_model_name=str(DicomProcessor.safe_get(dcm, "ManufacturerModelName", "")),
                device_serial_number=str(DicomProcessor.safe_get(dcm, "DeviceSerialNumber", ""))
            )
        except Exception as e:
            logger.error(f"Error extracting series metadata: {e}")
            return SeriesMetadata()

    @staticmethod
    def extract_image_metadata(dcm: pydicom.Dataset, idx: int = 0) -> ImageMetadata:
        """Extract instance-level metadata from a DICOM dataset"""
        try:
            metadata = ImageMetadata(
                sop_instance_uid=str(DicomProcessor.safe_get(dcm, "SOPInstanceUID", "")),
                instance_number=int(DicomProcessor.safe_get(dcm, "InstanceNumber", idx)),
                acquisition_number=int(DicomProcessor.safe_get(dcm, "AcquisitionNumber", 0)),
                content_date=str(DicomProcessor.safe_get(dcm, "ContentDate", "")),
                content_time=str(DicomProcessor.safe_get(dcm, "ContentTime", "")),
                slice_location=float(DicomProcessor.safe_get(dcm, "SliceLocation", 0.0)),
                slice_thickness=float(DicomProcessor.safe_get(dcm, "SliceThickness", 0.0)),
                rows=int(DicomProcessor.safe_get(dcm, "Rows", 0)),
                columns=int(DicomProcessor.safe_get(dcm, "Columns", 0))
            )

            # Handle window center/width which might be multiple values
            window_center = DicomProcessor.safe_get(dcm, "WindowCenter")
            window_width = DicomProcessor.safe_get(dcm, "WindowWidth")
            if window_center is not None:
                if isinstance(window_center, pydicom.multival.MultiValue):
                    metadata.window_center = float(window_center[0])
                else:
                    metadata.window_center = float(window_center)
            if window_width is not None:
                if isinstance(window_width, pydicom.multival.MultiValue):
                    metadata.window_width = float(window_width[0])
                else:
                    metadata.window_width = float(window_width)

            # Handle rescale values
            metadata.rescale_intercept = float(DicomProcessor.safe_get(dcm, "RescaleIntercept", 0.0))
            metadata.rescale_slope = float(DicomProcessor.safe_get(dcm, "RescaleSlope", 1.0))

            # Handle image position and orientation
            image_position = DicomProcessor.safe_get(dcm, "ImagePositionPatient")
            if image_position is not None:
                metadata.image_position = [float(x) for x in image_position]

            image_orientation = DicomProcessor.safe_get(dcm, "ImageOrientationPatient")
            if image_orientation is not None:
                metadata.image_orientation = [float(x) for x in image_orientation]

            pixel_spacing = DicomProcessor.safe_get(dcm, "PixelSpacing")
            if pixel_spacing is not None:
                metadata.pixel_spacing = [float(x) for x in pixel_spacing]

            return metadata
        except Exception as e:
            logger.error(f"Error extracting image metadata: {e}")
            return ImageMetadata()

    @staticmethod
    def get_dicom_tags(filename: str) -> Tuple[str, str, str]:
        """Extract study and series UIDs from a DICOM file"""
        try:
            dcm = pydicom.dcmread(filename, stop_before_pixels=True)
            study_uid = str(DicomProcessor.safe_get(dcm, "StudyInstanceUID", ""))
            series_uid = str(DicomProcessor.safe_get(dcm, "SeriesInstanceUID", ""))
            sop_uid = str(DicomProcessor.safe_get(dcm, "SOPInstanceUID", ""))
            return study_uid, series_uid, sop_uid
        except Exception as e:
            logger.error(f"Error reading DICOM tags from {filename}: {e}")
            return "", "", ""

    @staticmethod
    def organize_dicom_files(directory: Path) -> Dict[str, Dict[str, List[str]]]:
        """
        Organize DICOM files by study UID and series UID
        Returns: Dict[study_uid, Dict[series_uid, List[filenames]]]
        """
        study_series_files = defaultdict(lambda: defaultdict(list))

        # Recursively find all files in directory
        for file_path in directory.rglob("*"):
            if file_path.is_file():
                try:
                    study_uid, series_uid, _ = DicomProcessor.get_dicom_tags(str(file_path))
                    if study_uid and series_uid:
                        study_series_files[study_uid][series_uid].append(str(file_path))
                except Exception:
                    continue  # Skip non-DICOM files

        return study_series_files

    @staticmethod
    def load_series(filenames: List[str]) -> Optional[Series]:
        """Load a single series from a list of DICOM filenames"""
        try:
            # Use SimpleITK for image loading
            reader = sitk.ImageSeriesReader()
            reader.SetFileNames(filenames)
            image = reader.Execute()
            pixel_array = sitk.GetArrayFromImage(image)

            # Use pydicom for metadata
            first_dcm = pydicom.dcmread(filenames[0], stop_before_pixels=True)
            series_metadata = DicomProcessor.extract_series_metadata(first_dcm)

            # Load metadata for each slice
            image_metadata_list = []
            for idx, filename in enumerate(filenames):
                dcm = pydicom.dcmread(filename, stop_before_pixels=True)
                slice_metadata = DicomProcessor.extract_image_metadata(dcm, idx)
                image_metadata_list.append(slice_metadata)

            return Series(
                metadata=series_metadata,
                image_metadata=image_metadata_list,
                pixel_data=pixel_array
            )

        except Exception as e:
            logger.error(f"Error loading series: {e}")
            return None

    @staticmethod
    def load_dicom_studies(directory: Path) -> Dict[str, Study]:
        """
        Load all DICOM studies from a directory
        Returns: Dict[study_uid, Study]
        """
        try:
            # First, organize files by study and series
            study_series_files = DicomProcessor.organize_dicom_files(directory)
            studies = {}

            for study_uid, series_dict in study_series_files.items():
                if not series_dict:
                    continue

                # Get study metadata from first file of first series
                first_series_files = next(iter(series_dict.values()))
                if not first_series_files:
                    continue

                # Use pydicom for metadata extraction
                first_dcm = pydicom.dcmread(first_series_files[0], stop_before_pixels=True)
                study_metadata = DicomProcessor.extract_study_metadata(first_dcm)

                # Create new study
                study = Study(metadata=study_metadata)

                # Load each series in the study
                for series_uid, filenames in series_dict.items():
                    series = DicomProcessor.load_series(filenames)
                    if series:
                        study.series[series_uid] = series

                studies[study_uid] = study

            return studies

        except Exception as e:
            logger.error(f"Error loading DICOM studies: {e}")
            return {}

    @staticmethod
    def normalize_image(image: np.ndarray) -> np.ndarray:
        """Normalize image to 0-1 range"""
        min_val = np.min(image)
        max_val = np.max(image)
        return (image - min_val) / (max_val - min_val) if max_val > min_val else image