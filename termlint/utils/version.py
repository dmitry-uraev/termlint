"""Version helpers."""

from importlib.metadata import PackageNotFoundError, version


def get_termlint_version() -> str:
    """Return installed package version, or a dev fallback."""
    try:
        return version("termlint")
    except PackageNotFoundError:
        return "0.0.0+local"
