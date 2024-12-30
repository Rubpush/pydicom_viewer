# Project description
This is a simple python based GUI DICOM viewer. 
Currently the viewer only offers direct data visualisation functionality and dicom header inspection. 

## Installation

1.Use Poetry for virtual environment creation and installation of dependencies found in the pyproject.toml file.

`
poetry install
`

2.Select the python.exe installed in the virtual environment as project interpreter

## Running the project

1. Run the project by running the viewer.py file. No configuration is needed.
   
`
poetry run viewer.py
`
2. To load a dicom series, go to the top left corner of the GUI, click on 'file'

3.  select a folder containing the dicom files of a single series.
