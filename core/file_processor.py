import os


# May take one file, or multiple files, or nested lists of files. Handles the
# logic of handling those cases for a cleaner API where one file is processed
# at one time to the client.
class FileProcessor:
    def __init__(self, files, op):
        """
        Initialize the FileProcessor with files and the operation (op) to apply on each file.
        
        :param files: Can be a single file, a list of files, or nested lists of files.
        :param op: The operation to open the file handle as (e.g., `"r"`, `"w"`, etc.).
        """
        # Normalize files to a list, even if a single file is passed.
        self.files = self._normalize_files(files)
        self.op = op
        self._index = 0 # Index for iterating through files.
        self._curr = None
        self._fh = None


    # CREDIT: OpenAI's ChatGPT
    def _normalize_files(self, files):
        """
        Normalize the input so it always returns a flat list of file paths, 
        even if nested lists are provided.
        """
        if isinstance(files, str):  # Single file (string)
            return [files]
        elif isinstance(files, list):  # List of files or nested lists
            flat_files = []
            for item in files:
                if isinstance(item, str):  # If item is a file (string), add it
                    flat_files.append(item)
                elif isinstance(item, list):  # If item is a nested list, flatten it
                    flat_files.extend(self._normalize_files(item))
            return flat_files
        else:
            raise ValueError("Files should be a string, list of strings, or nested list of strings.")


    # CREDIT: OpenAI's ChatGPT
    def __iter__(self):
        """
        Make the class iterable, so we can use it in a loop to process files one at a time.
        """
        return self


    # CREDIT: OpenAI's ChatGPT
    def __next__(self):
        """
        Return the next file path, and apply the operation (op) to it.
        """
        if self._index < len(self.files):
            file_path = self.files[self._index]
            self._index += 1
            self._curr = file_path  # Keep track of the current file
          
            # Close the last open file handle (if there is one).
            if self._fh:
                self._fh.close()
            self._fh = self._open(file_path)
            return self._fh
        else:
            # Close the final open file handle (if there is one).
            if self._fh:
                self._fh.close()
            raise StopIteration


    # CREDIT: OpenAI's ChatGPT
    # xxx look into contextlib from contextmanager, `@contextmanager`
    def _open(self, file_path):
        """
        Open the file with the specified operation and return the file handle.
        
        :param file_path: The path to the file to be opened.
        :return: The file handle.
        """
        try:
            # Open the file in the given mode (op) and return the file handle
            fh = open(file_path, self.op)
            return fh  # Return the file handle so the client can read/write as needed
        except FileNotFoundError as e:
            raise FileNotFoundError(f"File not found: {file_path}") from e
        except PermissionError as e:
            raise PermissionError(f"Permission denied: {file_path}") from e
        except Exception as e:
            raise Exception(f"An error occurred while processing {file_path}") from e


    # CREDIT: OpenAI's ChatGPT
    def get_type(self):
        """
        Return the file extension (type) of the current file being processed.
        """
        if self._curr is None:
            raise ValueError("No current file being processed. Make sure to call __next__() first.")

        _, ext = os.path.splitext(self._curr)
        return ext  # Returns the file extension (e.g., '.hpp', '.cpp', etc.)

