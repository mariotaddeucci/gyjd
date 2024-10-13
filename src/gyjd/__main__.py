import argparse
import importlib
import os
import shutil
import subprocess
import sys


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


def compile_file(filename):
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


def main():
    parser = argparse.ArgumentParser(description="Python CLI to compile files with Nuitka.")
    parser.add_argument("--compile", type=str, help="Specify the Python file to compile with Nuitka.")

    args = parser.parse_args()
    if not args.compile:
        print("No file specified to compile. Use --compile <filename.py>.")
        sys.exit(1)

    filename = args.compile
    if not os.path.isfile(filename):
        print(f"File {filename} does not exist.", file=sys.stderr)
        sys.exit(1)

    compile_file(filename)


if __name__ == "__main__":
    main()
