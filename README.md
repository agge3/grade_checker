# Grade Checker

## Usage
Setup:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
To run all tests:
```bash
python -m tests.<type_of_test>.run  # General
python -m tests.unit.run    # Specific example
```
To run specific tests:
```bash
python -m tests.<type_of_test>.<test_name>  # General
python -m tests.unit.shell_unit # Specific example
```

## Organization
* `root`
  * `main.py` - Main entry point.
  * `config.py` - Reads in Grade Checker's configuration file and handles
                  different grading configurations.
  * `core`
    * `build.py` - Cross platform CXX project building.
    * `shell.py` - Cross platform shell. Most notably, handles git bash on
                   Windows to call bash scripts.
    * `file_processor.py` - Iterator for different file collections.
    * `grader.py` - Main driver for Grade Checker; handles "grading".
    * `reporter.py` - Reporting information for Grade Checker.
  * `tools`
    * `util.py` - Global utility functions.
  * `scripts` - Bash scripts for things that can be done easier with UNIX shell.
    * `check-ec.sh` - Check for extra credit, specified by the following 
                      parameters: `--smart_ptrs`, `--templates`, or `--gtest`.
    * `check-static.sh` - Check for static or globals.
    * `check-stl.sh` - Check for usage of the CXX STL.
    * `find_hpp.sh` - Search for `.hpp` files of a class, accounting for 
                      different file naming conventions.
    * `find_cpp.sh` - Search for `.cpp` files of a class, accounting for 
                      different file naming conventions.
  * `milestones` - JSON configuration files Grade Checker parses in for each
                   milestone's configuration.
    * `_milestoneX` - Each milestone's configuration file.
