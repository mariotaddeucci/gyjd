import argparse
import os
import subprocess
import sys


def install_dependencies():
    try:
        import nuitka
    except ImportError:
        print("Nuitka not found. Installing package gyjd[compiler]...")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "gyjd[compiler]"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


def compile_file(filename):
    try:
        subprocess.run(
            ["nuitka", "--follow-imports", "--onefile", filename], check=True
        )
        print(f"Successfully compiled {filename} using Nuitka.")
    except subprocess.CalledProcessError as e:
        print(f"Error during compilation: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Python CLI to compile files with Nuitka."
    )
    parser.add_argument(
        "--compile", type=str, help="Specify the Python file to compile with Nuitka."
    )

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
