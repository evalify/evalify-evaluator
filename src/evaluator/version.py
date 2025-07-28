"""
Version management for the Evaluator service.

This module provides centralized version information using importlib.metadata
to read the version from the installed package metadata.
"""

from importlib.metadata import PackageNotFoundError, version

# Package name as defined in pyproject.toml
PACKAGE_NAME = "evalify-evaluator"


def get_version() -> str:
    """
    Get the current version of the evaluator package.

    Returns:
        str: The version string from package metadata

    Raises:
        PackageNotFoundError: If the package is not installed or version cannot be determined
    """
    try:
        return version(PACKAGE_NAME)
    except PackageNotFoundError:
        # Fallback for development/testing when package is not installed
        return "0.1.0-dev"


def get_version_info() -> dict[str, str]:
    """
    Get detailed version information.

    Returns:
        dict: Dictionary containing version details
    """
    pkg_version = get_version()

    # Determine if this is a development version
    is_dev = pkg_version.endswith("-dev")

    # Parse version components
    version_parts = pkg_version.replace("-dev", "").split(".")
    major = version_parts[0] if len(version_parts) > 0 else "0"
    minor = version_parts[1] if len(version_parts) > 1 else "1"
    patch = version_parts[2] if len(version_parts) > 2 else "0"

    return {
        "version": pkg_version,
        "major": major,
        "minor": minor,
        "patch": patch,
        "is_development": str(is_dev).lower(),
        "package_name": PACKAGE_NAME,
    }


# Export the version for easy access
__version__ = get_version()
