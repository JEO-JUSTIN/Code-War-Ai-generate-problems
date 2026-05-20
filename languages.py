"""
Language configuration for the code execution engine.
Each entry defines the filename, optional compile command, and run command.
"""

LANGUAGES = {
    "python": {
        "filename": "main.py",
        "compile": None,  # interpreted, no compile step
        "run": ["python3", "main.py"],
    },
    "c": {
        "filename": "main.c",
        "compile": ["gcc", "main.c", "-o", "main", "-lm", "-Wall"],
        "run": ["./main"],
    },
    "java": {
        "filename": "Main.java",
        "compile": ["javac", "Main.java"],
        "run": ["java", "Main"],
    },
}


def get_language_config(language: str) -> dict:
    """
    Return the config dict for the requested language.
    Raises ValueError for unsupported languages.
    """
    key = language.strip().lower()
    if key not in LANGUAGES:
        raise ValueError(
            f"Unsupported language '{language}'. "
            f"Supported: {', '.join(LANGUAGES.keys())}"
        )
    return LANGUAGES[key]
