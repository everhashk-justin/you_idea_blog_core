"""
blog_core.analytics.credentials - Lazy Service Account Credentials Locator
Discovers Google Service Account JSON files from paths, environment variables, and defaults.
"""

import os
from pathlib import Path
from typing import Optional, List, Union

KNOWN_CREDENTIAL_FILENAMES = [
    "blog-analytics-513909-90ec135313ba.json",
    "service_account.json",
    "credentials.json",
]

DEFAULT_SEARCH_DIRS = [
    Path.cwd(),
    Path(r"D:\00_antigravity\01_you_idea_blog"),
]


def find_credentials(
    search_paths: Optional[List[Union[str, Path]]] = None,
    explicit_path: Optional[Union[str, Path]] = None,
    env_var: Optional[str] = None
) -> Optional[str]:
    """
    Locates Google Service Account JSON credentials without raising exceptions if missing.
    Resolution priority:
    1. Explicit path parameter (if specified: returns resolved path if exists, otherwise None)
    2. Environment variable (target env_var or GOOGLE_APPLICATION_CREDENTIALS)
    3. Search directories (known filenames, followed by blog-analytics*.json glob)
    """
    if explicit_path is not None:
        p = Path(explicit_path)
        if p.exists() and p.is_file():
            return str(p.resolve())
        return None

    target_env = env_var or "GOOGLE_APPLICATION_CREDENTIALS"
    env_val = os.environ.get(target_env)
    if env_val:
        p = Path(env_val)
        if p.exists() and p.is_file():
            return str(p.resolve())

    dirs_to_check: List[Path] = []
    if search_paths:
        for sp in search_paths:
            dirs_to_check.append(Path(sp))
    for default_dir in DEFAULT_SEARCH_DIRS:
        if default_dir not in dirs_to_check:
            dirs_to_check.append(default_dir)

    for directory in dirs_to_check:
        if not directory.exists() or not directory.is_dir():
            continue

        # Check known filenames
        for fname in KNOWN_CREDENTIAL_FILENAMES:
            candidate = directory / fname
            if candidate.exists() and candidate.is_file():
                return str(candidate.resolve())

        # Check glob pattern for blog-analytics*.json
        try:
            for candidate in directory.glob("blog-analytics*.json"):
                if candidate.is_file():
                    return str(candidate.resolve())
        except Exception:
            pass

    return None
