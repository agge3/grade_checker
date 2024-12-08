# CREDIT: OpenAI's ChatGPT

import json

def read_config(config_path):
    """Reads the JSON config from a given path."""
    with open(config_path, 'r') as file:
        config = json.load(file)
    return config

def parse_milestones(config):
    """Parses and prints the milestones from the config."""
    milestones = config.get("milestones", {})
    for milestone, projects in milestones.items():
        print(f"\nMilestone: {milestone}")
        for project_name, details in projects.items():
            print(f"  Project Name: {project_name}")
            print(f"    Methods: {', '.join(details.get('methods', []))}")
            print(f"    Optionals: {', '.join(details.get('optionals', []))}")
            grading = details.get("grading", {})
            print(f"    Grading:")
            print(f"      Rubric: {grading.get('rubric', 'N/A')}")
            print(f"      Max Points: {grading.get('max_points', 'N/A')}")
            extra_credit = details.get("extra_credit", {})
            print(f"    Extra Credit:")
            print(f"      Enabled: {extra_credit.get('enabled', False)}")
            print(f"      Criteria: {', '.join(extra_credit.get('criteria', []))}")

# Example usage
if __name__ == "__main__":
    config_path = "config.json"  # Path to your JSON config file
    config = read_config(config_path)
    parse_milestones(config)
