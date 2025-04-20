import os
import re


def is_windows():
    """ Check if the OS is Windows. """
    return os.name == "nt"


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

def methods_to_strlst(config):
    if "methods" not in config:
        raise KeyError(
                f"'methods' key not found in config. Config parsing error."
        )

    strlst = []
    for name, decl in config["methods"].items():
        ret = decl["return"]
        para = decl["params"]
        strlst.append(f"{ret} {name}")

    return strlst
