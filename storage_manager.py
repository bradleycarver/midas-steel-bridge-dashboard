import os
import shutil
import platform
import subprocess
import sys

def get_bundle_dir():
    """Path to the internal bundled files (Templates)"""
    if hasattr(sys, '_MEIPASS'):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))

def get_user_dir():
    """Path to the folder where the EXE sits"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

# --- DEFINITIONS ---
# Internal (Read-only, bundled inside EXE)
TEMPLATES_DIR = os.path.join(get_bundle_dir(), "templates")

# External (User interacts with these)
ROOT_DIR = get_user_dir()
CURRENT_DIR = os.path.join(ROOT_DIR, "current")
ARCHIVE_DIR = os.path.join(ROOT_DIR, "archive")

def ensure_directories():
    for d in [CURRENT_DIR, ARCHIVE_DIR]:
        if not os.path.exists(d):
            os.makedirs(d)

def save_iteration(name):
    """Copies contents of 'current' to 'archive/name'."""
    destination = os.path.join(ARCHIVE_DIR, name)
    if os.path.exists(destination):
        raise ValueError("An iteration with this name already exists.")
    
    shutil.copytree(CURRENT_DIR, destination)
    
    try:
        os.utime(destination, None)
    except Exception:
        pass
        
    return destination

def delete_iteration(name):
    target = os.path.join(ARCHIVE_DIR, name)
    if os.path.exists(target):
        shutil.rmtree(target)

def get_iterations():
    if not os.path.exists(ARCHIVE_DIR):
        return []
    items = os.listdir(ARCHIVE_DIR)
    
    folders = [item for item in items if os.path.isdir(os.path.join(ARCHIVE_DIR, item))]
    folders.sort(key=lambda x: os.path.getmtime(os.path.join(ARCHIVE_DIR, x)), reverse=True)
    
    return folders

def open_folder(path):
    abs_path = os.path.abspath(path)
    if platform.system() == "Windows":
        os.startfile(abs_path)
    elif platform.system() == "Darwin":
        subprocess.Popen(["open", abs_path])
    else:
        subprocess.Popen(["xdg-open", abs_path])