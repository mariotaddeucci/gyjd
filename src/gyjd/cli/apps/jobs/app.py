import os
import subprocess
from pathlib import Path
from typing import Annotated

import typer

app = typer.Typer(no_args_is_help=True, help="CLI for managing jobs.")


@app.command(help="Start dagster server.")
def server(
    target: Annotated[
        Path,
        typer.Argument(
            help="Path that contains the scripts to run.",
        ),
    ] = Path("scripts"),
):
    repos_dir = Path(__file__).parent / "repos"

    dependencies = ["dagster-webserver", "uv"]

    command = ["uvx", "--with", ",".join(dependencies), "dagster", "dev"]

    for repo in repos_dir.glob("*.py"):
        command.extend(["-f", str(repo)])

    envs = os.environ.copy()
    envs["GYJD_SCRIPTS_PATH"] = str(target.absolute())

    process = subprocess.run(command, stdout=None, stderr=None, text=True, env=envs)

    print(f"Exit Code: {process.returncode}")


@app.command(help="Create python script job.")
def create_script(
    name: Annotated[str, typer.Argument(help="Name of the script.")],
    python_version: Annotated[str, typer.Option(help="Python version to use.", prompt=True)] = "3.11",
):
    print("Deleting user: Hiro Hamada")
