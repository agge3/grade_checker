class Shell:
    def __init__(self):
        self._os = os.name
        self._bash = self._get_bash_path()
        self._check_dep()


    def _get_bash_path(self):
        """ Find the appropriate bash executable depending on the OS. """
        if _is_windows():
            return self._get_git_bash_path()
        return "/usr/bin/env bash"


    def _get_git_bash_path(self):
        """ Find Git Bash executable on Windows. """
        possible_paths = [
            r"C:\Program Files\Git\bin\bash.exe",
            r"C:\Program Files (x86)\Git\bin\bash.exe",
        ]
        for path in possible_paths:
            if os.path.isfile(path):
                return path
        raise FileNotFoundError("Git Bash not found. Please install Git Bash.")


    def _check_dep(self):
        """
        Ensure required dependencies like `grep` are available.
        On Windows, Git Bash includes grep; ensure it works.
        """
        try:
            res = subprocess.run(
                "grep --version", shell=True, capture_output=True, text=True
            )
            if res.returncode != 0:
                raise RuntimeError(f"grep check failed with error: {res.stderr}")
            print("grep is available.")
        except FileNotFoundError:
            print("Error: `grep` command not found.")
            sys.exit(1)


    def cmd(self, cmd):
        """
        Run a shell command.
        On Windows, use Git Bash if specified; otherwise, run normally.
        """
        if _is_windows():
            # Wrap the command for Git Bash compatibility.
            # xxx why do we need to join here?
            bash_cmd = ' '.join(cmd)
            result = subprocess.run([self._bash, "-c", bash_cmd], capture_output=True, text=True)
        else:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

        return result.stdout, result.stderr, result.returncode
