"""Run the instructor-provided source similarity analyzer."""

from __future__ import annotations

import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile


class SimilarityAnalyzer:
    """Compile and run an unchanged CodeAnalyzer source file.

    :param analyzer_path: C++ source file or directory containing
        ``CodeAnalyzer.cpp`` and its headers.
    :param timeout: Maximum number of seconds allowed for analysis.
    """

    def __init__(self, analyzer_path: str | Path, timeout: int = 120) -> None:
        self.analyzer_path = Path(analyzer_path).expanduser()
        if timeout <= 0:
            raise ValueError("Similarity-analysis timeout must be positive.")
        self.timeout = timeout

    def run(self, input_root: Path, output_path: Path) -> str:
        """Run CodeAnalyzer against student-only submission directories.

        :param input_root: Directory containing one submission per child directory.
        :param output_path: Destination for the analyzer's text report.
        :return: Analyzer diagnostics and generated report contents.
        :raises FileNotFoundError: If the analyzer source or compiler is absent.
        :raises ValueError: If the analyzer source has no hard-coded config path.
        :raises RuntimeError: If compilation or analysis fails.
        """
        source, source_root = self._resolve_source()
        compiler = shutil.which("c++") or shutil.which("g++") or shutil.which("clang++")
        if compiler is None:
            raise FileNotFoundError("No C++ compiler was found for CodeAnalyzer.")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="code-analyzer-") as temporary:
            staging = Path(temporary)
            executable = staging / "CodeAnalyzer"
            try:
                compile_result = subprocess.run(
                    [compiler, "-std=c++20", str(source), "-o", str(executable)],
                    cwd=source_root, capture_output=True, text=True,
                    timeout=self.timeout, check=False,
                )
            except subprocess.TimeoutExpired as error:
                raise RuntimeError("CodeAnalyzer compilation timed out.") from error
            if compile_result.returncode != 0:
                raise RuntimeError(
                    "CodeAnalyzer compilation failed:\n"
                    f"{compile_result.stdout}{compile_result.stderr}"
                )
            config_name = self._config_filename(source)
            (staging / config_name).write_text(
                json.dumps({"inputRoot": str(input_root), "output": str(output_path)}, indent=2)
                + "\n", encoding="utf-8"
            )
            try:
                run_result = subprocess.run(
                    [str(executable)], cwd=staging, capture_output=True,
                    text=True, timeout=self.timeout, check=False,
                )
            except subprocess.TimeoutExpired as error:
                raise RuntimeError("CodeAnalyzer analysis timed out.") from error
        if run_result.returncode != 0:
            raise RuntimeError(
                "CodeAnalyzer failed:\n"
                f"{run_result.stdout}{run_result.stderr}"
            )
        if not output_path.is_file():
            raise RuntimeError("CodeAnalyzer completed without creating its report.")
        return (
            f"Analyzer source: {source}\n"
            f"Analyzed submissions: {self._submission_names(input_root)}\n\n"
            + output_path.read_text(encoding="utf-8", errors="replace")
        )

    def _resolve_source(self) -> tuple[Path, Path]:
        """Locate the analyzer source and its header directory.

        :return: Analyzer source and compiler working directory.
        :raises FileNotFoundError: If ``CodeAnalyzer.cpp`` cannot be found.
        """
        if self.analyzer_path.is_file():
            return self.analyzer_path, self.analyzer_path.parent
        source = self.analyzer_path / "CodeAnalyzer.cpp"
        if source.is_file():
            return source, self.analyzer_path
        raise FileNotFoundError(f"CodeAnalyzer.cpp was not found at '{self.analyzer_path}'.")

    @staticmethod
    def _config_filename(source: Path) -> str:
        """Extract the analyzer's hard-coded JSON filename.

        :param source: CodeAnalyzer C++ source file.
        :return: Filename used by the analyzer when opening its config.
        :raises ValueError: If no hard-coded JSON path is declared.
        """
        contents = source.read_text(encoding="utf-8", errors="replace")
        match = re.search(r'JSON_FILE\s*=\s*R"\((.*?)\)"', contents, re.DOTALL)
        if match is None:
            raise ValueError("CodeAnalyzer does not declare a hard-coded JSON_FILE path.")
        return match.group(1)

    @staticmethod
    def _submission_names(input_root: Path) -> str:
        """List submission directories passed to the analyzer.

        :param input_root: Student-only submissions directory.
        :return: Comma-separated submission identifiers, or ``none``.
        """
        names = sorted(path.name for path in input_root.iterdir() if path.is_dir())
        return ", ".join(names) or "none"
