import importlib
import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

import typer
from typing_extensions import Annotated

app = typer.Typer(no_args_is_help=True)


def install_dependencies():
    try:
        importlib.import_module("nuitka")
    except ImportError:
        print("Installing package gyjd[compiler]...")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "gyjd[compiler]"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        print("Successfully installed gyjd[compiler].")


@app.command(name="compile", help="Compile a Python file to an executable.", no_args_is_help=True)
def compile(
    filename: Annotated[
        Path,
        typer.Option(help="Python file to compile."),
    ],
):
    install_dependencies()
    dist_path = "dist"
    try:
        print(f"Compiling {filename}...")
        subprocess.run(
            [
                sys.executable,
                "-m",
                "nuitka",
                "--follow-imports",
                "--onefile",
                f"--output-dir={dist_path}",
                "--assume-yes-for-downloads",
                filename,
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        print(f"Successfully compiled {filename}.")
    except subprocess.CalledProcessError as e:
        print(f"Error during compilation: {e}", file=sys.stderr)
        sys.exit(1)

    for entry in os.listdir(dist_path):
        entry_uri = os.path.join(dist_path, entry)
        if not os.path.isfile(entry_uri):
            shutil.rmtree(entry_uri)


if __name__ == "__main__":
    app()
