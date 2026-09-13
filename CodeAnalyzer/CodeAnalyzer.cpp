/**
 * @file CodeAnalyzer.cpp
 * @brief CSC340 Plagiarism / Similarity Detection Tool
 *
 * @details
 * This program analyzes student C++ submissions and computes pairwise similarity
 * using a Jaccard-based token comparison approach.
 *
 * It is designed for academic integrity checking in programming assignments.
 *
 * -------------------------------------------------------------------------
 * INPUT (CONFIG FILE: milestone.json)
 * -------------------------------------------------------------------------
 * The program expects a JSON file located at JSON_FILE containing:
 *
 * {
 *   "inputRoot": "C:\\path\\to\\parent\\directory",
 *   "output": "C:\\path\\to\\output\\report.txt"
 * }
 *
 * inputRoot:
 *   - A directory containing multiple student subdirectories.
 *   - Each subdirectory represents one student's submission.
 *   - Each submission may contain multiple .cpp/.h/.hpp/.c files.
 *
 * output:
 *   - Path to the output report file.
 *
 * -------------------------------------------------------------------------
 * OUTPUT
 * -------------------------------------------------------------------------
 * A text report containing:
 *   - Pairwise similarity percentages between students
 *   - "*** POSSIBLE COPY ***" flag if similarity >= threshold (default 90%)
 *
 * -------------------------------------------------------------------------
 * PROCESSING PIPELINE
 * -------------------------------------------------------------------------
 * 1. Read all source files per student (recursive directory traversal)
 * 2. Remove comments
 * 3. Normalize identifiers (replace user-defined names with IDs)
 * 4. Remove whitespace
 * 5. Tokenize code into lexical tokens
 * 6. Compute Jaccard similarity between token sets
 * 7. Output ranked similarity report
 */

#include "json.hpp"
using json = nlohmann::json;

#include <iostream>
#include <fstream>
#include <string>
#include <vector>
#include <unordered_map>
#include <unordered_set>
#include <set>
#include <regex>
#include <filesystem>
#include <algorithm>
#include <iterator>

using namespace std;
namespace fs = std::filesystem;

const string JSON_FILE =
R"(C:\Users\Hughh\Documents\Data\SFSU\CSC340\2026-Fall\CodeAnalyzer\milestone.json)";

/**
 * @brief Reads the full contents of a file into a string.
 *
 * @param filename Path to file.
 * @return File contents as a string, or empty string if file cannot be opened.
 */
string readFile(const string& filename)
{
    ifstream in(filename);
    if (!in) return "";

    return string(
        istreambuf_iterator<char>(in),
        istreambuf_iterator<char>());
}

/**
 * @brief Reads all source code files in a student submission directory recursively.
 *
 * @details
 * Only includes files with extensions:
 * .cpp, .h, .hpp, .c
 *
 * @param studentDir Root directory of a student's submission.
 * @return Concatenated source code from all valid files.
 */
string readEntireSubmission(const fs::path& studentDir)
{
    string combined;

    for (const auto& entry : fs::recursive_directory_iterator(studentDir))
    {
        if (!entry.is_regular_file())
            continue;

        string ext = entry.path().extension().string();
        transform(ext.begin(), ext.end(), ext.begin(), ::tolower);

        if (ext == ".cpp" || ext == ".h" || ext == ".hpp" || ext == ".c")
        {
            combined += readFile(entry.path().string());
            combined += "\n";
        }
    }

    return combined;
}

/**
 * @brief Removes C++ block and line comments from source code.
 *
 * @param code Raw source code.
 * @return Code with comments removed.
 */
string removeComments(const string& code)
{
    string result = code;

    regex blockComment(R"(/\*[\s\S]*?\*/)");
    result = regex_replace(result, blockComment, "");

    regex lineComment(R"(//[^\r\n]*)");
    result = regex_replace(result, lineComment, "");

    return result;
}

/**
 * @brief Removes all whitespace characters from source code.
 *
 * @param code Input code.
 * @return Code with all whitespace removed.
 */
string removeWhitespace(const string& code)
{
    return regex_replace(code, regex(R"(\s+)"), "");
}

/**
 * @brief Normalizes identifiers in the source code.
 *
 * @details
 * Replaces all user-defined identifiers with generic IDs (ID1, ID2, ...),
 * while preserving C++ keywords.
 *
 * This reduces similarity noise caused by renamed variables/functions.
 *
 * @param code Input source code.
 * @return Code with normalized identifiers.
 */
string normalizeIdentifiers(const string& code)
{
    static const unordered_set<string> keywords =
    {
        "int","double","float","char","void",
        "return","if","else","while","for",
        "class","struct","public","private",
        "protected","new","delete","const",
        "true","false","nullptr","using",
        "namespace","std","include",
        "string","bool","auto",
        "cout","cin","endl",
        "vector","list","queue","stack",
        "map","pair","size_t"
    };

    unordered_map<string, string> identifierMap;
    int nextID = 1;

    regex wordPattern(R"(\b[A-Za-z_][A-Za-z0-9_]*\b)");

    string result;
    size_t lastPos = 0;

    auto begin = sregex_iterator(code.begin(), code.end(), wordPattern);
    auto end = sregex_iterator();

    for (auto it = begin; it != end; ++it)
    {
        smatch match = *it;

        result += code.substr(lastPos, match.position() - lastPos);

        string token = match.str();

        if (keywords.contains(token))
        {
            result += token;
        }
        else
        {
            if (!identifierMap.contains(token))
                identifierMap[token] = "ID" + to_string(nextID++);

            result += identifierMap[token];
        }

        lastPos = match.position() + match.length();
    }

    result += code.substr(lastPos);
    return result;
}

/**
 * @brief Fully normalizes source code for comparison.
 *
 * @param source Raw source code.
 * @return Normalized code string.
 */
string normalizeSource(const string& source)
{
    string result = removeComments(source);
    result = normalizeIdentifiers(result);
    result = removeWhitespace(result);
    return result;
}

/**
 * @brief Tokenizes normalized source code into a set of lexical tokens.
 *
 * @param source Normalized source code.
 * @return Set of unique tokens.
 */
set<string> tokenize(const string& source)
{
    set<string> tokens;

    regex tokenPattern(
        R"([A-Za-z_][A-Za-z0-9_]*|\d+|==|!=|<=|>=|&&|\|\||\S)");

    auto begin = sregex_iterator(source.begin(), source.end(), tokenPattern);
    auto end = sregex_iterator();

    for (auto it = begin; it != end; ++it)
        tokens.insert(it->str());

    return tokens;
}

/**
 * @brief Computes Jaccard similarity between two token sets.
 *
 * @param a First token set.
 * @param b Second token set.
 * @return Similarity percentage (0–100).
 */
double similarity(const set<string>& a, const set<string>& b)
{
    vector<string> intersection;
    vector<string> uni;

    set_intersection(a.begin(), a.end(),
        b.begin(), b.end(),
        back_inserter(intersection));

    set_union(a.begin(), a.end(),
        b.begin(), b.end(),
        back_inserter(uni));

    if (uni.empty()) return 0.0;

    return 100.0 * intersection.size() / uni.size();
}

/**
 * @brief Represents one student submission.
 */
struct Submission
{
    string name;
    set<string> tokens;
};

/**
 * @brief Finds connected plagiarism groups.
 *
 * @details
 * Each student is represented as a node in a graph.
 * An edge exists when two submissions exceed the plagiarism threshold.
 *
 * Connected components correspond to possible copying groups.
 *
 * @param graph Similarity graph.
 * @return Vector of groups.
 */
vector<vector<int>> findGroups(
    const vector<vector<int>>& graph)
{
    vector<vector<int>> groups;

    vector<bool> visited(graph.size(), false);

    for (size_t start = 0; start < graph.size(); start++)
    {
        if (visited[start])
            continue;

        if (graph[start].empty())
            continue;

        vector<int> group;
        vector<int> stack;

        stack.push_back(static_cast<int>(start));
        visited[start] = true;

        while (!stack.empty())
        {
            int current = stack.back();
            stack.pop_back();

            group.push_back(current);

            for (int neighbor : graph[current])
            {
                if (!visited[neighbor])
                {
                    visited[neighbor] = true;
                    stack.push_back(neighbor);
                }
            }
        }

        groups.push_back(group);
    }

    return groups;
}

/**
 * @brief Program entry point.
 *
 * @details
 * Loads configuration from JSON_FILE, processes all student submissions,
 * computes pairwise similarity, and writes a report to the output file.
 *
 * @return Exit status code.
 */
int main()
{
    ifstream jsonFile(JSON_FILE);

    if (!jsonFile)
    {
        cerr << "Cannot open JSON file:\n" << JSON_FILE << endl;
        return 1;
    }

    json j;

    try
    {
        jsonFile >> j;
    }
    catch (const exception& e)
    {
        cerr << "JSON parse error:\n" << e.what() << endl;
        return 1;
    }

    string inputRoot;
    string outputFile;

    if (j.contains("inputRoot") && j["inputRoot"].is_string())
        inputRoot = j["inputRoot"];
    else
    {
        cerr << "Missing 'inputRoot' in JSON\n";
        return 1;
    }

    if (j.contains("output") && j["output"].is_string())
        outputFile = j["output"];
    else
    {
        cerr << "Missing 'output' in JSON\n";
        return 1;
    }

    vector<Submission> submissions;

    if (!fs::exists(inputRoot))
    {
        cerr << "Missing input root:\n" << inputRoot << endl;
        return 1;
    }

    for (const auto& student : fs::directory_iterator(inputRoot))
    {
        if (!student.is_directory())
            continue;

        string studentName = student.path().filename().string();

        cout << "Processing " << studentName << endl;

        string source = readEntireSubmission(student.path());

        if (source.empty())
            continue;

        source = normalizeSource(source);

        Submission s;

        s.name = studentName;
        s.tokens = tokenize(source);

        submissions.push_back(s);
    }

    sort(submissions.begin(), submissions.end(),
        [](const auto& a, const auto& b)
        {
            return a.name < b.name;
        });

    ofstream out(outputFile);

    if (!out)
    {
        cerr << "Cannot create output file:\n"
            << outputFile << endl;
        return 1;
    }

    out << "CSC340 Similarity Report\n";
    out << "========================\n\n";

    const double FLAG_THRESHOLD = 90.0;
    vector<vector<int>> graph(submissions.size());

    for (size_t i = 0; i < submissions.size(); i++)
    {
        for (size_t j = i + 1; j < submissions.size(); j++)
        {
            double score =
                similarity(
                    submissions[i].tokens,
                    submissions[j].tokens);

            out << fixed;
            out.precision(2);

            out << score << "%\n";

            out << submissions[i].name << '\n';
            out << submissions[j].name << '\n';

            if (score >= FLAG_THRESHOLD)
            {
                out << "*** POSSIBLE COPY ***\n";

                graph[i].push_back(static_cast<int>(j));
                graph[j].push_back(static_cast<int>(i));
            }

            out << "\n";
        }
    }

    auto groups = findGroups(graph);

    out << "\n";
    out << "=========================================\n";
    out << "POSSIBLE COPYING GROUPS\n";
    out << "=========================================\n\n";

    int groupNumber = 1;

    for (const auto& group : groups)
    {
        if (group.size() < 2)
            continue;

        out << "Group #" << groupNumber++ << "\n";
        out << "-------------------------\n";

        for (int index : group)
        {
            out << submissions[index].name << '\n';
        }

        out << '\n';
    }

    cout << "\nReport written to:\n" << outputFile << endl;

    return 0;
}