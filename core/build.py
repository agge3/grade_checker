from tools import util
from core.shell import Shell

import os
import subprocess
import shutil
import sys


class Build:
    def __init__(self):
        if util.is_windows():
            try:
                self.exec_name = self._find_msbuild()
            except FileNotFoundError as e:
                print(e)
                sys.exit(1)

            self.config = self._find_sln_path()
            if not self.config:
                print("No .sln file found in the current directory.")
                sys.exit(1)

            self.cmd = f'"{self.exec_name}" "{self.config}" /p:Configuration=Debug'
        else:
            self.exec_name = "/usr/bin/env cmake"
            self.config = "CMakeLists.txt"
            self.cmd = "mkdir build && cd build && cmake .. && cmake --build ."


    def _find_msbuild(self):
        """ Find msbuild.exe on Windows. """
        search_dirs = [
            r"C:\Program Files (x86)",
            r"C:\Program Files",
        ]
        exec_name = "msbuild.exe"
    
        # Search through the directories
        for root_dir in search_dirs:
            for root, dirs, files in os.walk(root_dir):
                if exec_name in files:
                    return os.path.join(root, exec_name)
        
        # Fallback to check system PATH
        for path in os.getenv("PATH", "").split(os.pathsep):
            msbuild_path = os.path.join(path, exec_name)
            if os.path.isfile(msbuild_path):
                return msbuild_path
    
        raise FileNotFoundError("msbuild.exe not found on this system.")

    def _find_sln_path(self):
        """ Find the .sln file on Windows. """
        search_command = 'findstr /S /I ".sln" *'
    
        try:
            result = subprocess.run(
                search_command,
                shell=True,
                capture_output=True,
                text=True,
                check=True,
            )
            #matches = result.stdout.strip().splitlines()
            stdout = result.stdout
            print(f"stdout: {stdout}")
            return stdout if stdout else None
        except subprocess.CalledProcessError as e:
            print(f"Error while searching for .sln file: {e.stderr}")
            return None


    def make_run(self):
        """ Build and run the project. """
        if util.is_windows():
            try:
                res = subprocess.run(self.cmd, shell=True, capture_output=True, text=True)
            except Exception as e:
                print(f"Error while building: {e}")
                sys.exit(1)

            if res.returncode != 0:
                print(f"Build failed with code {res.returncode}:")
                print(res.stderr)
                return "", False

            # Assuming the output directory is Debug or Release
            debug_dir = os.path.join(os.path.dirname(self.config), "Debug")
            exe_files = [f for f in os.listdir(debug_dir) if f.endswith(".exe")]

            if not exe_files:
                print("No executable found in the Debug directory.")
                sys.exit(1)

            exe_path = os.path.join(debug_dir, exe_files[0])
            print(f"Executing: {exe_path}")

            try:
                res = subprocess.run([exe_path], capture_output=True, text=True)
                print("Program output:")
            except Exception as e:
                print(f"Error while executing the executable: {e}")
                sys.exit(1)

            if res.returncode != 0:
                print(res.stdout)
                return res.stdout, False
            return res.stdout, True

        # For non-Windows (assuming Linux/Mac)
        res = subprocess.run(self.cmd, shell=True, capture_output=True, text=True)
        if res.returncode != 0:
            print(res.stderr)
            return "", False

        # Use grep to find the executable name
        cmd = f"grep -oP '(?<=add_executable\\()\\w+' {self.config}"
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if res.returncode != 0:
            executable_name = "main"
        else:
            executable_name = res.stdout.strip()

        cmd = f"./build/{executable_name}"
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if res.returncode != 0:
            return res.stdout, False
        return res.stdout, True
