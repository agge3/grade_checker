class Report:
    def __init__(self):
        self.tmp = ""

# CREDIT: OpenAi's ChatGPT
class Reporter:
    def __init__(self, grader):
        self._grader = grader
        self.report = {}
        self.summary = {}

    def get_report(self):
        return self.report

    def generate_report(self): 
        # pwd and regex capture project root
        self.report["name"] = self._grader.get_name()
        self.report["points"]["total"] = config._config["grading"]["total"]

        if config._config["options"]["build"]:
            build = Build()
            out, res = build.make_run()

            if not res:
                self.report["build"] = {
                    "result" : "Build unsuccessful.",
                    "score" : 0,
                    "output" : out
                }
            else:
                self.report["build"] = {
                    "result" : "Build successful.",
                    "score" : config._config["grading"]["build"],
                    "output" : out
                }

        if config._config["extra_credit"]["enabled"]:
            pts, out = self._grader.check_ec(config._config["extra_credit"]["args"])
            self.report["score"] = {
                "score" : config._config["grading"]["extra_credit"],
                "output" :  out
            }

        pts, out = self._grader.check_headers(config._config["grading"]["headers"])
        self.report["headers"] = {
            "score" : pts,
            "output" : out
        }

        # Comments for File, Class and Method headers.
        # Implementations for all of the required methods.
        pts, out = self._grader.check_func(config._config["grading"]["methods"])
        self.report["methods"] = {
            "score" : pts,
            "output" : out
        }

        #
        # Checks for extra items that can easily be grepped for via an argument
        # list. Including:
        #   1. Hard coded values (i.e., sizes of Hashtable, arrays, or cache,
        #      etc.)
        #
        for k, v in config._config["extra"].items():
            if v["enabled"]:
                pts, out = self._grader.check_for(v["args"],
                                            config._config["grading"][v])
                self.report[k] = {
                    "score" : pts,
                    "output" : out
                }

        # Static variables or methods.
        pts, out = self._grader.check_static(config._config["grading"]["static"])
        self.report["static"] = {
            "score" : pts,
            "output" : out
        }

        # Use of STL before Milestone 4 (the implementations of the Data 
        # Structures should be hand-written, not use STL).
        if config._config["options"]["stl"]:
            pts, out = self._grader.check_stl(config._config["grading"]["stl"])
            self.report["stl"] = {
                "score" : pts,
                "output" : out
            }

        # Methods without any parameters (with the exception of getters/main).
        # xxx might be harder, but probably a grep regex pattern:

        # Lack of header files (all code in one file).
        pts, out = self._grader.check_hpp(config._config["grading"]["hpp"])
        self.report["hpp"] = {
            "score" : pts,
            "output" : out
        }

        actual = 0
        for k, v in self.report.items():
            if isinstance(v, dict):
                actual += k.get("score", 0)
        self.report["points"]["actual"] = actual

    def generate_summary(self):
        for k, v in self.report.items():
            if isinstance(v, dict) and
                config._config["grading"].get(k, 0) > v.get("score", 0):
                self.summary[k] = v

    def get_summary(self):
        return self.summary

    def summary_to_json(self, file = "grade_summary.json"):
        with open(file, 'w') as fh:
            json.dump(self.summary, fh, indent = 4)

    def report_to_json(self, file = "grade_report.json"):
        with open(file, 'w') as fh:
            json.dump(self.report, fh, indent = 4)

    def summary_to_text(self, file = "grade_summary.txt"):
        # "pretty" print summary to file, with plain-text kvp and tabs
        with open(file, 'w') as fh:
            for key, val in self.summary.items():
                fh.write(f"{key}:\n")
                for k, v in val.items():
                    fh.write(f"\t{k} = {v}\n")

    # CREDIT: OpenAI's ChatGPT
    def report_to_text(self, file = "grade_report.txt"):
        # "pretty" print report to file, with plain-text kvp and tabs
        with open(file, 'w') as fh:
            for key, item in self.report.items():
                if isinstance(item, dict):
                    fh.write(f"{key}:\n")
                    for k, v in item.items():
                        fh.write(f"\t{k} = {v}\n")
                else:
                    fh.write(f"{key} = {item}\n")


# CREDIT: OpenAI's ChatGPT
    #def get_student_name_from_dir():
    #    """
    #    Gets the student name from the root directory.
    #    Handles cases where the directory name may be invalid.
    #    """
    #    student_name = os.path.basename(os.getcwd())  # Get the current working directory's name
    #    # If the directory name is empty or has an unusual format, return None to indicate failure
    #    if not student_name or re.search(r"[^a-zA-Z0-9_]", student_name):
    #        return None
    #    return student_name
    #
    #def generate_summary():
    #    student_scores = {}
    #    # Loop through the report directory and find all grade reports
    #    for student_dir in os.listdir(self.report_dir):
    #        student_path = os.path.join(self.report_dir, student_dir)
    #        if os.path.isdir(student_path):  # Only process directories
    #            report_file = os.path.join(student_path, "grade_report.txt")
    #            if os.path.isfile(report_file):
    #                try:
    #                    with open(report_file, 'r') as f:
    #                        report_lines = f.readlines()
    #                        # Look for the total score line in the report
    #                        for line in report_lines:
    #                            if "total_score" in line:
    #                                score_value = line.split("=")[1].strip().strip('"')
    #                                student_scores[student_dir] = float(score_value)
    #                                break
    #                except Exception as e:
    #                    print(f"Error reading report for {student_dir}: {e}")
    #                    student_scores[student_dir] = "Error"
    #            else:
    #                student_scores[student_dir] = "No Report"
    #
    #    return student_scores
    #
    #def generate_all_reports(clazz, base_directory="students"):
    #    """
    #    Generate reports for all students in the base directory.
    #    Assumes each student's directory contains their source code and grading script.
    #    """
    #    student_reports = {}
    #    
    #    for student_dir in os.listdir(base_directory):
    #        student_path = os.path.join(base_directory, student_dir)
    #        if os.path.isdir(student_path):
    #            os.chdir(student_path)  # Change to the student's directory to simulate their environment
    #            reporter = GradeReporter(shell, clazz, student_name=student_dir)
    #            reporter.generate_report()
    #            reporter.save_report(filename="grade_report.txt")
    #            total_score = reporter.report.get("total_score", ["0"])[0]
    #            student_reports[student_dir] = total_score
    #            os.chdir(base_directory)  # Return to the base directory
    #
    #    return student_reports


#class ProjectManager:
