
# CREDIT: OpenAi's ChatGPT
class GradeReporter:
    def __init__(self, shell, clazz):
        self.shell = shell
        self.clazz = clazz
        self.grader = Grader(shell, clazz)
        self.report = {}

    def generate_report(self):
        score = 0
        self.report = {}

        # Extra Credit
        ec_args_lst = [
            "--smart_ptrs",
            "--templates",
            "--gtest",
        ]
        ec_args = ' '.join(ec_args_lst)
        stdout, stderr, code = self.shell.cmd(f"./check-ec.sh {ec_args}")
        try:
            ec_score = float(stdout)
            self.report["extra_credit_score"] = [str(ec_score)]
            score += ec_score
        except ValueError:
            self.report["extra_credit_score"] = ["N/A"]

        # Generic grading (applies to all milestones)
        try:
            headers_score = self.grader.check_headers()
            self.report["headers_score"] = [f"{headers_score:.2f}"]
            score += headers_score
        except Exception as e:
            self.report["headers_score"] = ["Error"]
        
        try:
            func_score, comments_score, clazz_comment = self.grader.check_func()
            self.report["functionality_score"] = [f"{func_score:.2f}"]
            self.report["comments_score"] = [f"{comments_score:.2f}"]
            self.report["class_comment_score"] = [f"{clazz_comment:.2f}"]
            score += func_score + comments_score + clazz_comment
        except Exception as e:
            self.report["functionality_score"] = ["Error"]
            self.report["comments_score"] = ["Error"]
            self.report["class_comment_score"] = ["Error"]

        # HashTable specific grading
        try:
            prime_score = self.grader.check_prime()
            self.report["prime_score"] = [f"{prime_score:.2f}"]
            score += prime_score
        except Exception as e:
            self.report["prime_score"] = ["Error"]

        try:
            list_score = self.grader.check_list()
            self.report["list_score"] = [f"{list_score:.2f}"]
            score += list_score
        except Exception as e:
            self.report["list_score"] = ["Error"]

        # Total score
        self.report["total_score"] = [f"{score:.2f}"]
        return self.report

    def save_report(self, filename="grade_report.txt"):
        """
        Saves the generated report in plain text format.
        Handles cases where report is empty or incomplete.
        """
        try:
            with open(filename, 'w') as f:
                for key, value in self.report.items():
                    f.write(f'{key}="{", ".join(value)}"\n')
            print(f"Report saved to {filename}.")
        except Exception as e:
            print(f"Error saving report: {e}")


# CREDIT: OpenAI's ChatGPT
class ReportDisplayer:
    def __init__(self, report_filename="grade_report.txt"):
        self.report_filename = report_filename

    def display_report(self):
        student_name = self.get_student_name_from_dir()
        if not student_name:
            student_name = "Unknown Student"
        
        print(f"Grade Report for {student_name}")
        print("=" * (len(student_name) + 14))  # Just to add a little formatting to the title

        try:
            with open(self.report_filename, 'r') as f:
                report_lines = f.readlines()
            if not report_lines:
                print("Report is empty or has no valid content.")
                return
        except FileNotFoundError:
            print(f"Error: Report file '{self.report_filename}' not found.")
            return
        except Exception as e:
            print(f"Error reading report file: {e}")
            return

        # Display simplified report
        for line in report_lines:
            key, value = line.strip().split("=")
            value = value.strip('"')
            print(f"{key}: {value}")

    def get_student_name_from_dir(self):
        """
        Gets the student name from the root directory.
        Handles cases where the directory name may be invalid.
        """
        student_name = os.path.basename(os.getcwd())  # Get the current working directory's name
        # If the directory name is empty or has an unusual format, return None to indicate failure
        if not student_name or re.search(r"[^a-zA-Z0-9_]", student_name):
            return None
        return student_name

class SummaryDisplayer:
    def __init__(self, report_dir):
        self.report_dir = report_dir  # Directory containing student reports

    def display_summary(self):
        student_scores = self.generate_summary_report()

        print("Grade Summary Report")
        print("=====================")

        for student_name, total_score in student_scores.items():
            print(f"{student_name}: {total_score:.2f}")

    def generate_summary(self):
        student_scores = {}
        # Loop through the report directory and find all grade reports
        for student_dir in os.listdir(self.report_dir):
            student_path = os.path.join(self.report_dir, student_dir)
            if os.path.isdir(student_path):  # Only process directories
                report_file = os.path.join(student_path, "grade_report.txt")
                if os.path.isfile(report_file):
                    try:
                        with open(report_file, 'r') as f:
                            report_lines = f.readlines()
                            # Look for the total score line in the report
                            for line in report_lines:
                                if "total_score" in line:
                                    score_value = line.split("=")[1].strip().strip('"')
                                    student_scores[student_dir] = float(score_value)
                                    break
                    except Exception as e:
                        print(f"Error reading report for {student_dir}: {e}")
                        student_scores[student_dir] = "Error"
                else:
                    student_scores[student_dir] = "No Report"

        return student_scores

# Example usage:

def generate_all_reports(shell, clazz, base_directory="students"):
    """
    Generate reports for all students in the base directory.
    Assumes each student's directory contains their source code and grading script.
    """
    student_reports = {}
    
    for student_dir in os.listdir(base_directory):
        student_path = os.path.join(base_directory, student_dir)
        if os.path.isdir(student_path):
            os.chdir(student_path)  # Change to the student's directory to simulate their environment
            reporter = GradeReporter(shell, clazz, student_name=student_dir)
            reporter.generate_report()
            reporter.save_report(filename="grade_report.txt")
            total_score = reporter.report.get("total_score", ["0"])[0]
            student_reports[student_dir] = total_score
            os.chdir(base_directory)  # Return to the base directory

    return student_reports

