"""
Setup virtual environment and install dependencies for the datasheet reader skill.
Usage: python setup_env.py [--check-only]
"""
import subprocess
import sys
import os
from pathlib import Path


VENV_DIR = Path(__file__).resolve().parent.parent.parent.parent / ".venv"
REQUIREMENTS = ["pymupdf>=1.24.0"]


def get_venv_python() -> Path:
    if sys.platform == "win32":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def create_venv():
    print(f"Creating virtual environment at {VENV_DIR}...")
    subprocess.run([sys.executable, "-m", "venv", str(VENV_DIR)], check=True)
    print("Virtual environment created.")


def install_deps():
    python = get_venv_python()
    print("Installing dependencies...")
    subprocess.run(
        [str(python), "-m", "pip", "install", "--quiet"] + REQUIREMENTS,
        check=True,
    )
    print("Dependencies installed successfully.")


def check_import():
    python = get_venv_python()
    result = subprocess.run(
        [str(python), "-c", "import fitz; print(fitz.version)"],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        print(f"PyMuPDF version: {result.stdout.strip()}")
        return True
    return False


def main():
    check_only = "--check-only" in sys.argv

    if not VENV_DIR.exists():
        if check_only:
            print(f"MISSING: Virtual environment not found at {VENV_DIR}")
            sys.exit(1)
        create_venv()
        install_deps()
    else:
        python = get_venv_python()
        if not python.exists():
            if check_only:
                print(f"BROKEN: Python executable not found in {VENV_DIR}")
                sys.exit(1)
            create_venv()
            install_deps()

    if not check_import():
        if check_only:
            print("MISSING: PyMuPDF not importable")
            sys.exit(1)
        install_deps()
        if not check_import():
            print("ERROR: Failed to install PyMuPDF")
            sys.exit(1)

    print(f"OK: Environment ready at {VENV_DIR}")
    print(f"Python: {get_venv_python()}")


if __name__ == "__main__":
    main()
