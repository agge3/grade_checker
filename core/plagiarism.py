import os
import difflib

from core.shell import shell
from core.file_processor import FileProcessor
from tools import util
from tools.logger import MyLogger

class Plagiarism:
    def __init__(self, milestone, config):
        self._name = self.__class__.__name__
        self._logger = MyLogger.create(self._name)
        self._milestone = milestone
        self._config = config
        self._repo_root = ""
        self._repos = []
        self._set_config()

    def _set_config(self):
        self._repo_root = ""f"repos/{self._milestone}-{self._config["prof"]}/"

        self._logger.debug(f"milestone: {self._milestone}")
        self._logger.debug(f"professor: {self._config["prof"]}")
        self._logger.debug(f"repository root: {self._repo_root}")

        reserved = ["reports"]
        self._repos = util.get_dirs(self._repo_root, reserved)

        self._clazzes = self._config["classes"]

    def _read_lines(self, file):
        """
        Python 3 uses universal newlines by default, so no need to dos2unix.
        """

        lines = []
        processor = FileProcessor(file, "r")
        for fh, ftype in processor:
            lines = fh.readlines()

        return lines

    def _diff(self, lines_a, lines_b, threshold):
        """
        NOTE:
        https://docs.python.org/3/library/difflib.html#difflib.SequenceMatcher.ratio
        This is expensive to compute if get_matching_blocks() or get_opcodes()
        hasn’t already been called, in which case you may want to try
        quick_ratio() or real_quick_ratio() first to get an upper bound.
        """

        sm = difflib.SequenceMatcher(None, lines_a, lines_b)

        quick_ratio = sm.quick_ratio()
        if quick_ratio < threshold:
            return None

        ratio = sm.ratio()
        if ratio < threshold:
            return None

        # diff ${a} ${b}
        diff_out = "".join(difflib.unified_diff(
            lines_a, lines_b,
            fromfile="a", tofile="b",
        ))

        set_a = set(lines_a)
        set_b = set(lines_b)

        # grep -Fxf ${a} ${b}
        same_cnt = sum(1 for line in lines_b if line in set_a)
        # grep -Fxvf ${a} ${b}
        diff_cnt = sum(1 for line in lines_b if line not in set_a)

        return diff_out, ratio, same_cnt, diff_cnt


    def strip(self, lines):
        stripped = []

        for line in lines:
            # trim just to compare comments or blank lines
            tmp = line.strip()
            if not tmp or tmp.startswith('//') or tmp.startswith('/*') or tmp.startswith('*'):
                continue
            stripped.append(line)

        return stripped

    def _cat_repo_files(self, path):
        files = util.get_files(self._clazzes, path)
        lines = []
        for f in files["cpp"].values():
            lines.extend(self._read_lines(f))
        return lines

    def check(self, threshold, strip=False):
        repo_lines = {}
        matches = {}

        for i in range(len(self._repos)):
                repo_a = self._repos[i]
                if not repo_lines[repo_a]:
                    repo_lines = self._cat_repo_files(repo_a)
                    if strip:
                        repo_lines = strip(repo_lines)

            for j in range(i + 1, len(self._repos)):
                repo_b = self._repos[j]
                if not repo_lines[repo_b]:
                    repo_lines = self._cat_repo_files(repo_b)
                    if strip:
                        repo_lines = strip(repo_lines)

                res = self._diff(repo_lines[repo_a], repo_lines[repo_b],
                                 threshold)

                if not res:
                    self._logger.debug(
                        f"passed plagiarism check: (a: {repo_a}, b: {repo_b})")
                    continue

                diff_out, ratio, same_cnt, diff_cnt = res

                if repo_a not in matches:
                    matches[repo_a] = []

                matches[repo_a].append({
                    "repo": repo_b,
                    "diff_out": diff_out,
                    "ratio": ratio,
                    "same_cnt": same_cnt,
                    "diff_cnt": diff_cnt,
                })

        return matches


    def run(self):
        strip = self._config["plagiarism"]["strip"]  # throws
        raw = self._config["plagiarism"]["raw"] # throws
        threshold = self._config["plagiarism"]["threshold"] # throws

        if not raw or not strip:
            self._logger.warning(
                "no plagiarism check mode is 'True'. nothing to do")

        if raw is True:
            self._logger.info("checking plagiarism mode 'raw'...")
            matches = self.check(threshold)
            for match in matches:
                self._logger.info("found match:")
                self._logger.info(match)
        if strip is True:
            self._logger.info("checking plagiarism mode 'strip'...")
            matches = self.check(threshold, strip)
            for match in matches:
                self._logger.info("found match:")
                self._logger.info(match)
