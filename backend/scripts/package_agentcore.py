"""Build the Linux ARM64 ZIP consumed by AgentCore direct code deployment."""
from pathlib import Path
import shutil
import subprocess
import zipfile


BACKEND = Path(__file__).resolve().parents[1]
PROJECT = BACKEND.parent
BUILD = PROJECT / ".build" / "agentcore"
PACKAGE = BUILD / "package"
ARCHIVE = BUILD / "mom-life-agentcore.zip"


def main() -> None:
    if BUILD.exists():
        shutil.rmtree(BUILD)
    PACKAGE.mkdir(parents=True)
    subprocess.run(
        [
            "uv", "pip", "install",
            "--python-platform", "aarch64-manylinux2014",
            "--python-version", "3.14",
            "--target", str(PACKAGE),
            "--only-binary=:all:",
            "-r", str(BACKEND / "requirements.txt"),
        ],
        check=True,
    )
    for directory in ("agents", "app", "plugins", "tools"):
        shutil.copytree(
            BACKEND / directory,
            PACKAGE / directory,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            dirs_exist_ok=True,
        )
    shutil.copy2(BACKEND / "agentcore_main.py", PACKAGE / "agentcore_main.py")
    shutil.copy2(BACKEND / "certs" / "aws-rds-global-bundle.pem", PACKAGE / "aws-rds-global-bundle.pem")
    with zipfile.ZipFile(ARCHIVE, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in PACKAGE.rglob("*"):
            if path.is_file() and path.name != ".lock":
                archive.write(path, path.relative_to(PACKAGE))
    size_mb = ARCHIVE.stat().st_size / 1024 / 1024
    if size_mb > 250:
        raise RuntimeError(f"AgentCore archive is {size_mb:.1f} MB; the service limit is 250 MB.")
    print(f"Built {ARCHIVE} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
