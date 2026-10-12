"""Compatibility service boundary for class/personal project operations."""

from project_core import (
    create_class_project,
    create_personal_project,
    delete_file,
    download_file,
    get_project_files,
    load_all_complete_personal_projects,
    load_class_projects,
    load_personal_projects,
    student_has_uploaded,
    update_project_status,
    upload_file,
)

__all__ = [
    "create_class_project",
    "create_personal_project",
    "delete_file",
    "download_file",
    "get_project_files",
    "load_all_complete_personal_projects",
    "load_class_projects",
    "load_personal_projects",
    "student_has_uploaded",
    "update_project_status",
    "upload_file",
]
