import os
import shutil
import subprocess
from pathlib import Path
from typing import Annotated

import typer

from gyjd.cli.apps.jobs.app import app as jobs_app

app = typer.Typer(no_args_is_help=True)
app.add_typer(jobs_app, name="jobs", help="CLI for managing jobs.")


@app.command(name="compile", help="Compile a Python file to an executable.", no_args_is_help=True)
def compile(
    filename: Annotated[
        Path,
        typer.Option(help="Python file to compile."),
    ],
):
    output_dir = "dist"

    commnad = [
        "uvx",
        "nuitka",
        "--follow-imports",
        "--onefile",
        f"--output-dir={output_dir}",
        "--assume-yes-for-downloads",
        str(filename),
    ]

    subprocess.run(commnad, stdout=None, stderr=None, text=True)

    for entry in os.listdir(output_dir):
        entry_uri = os.path.join(output_dir, entry)
        if not os.path.isfile(entry_uri):
            shutil.rmtree(entry_uri)


if __name__ == "__main__":
    app()
