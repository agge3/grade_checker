"""
[x] Comments for File, Class and Method headers
[kind of] Implementations for all of the required methods
Matching expected output for our supplied testcases
Run unpublished testcases with expected output (we never got around to this)

Global variables
[x] bash script: Static variables or methods
[xxx] grep for: Hard coded values (i.e., sizes of Hashtable, arrays, or cache, etc.)
[x] bash script (`find_hpp.sh` returns none): Lack of header files (all code in one file)
[xxx] might be harder, but probably a grep regex pattern:
Methods without any parameters (with the exception of getters/main)
[x] bash script: Use of STL before Milestone 4 (the implementations of the Data Structures should be hand-written, not use STL)
Others?
"""

# Grade HashTable.
def grade_hash_table():
    shell = Shell()
    build = Build()

    grader = Grader(shell, "HashTable")
    score = 0

    # Helper script to grade extra credit.
    ec_args_lst = [
        "--smart_ptrs",
        "--templates",
        "--gtest",
    ]
    # Fixing the join statement
    ec_args = ' '.join(ec_args_lst)  # Join the list into a single string

    # Run the extra credit script
    stdout, stderr, code = shell.cmd(f"./check-ec.sh {ec_args}")
    try:
        score += float(stdout)  # Add the extra credit score
    except ValueError as e:
        print(e)

    # Generic grading (applies to all milestones).
    score += grader.check_headers()
    func_score, comments_score, clazz_comment = grader.check_func()
    score += func_score + comments_score + clazz_comment  # Simplified this part

    # HashTable specific grading.
    score += grader.check_prime()
    score += grader.check_list()

    return score  # Return the final grade score


def main():
    final_score = grade_hash_table()  # Capture the final score
    print(f"Final Score: {final_score}")  # Print the final score


if __name__ == "__main__":
    main()
