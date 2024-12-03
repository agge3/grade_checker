import os
import subprocess
import sys
import re
from sympy import primerange
from dateutil import parser


def is_windows():
    """Check if the OS is Windows."""
    return os.name == "nt"


def get_git_bash_path():
    """Find Git Bash executable on Windows."""
    possible_paths = [
        r"C:\Program Files\Git\bin\bash.exe",
        r"C:\Program Files (x86)\Git\bin\bash.exe",
    ]
    for path in possible_paths:
        if os.path.isfile(path):
            return path
    raise FileNotFoundError("Git Bash not found. Please install Git Bash.")


def run_command(command, use_git_bash=False):
    """Run a shell command with cross-platform compatibility."""
    if use_git_bash and is_windows():
        git_bash_path = get_git_bash_path()
        result = subprocess.run(
            [git_bash_path, "-c", command],
            capture_output=True,
            text=True,
        )
    else:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
        )
    return result.stdout.strip(), result.stderr.strip(), result.returncode


def check_dependencies():
    """Ensure required dependencies like `grep` are available."""
    try:
        stdout, stderr, code = run_command("grep --version", use_git_bash=is_windows())
        if code != 0:
            raise RuntimeError(f"grep check failed with error: {stderr}")
        print("grep is available.")
    except FileNotFoundError as e:
        print(e)
        sys.exit(1)


def build():
    """Build and test the project."""
    if is_windows():
        # Windows-specific build logic
        try:
            msbuild_path = find_msbuild()
        except FileNotFoundError as e:
            print(e)
            sys.exit(1)

        sln_path = find_sln_path()
        if not sln_path:
            print("No .sln file found in the current directory.")
            sys.exit(1)

        build_command = f'"{msbuild_path}" "{sln_path}" /p:Configuration=Debug'
        stdout, stderr, code = run_command(build_command)
        print(stdout)

        if code != 0:
            print(f"Build failed: {stderr}")
            return "", False

        debug_dir = os.path.join(os.path.dirname(sln_path), "Debug")
        exe_files = [f for f in os.listdir(debug_dir) if f.endswith(".exe")]

        if not exe_files:
            print("No executable found in the Debug directory.")
            sys.exit(1)

        exe_path = os.path.join(debug_dir, exe_files[0])
        stdout, stderr, code = run_command(exe_path)
        return stdout, code == 0
    else:
        # Linux-specific build logic
        build_commands = [
            "mkdir -p build && cd build && cmake ..",
            "cd build && cmake --build .",
        ]
        for cmd in build_commands:
            stdout, stderr, code = run_command(cmd)
            if code != 0:
                print(f"Build failed: {stderr}")
                return "", False

        executable = "cd build && ./main"
        stdout, stderr, code = run_command(executable)
        return stdout, code == 0


def get_files():
    """Find and categorize files containing 'hash map' references."""
    file_patterns = {
        "hpp": r"grep -i -r -l -E 'hash[- ]?map[- ]?\.(hpp|h|hh)' *",
        "cpp": r"grep -i -r -l -E 'hash[- ]?map[- ]?\.(cpp|cxx|cc)' *",
    }
    files = {}
    for key, pattern in file_patterns.items():
        stdout, _, _ = run_command(pattern, use_git_bash=is_windows())
        files[key] = stdout.splitlines()
    return files


def check_headers(files):
    """Verify headers in files for format compliance."""
    name_pattern = r"(Created by|Modified by)\s+[\w\s]+"
    score = 1

    for ftype, file_list in files.items():
        for file in file_list:
            with open(file, "r") as fh:
                content = fh.read()
                if "/**" not in content or "*/" not in content:
                    score -= 0.5
                    continue

                header = content.split("*/")[0]
                if not re.search(name_pattern, header):
                    score -= 0.5
    return max(score, 0)


def check_prime(files):
    """Check for usage of prime numbers in header files."""
    limit = 10000
    primes = set(map(str, primerange(2, limit + 1)))
    score = 1

    for file in files.get("hpp", []):
        with open(file, "r") as fh:
            content = fh.read()
            if not any(prime in content for prime in primes):
                score = 0
    return score


def main():
    """Main function to orchestrate the checks."""
    check_dependencies()
    score = 0

    files = get_files()
    score += check_prime(files)
    score += check_headers(files)

    stdout, build_success = build()
    if build_success:
        print("Build and execution successful.")
    else:
        print("Build or execution failed.")
    print(f"Final score: {score:.2f}")


if __name__ == "__main__":
    main()
