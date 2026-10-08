"""Build a standalone Windows executable and a portable distribution ZIP."""
from pathlib import Path
import argparse
import hashlib
import shutil
import subprocess
import sys
import zipfile


def main():
    if sys.platform != "win32":
        raise SystemExit("Windows EXE must be built on Windows.")
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="Build the portable LTE tester")
    parser.add_argument("--output-dir", default="dist", help="Output directory relative to lte_tester")
    args = parser.parse_args()
    dist = (root / args.output_dir).resolve()
    subprocess.run([
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--onefile", "--windowed",
        "--name", "PRE-LTE-Tester", "--distpath", str(dist),
        "--workpath", str(root / "build"), "--specpath", str(root / "build"),
        "--paths", str(root), "--exclude-module", "mariadb",
        "--exclude-module", "fastapi", "--exclude-module", "dotenv",
        str(root / "app.py"),
    ], cwd=root, check=True)
    exe = dist / "PRE-LTE-Tester.exe"
    shutil.copyfile(root / "README.md", dist / "README.md")
    digest = hashlib.sha256(exe.read_bytes()).hexdigest()
    (dist / "SHA256.txt").write_text(f"{digest}  {exe.name}\n", encoding="utf-8")
    with zipfile.ZipFile(dist / "PRE-LTE-Tester-Windows.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for path in (exe, dist / "README.md", dist / "SHA256.txt"):
            archive.write(path, arcname=path.name)
    print(f"Ready: {exe}")


if __name__ == "__main__":
    main()
