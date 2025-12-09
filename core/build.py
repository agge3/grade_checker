from tools import util
from core.shell import Shell

import os
import subprocess
import shutil
import sys
import re


class Build:
    def __init__(self, milestone, config, repo_path):
        self._shell = Shell()
        self._config = config

        self._milestone = milestone
        print(f'Build:\tmilestone:\t{self._milestone}')

        self._pmilestone = self._milestone + f'-{self._config['prof']}'
        print(f'Build:\tprofessor milestone:\t{self._pmilestone}')

        # Relative.
        # xxx
        self._repo_path = repo_path
        self._fhs = self._init_fhs()

        self._missing = []
        self._cfgfhs_path = f"project_fhs/{self._pmilestone}"
        print(f'Build:\tconfig files path:\t{self._cfgfhs_path}')

        self._force_incl = []
        
        if self._milestone == "milestone4":
            self._force_incl = ['milestone4.json', 'milestone4_config.json']

        # Windows case:
        if util.is_windows():
            try:
                self.exec_name = self._find_msbuild()
            except FileNotFoundError as e:
                print(e)
                sys.exit(1)

            self.buildfh = self._find_sln_path()
            if not self.buildfh:
                print("No .sln file found in the current directory.")
                sys.exit(1)

            self.cmd = f'"{self.exec_name}" "{self.buildfh}" /p:Configuration=Debug'


        # *Nix case:
        else:
            self.exec_name = "/usr/bin/env cmake"
            self.buildfh = "CMakeLists.txt"
            self.cmd = "mkdir build && cd build && cmake .. && cmake --build ."

    def _init_fhs(self): 
        fhs = []
        for fh in os.listdir(self._repo_path):
            fhs.append(fh)

        return fhs

    def _check_fhs(self):
        for fh in os.listdir(self._cfgfhs_path):
            if fh in self._fhs and fh not in self._force_incl:
                continue
            if re.match(r"^ignore-.*", fh):
                continue
            self._missing.append(fh)

    # XXX *NIX ONLY.
    def copy_fhs(self):
        self._check_fhs()
        for fh in self._missing:
           shutil.copy2(f"{self._cfgfhs_path}/{fh}", f"{self._repo_path}/{fh}")

    # Pre: CMakeLists.txt must be in the target repository directory.
    def _find_exec(self):
        cmake = f'{self._repo_path}/CMakeLists.txt'
        pattern = r'add_executable\((\w+)'

        try:
            with open(cmake, 'r') as fh:
                buf = fh.read()

                match = re.search(pattern, buf)

                if match:
                    return match.group(1)
                else:
                    print(
                        "Build: _find_exec: Could not find executable name in "
                        "CMakeLists.txt."
                    )
                    return "Milestone_1"    # default executable name
        except FileNotFoundError:
            print("Build: _find_exec: CMakeLists.txt not found.")
            return "Milestone_1"    # default executable name

    # Build and run project.
    def make_run(self):
        # Windows case:
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
            debug_dir = os.path.join(os.path.dirname(self.buildfh), "Debug")
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


        # *Nix case:
        print(f"Build: repo_path: {self._repo_path}")
        exec = self._find_exec()

        stdout, stderr, code = self._shell.cmd(
	        f"rm -rf {self._repo_path}/build && " +
	        f"mkdir -p {self._repo_path}/build && " +
	        f"cd {self._repo_path}/build && " + 
	        f"cmake .. && " +
	        f"make all && " +
            f"./{exec} && " +
	        f"cd -"
        )

        build_true = True
        if code != 0:
            build_true = False

        #print(f"XXX {stdout}")

        out = ""
        out += stdout + "\n"

        # xxx handle if there's already a CMakeLists.txt.
        # We can get the executable name by regex this string:
        # [100%] Built target milestone-2-hashtable-xxx

        return out, build_true


        # XXX DEPRECATED
        # Use grep to find the executable name.
        #cmd = f"grep -oP '(?<=add_executable\\()\\w+' {self.config}"
        #res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        #if res.returncode != 0:
        #    executable_name = "main"
        #else:
        #    executable_name = res.stdout.strip()

        #cmd = f"./build/{executable_name}"
        #res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        #if res.returncode != 0:
        #    return res.stdout, False
        #return res.stdout, True


    # For Windows API.
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

    # For Windows API.
    def _find_sln_path(self):
        """ Find the .sln file on Windows. """
        search_command = 'findstr /S /I ".sln" *'
    
        try:
            res = subprocess.run(
                search_command,
                shell=True,
                capture_output=True,
                text=True,
                check=True,
            )
            matches = res.stdout.strip().splitlines()
            return matches[0] if matches else None
        except subprocess.CalledProcessError as e:
            print(f"Error while searching for .sln file: {e.stderr}")
            return None
