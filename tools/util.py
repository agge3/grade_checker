import os
import re
from tools.logger import MyLogger
from core.shell import shell


logger = MyLogger.create(os.path.basename(__file__))


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

def get_dirs(root, reserved=None):
    """
    Returns a list of non-hidden directories from root. Optional reserved
    directories to also skip.
    """

    if reserved is None:
        reserved = []
    reserved = [os.path.normpath(os.path.join(root, r)) for r in reserved]

    dirs = []

    logger.info("Building directory list...")
    for dir in os.listdir(root):
        if dir.startswith("."):
            logger.info(f"Skipping dotfile: '{dir}'...")
            continue

        path = os.path.normpath(os.path.join(root, dir))
        if path in reserved:
            logger.info(f"Skipping reserved directory: '{dir}'...")
            continue

        logger.debug(f"Appended directory: {dir}.")
        dirs.append(dir)

    return dirs

def get_files(clazzes, path=""):
    """
    Returns a dictionary of `.cpp` and `.hpp` files found for the provided
    classes in the provided path.
    """
    files = {
        "hpp" : {},
        "cpp" : {},
    }

    for clazz in clazzes:
        words = split_clazz_name(clazz)
        args = ' '.join(words)

        # Run the shell scripts to find `.hpp` and `.cpp` files.
        for ext in ["hpp", "cpp"]:
            if path != "":
                # Have to backtrack a directory to be back in root from scripts.
                cmd = f"./scripts/find-{ext}.sh {path} {args}"
                print(f"Grader: find-{ext}.sh command: {cmd}")

                stdout, stderr, code = shell.cmd(cmd)
                print(f"Grader: _get_files: {stdout}")

                if stdout.strip():  # Only add if there are results.
                    files[ext][clazz] = \
                        f"{path}/{stdout.strip().splitlines()[0]}"
            else:
                # xxx handle handle path (root path).
                print("Grader: _get_files: Empty path.")

    return files

def find_header(lines, name):
    """
    Returns header end index, -1 if header not found on lines[0], or -2 if
    header malformed.
    """
    if not lines:
        logger.warning("empty lines")
        return -1

    # If file doesn't contain beginning comment block, it doesn't have
    # a header.
    COMMENT_BEGINS = ["/**", "//", "/*"]
    if not any (s in lines[0] for s in COMMENT_BEGINS):
        logger.warning(
            f"lines[0] did not contain a comment starting block in "
            f"{name}."
        )
        return -1
    logger.info(f"Found header comment starting block.")

    # Find the end of the comment block.
    #end = "".join(lines).find("*/") or "".join(lines).find("\n")
    end = next(
        (i for i, line in enumerate(lines)
        if line.strip() == "" or "*/" in line),
        -2
    )
    # Sanity check: Header shouldn't be longer than 25 lines.
    if end > 25:
        end = -2

    if end == -2:
        # Malformed comment block.
        logger.warning(
            f"Malformed comment block in {name}."
        )
        return end

    logger.info(f"Header comment block is not malformed.")
    logger.info(f"Header starts on lines[0] and ends on lines[{end}].")

    return end
