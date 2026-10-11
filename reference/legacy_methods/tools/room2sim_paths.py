"""Portable paths shared by the preserved reconstruction scripts.

prepare_workspace.py places this file beside each staged Python script. Nothing
in this module assumes where this repository, the workspace, or inputs live.
"""

from __future__ import annotations

import os
from pathlib import Path
import shutil


def workspace_root() -> Path:
    configured = os.environ.get("ROOM2SIM_WORKSPACE")
    if configured:
        return Path(configured).expanduser().resolve()
    for directory in Path(__file__).resolve().parents:
        if (directory / ".room2sim-workspace").is_file():
            return directory
    raise RuntimeError(
        "No reconstruction workspace found. Run tools/prepare_workspace.py "
        "--workspace PATH, or set ROOM2SIM_WORKSPACE to your staged workspace."
    )


def _beneath(root: Path, relative: str | os.PathLike[str]) -> str:
    relative_path = Path(relative)
    if relative_path.is_absolute():
        raise ValueError(f"Expected a relative path, received {relative!r}")
    target = (root / relative_path).resolve()
    if not target.is_relative_to(root.resolve()):
        raise ValueError(f"Path leaves its configured root: {relative!r}")
    return str(target)


def project_path(relative: str | os.PathLike[str] = "") -> str:
    """Resolve a path underneath the prepared working directory."""
    return _beneath(workspace_root(), relative)


def input_path(relative: str | os.PathLike[str] = "") -> str:
    """Resolve original videos, captures, or datasets in the inputs directory."""
    configured = os.environ.get("ROOM2SIM_INPUTS")
    root = Path(configured).expanduser().resolve() if configured else workspace_root() / "inputs"
    return _beneath(root, relative)


def _configured_executable(variable: str) -> str | None:
    value = os.environ.get(variable)
    if not value:
        return None
    path = Path(value).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"{variable} points to a missing executable: {path}")
    return str(path)


def browser_path() -> str | None:
    """Use Playwright's browser by default, or an explicitly supplied browser."""
    return _configured_executable("ROOM2SIM_BROWSER")


def openmvs_path(tool: str = "DensifyPointCloud") -> str:
    """Locate an OpenMVS program without assuming a locally compiled layout."""
    if Path(tool).name != tool:
        raise ValueError("OpenMVS tool must be a program name, not a path")
    directory = os.environ.get("ROOM2SIM_OPENMVS_BIN")
    if directory:
        candidate = Path(directory).expanduser().resolve() / tool
        if not candidate.is_file():
            raise FileNotFoundError(f"OpenMVS executable is missing: {candidate}")
        return str(candidate)
    executable = shutil.which(tool)
    if executable:
        return executable
    raise FileNotFoundError(
        f"{tool} is not on PATH. Install OpenMVS and set ROOM2SIM_OPENMVS_BIN "
        "to its executable directory."
    )


def ffmpeg_path() -> str:
    """Locate the FFmpeg command used by preview and video export scripts."""
    configured = _configured_executable("ROOM2SIM_FFMPEG")
    executable = configured or shutil.which("ffmpeg")
    if executable:
        return executable
    raise FileNotFoundError("Install FFmpeg on PATH or set ROOM2SIM_FFMPEG.")
