#!/usr/bin/env python3
import os
import shlex
import shutil
import subprocess
import sys
import tempfile

BINSTALL_INSTALL_URL = (
    "https://raw.githubusercontent.com/cargo-bins/cargo-binstall/main/"
    "install-from-binstall-release.sh"
)


def command_exists(command: str) -> bool:
    return shutil.which(command) is not None


def ensure_binstall() -> None:
    if command_exists("cargo-binstall"):
        return

    curl_available = command_exists("curl")
    curl_success = False
    if curl_available:
        temp_script = None
        try:
            with tempfile.NamedTemporaryFile(delete=False) as handle:
                temp_script = handle.name
            result = subprocess.run(
                [
                    "curl",
                    "-L",
                    "--proto",
                    "=https",
                    "--tlsv1.2",
                    "-sSf",
                    BINSTALL_INSTALL_URL,
                    "-o",
                    temp_script,
                ]
            )
            if result.returncode == 0:
                result = subprocess.run(["bash", temp_script])
                if result.returncode == 0:
                    curl_success = True
        finally:
            if temp_script and os.path.exists(temp_script):
                os.unlink(temp_script)

    if not command_exists("cargo-binstall"):
        if curl_available and curl_success:
            print(
                "cargo-binstall not found after installer (PATH or install issue); "
                "using cargo install fallback.",
                file=sys.stderr,
            )
        elif curl_available:
            print(
                "cargo-binstall installer failed; using cargo install fallback.",
                file=sys.stderr,
            )
        else:
            print("curl not available; using cargo install fallback.", file=sys.stderr)
        subprocess.run(["cargo", "install", "cargo-binstall", "--locked"], check=True)


def ensure_tool(check_cmd: str, package: str) -> None:
    check_args = shlex.split(check_cmd)
    result = subprocess.run(
        check_args,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if result.returncode == 0:
        return

    ensure_binstall()
    if command_exists("cargo-binstall"):
        result = subprocess.run(["cargo-binstall", "-y", package])
        if result.returncode == 0:
            return

    subprocess.run(["cargo", "install", package, "--locked"], check=True)
