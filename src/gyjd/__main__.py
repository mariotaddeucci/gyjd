import importlib
import importlib.util
import os
import shutil
import subprocess
import sys
import time
from collections import deque
from pathlib import Path
from typing import Annotated, Iterator

import click
import typer

app = typer.Typer(no_args_is_help=True)


def print_boxed_output(lines: Iterator[str], max_length: int = 120):
    if max_length == 0:
        max_length = max(len(line) for line in lines) if lines else 0

    top_border = click.style("╭" + "─" * (max_length + 2) + "╮", fg="bright_black")
    bottom_border = click.style("╰" + "─" * (max_length + 2) + "╯", fg="bright_black")
    click.echo(top_border)
    for line in lines:
        padded_line = line[:max_length].ljust(max_length)
        click.echo(click.style(f"│ {padded_line} │", fg="bright_black"))
    click.echo(bottom_border)


def execute_command(command: list[str]):
    spool = deque(maxlen=3)

    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if process.stdout:
        while process.poll() is None:
            if spool:
                sys.stdout.write("\033[F" * (len(spool) + 2))
                sys.stdout.flush()

            if output := process.stdout.readline():
                spool.append(output.strip())

            print_boxed_output(lines=spool)
            time.sleep(0.1)

        process.stdout.close()

    process.wait()


def install_dependencies():
    try:
        importlib.import_module("nuitka")
    except ImportError:
        click.echo("Installing gyjd[compiler]...")
        execute_command([sys.executable, "-m", "pip", "install", "gyjd[compiler]"])


@app.command(name="compile", help="Compile a Python file to an executable.", no_args_is_help=True)
def compile(
    filename: Annotated[
        Path,
        typer.Option(help="Python file to compile."),
    ],
):
    output_dir = "dist"
    install_dependencies()
    try:
        click.echo(f"Compiling {filename}...")
        execute_command(
            [
                sys.executable,
                "-m",
                "nuitka",
                "--follow-imports",
                "--onefile",
                f"--output-dir={output_dir}",
                "--assume-yes-for-downloads",
                str(filename),
            ]
        )
        click.echo(f"Successfully compiled {filename}.")
    except subprocess.CalledProcessError as e:
        click.echo(f"Error during compilation: {e}", file=sys.stderr, err=True)
        raise typer.Exit(code=1)

    for entry in os.listdir(output_dir):
        entry_uri = os.path.join(output_dir, entry)
        if not os.path.isfile(entry_uri):
            shutil.rmtree(entry_uri)


if __name__ == "__main__":
    app()
