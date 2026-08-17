import os
import re
import platform
from pathlib import Path


def is_windows():
    """ Check if the OS is Windows. """
    return os.name == "nt"


def get_os_type():
    """Returns the OS type: 'macos', 'linux', 'windows', or 'unknown'."""
    system = platform.system()
    if system == "Darwin":
        return "macos"
    elif system == "Linux":
        return "linux"
    elif system == "Windows":
        return "windows"
    else:
        return "unknown"



# Function to check if files exist
def check_files(files):
    """ Check if all files exist. """
    return all(check_file(file) for file in files)


def check_file(file):
	""" Check if a single file exists. """
	# Use `isfile()` vs. `exists()` because `exists()` can check for 
	# directories.
	if not os.path.isfile(file):
			print(f"Warning: File '{file}' does not exist.")
			return False
	return True


# Splits a PascalCase class name into a list: `["Pascal", "Case"]`.
def split_clazz_name(clazz):
    """ Split class name into words based on uppercase letters. """
    return re.findall(r'[A-Z][a-z]*', clazz)


# Converts a list to a space-separated string.
def lst_to_str(lst):
    s = ""
    for i in range(0, len(lst)):
        if i + 1 == len(lst):
            s += lst[i]
        else:
            s += lst[i] + " "
    return s

# CREDIT: OpenAI's ChatGPT
def fmtout(s: str, width: int = 80, border: str = "#") -> str:
    """Returns a formatted output string with the parameter string centered."""
    pad = (width - len(s) - 2) // 2  # Subtract 2 for spaces around the message

    # Construct the header
    top_bottom = border * width
    middle = f"{border * pad} {s} {border * pad}".ljust(width, border)

    return f"{top_bottom}\n{middle}\n{top_bottom}"

# Given a config milestone name, return a formatted GitHub(R) URL request
# version.
def fmt_milestone(s):
    return re.sub(r"(\D)(\d+)", r"\1-\2", s) 

# Returns dictionary of classes, with class as key and string list of methods
# as value.
def methods_to_strlst(config):
    if "methods" not in config:
        raise KeyError(
                f"'methods' key not found in config. Config parsing error."
        )

    strlst = {}
    for clazz, items in config["methods"].items():
        strlst[clazz] = []
        for name, decl in items.items():
            ret = decl["return"]
            para = decl["params"]
            strlst[clazz].append(f"{ret} {name}")

    return strlst


def find_files(search_dir, class_name, file_extensions):
    """
    Cross-platform file finder for class source files.
    
    Args:
        search_dir (str): Directory to search in
        class_name (str): Name of the class (e.g., "HashTable")
        file_extensions (list): List of extensions to search for (e.g., ["cpp", "cxx", "cc"])
    
    Returns:
        list: List of found files relative to search_dir
    
    Example:
        find_files(".", "HashTable", ["cpp", "cxx", "cc"])
        # Returns: ["HashTable.cpp"] or ["hash_table.cpp"] etc.
    """
    if not os.path.isdir(search_dir):
        return []
    
    # Split PascalCase class name into words
    class_words = split_clazz_name(class_name)
    
    found_files = []
    
    # Walk through directory
    for root, dirs, files in os.walk(search_dir):
        for filename in files:
            # Check if file has one of the requested extensions
            file_ext = filename.split(".")[-1].lower() if "." in filename else ""
            
            if file_ext not in [ext.lower() for ext in file_extensions]:
                continue
            
            # Check if filename matches class name variations
            if _matches_class_name(filename, class_words):
                relative_path = os.path.relpath(os.path.join(root, filename), search_dir)
                found_files.append(relative_path)
    
    return found_files


def _matches_class_name(filename, class_words):
    """
    Check if filename matches variations of class name.
    
    Variations checked:
    - ClassNameFile.cpp
    - class_name_file.cpp
    - classnamefile.cpp
    - class-name-file.cpp
    """
    filename_base = os.path.splitext(filename)[0].lower()
    
    # Try different separators and case variations
    separators = ["", "_", "-"]
    
    for sep in separators:
        class_pattern = sep.join(class_words).lower()
        if class_pattern in filename_base:
            return True
    
    # Also check camelCase variations
    camel_case = "".join(class_words).lower()
    if camel_case in filename_base:
        return True
    
    return False

