import os

def get_project_root_path():
    project_root = os.path.dirname(os.path.abspath(__file__))
    return project_root