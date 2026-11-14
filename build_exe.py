import os
import sys
import subprocess
import shutil

def build():
    print("=" * 60)
    print("Building standalone .exe with PyInstaller...")
    print("=" * 60)

    base_dir = os.path.dirname(os.path.abspath(__file__))
    icon_ico = os.path.join(base_dir, "icon.ico")
    icon_png = os.path.join(base_dir, "icon.png")

    # Command line args for PyInstaller
    cmd = [
        sys.executable,
        "-m", "PyInstaller",
        "--noconsole",
        "--onefile",
        "--clean",
        f"--name=USD_Rate_Monitor",
        f"--icon={icon_ico}",
        f"--add-data={icon_png};.",
        f"--add-data={icon_ico};.",
        "--collect-all=PySide6",
        os.path.join(base_dir, "app.py")
    ]

    print("Running:", " ".join(cmd))
    res = subprocess.run(cmd, cwd=base_dir)

    if res.returncode == 0:
        exe_path = os.path.join(base_dir, "dist", "USD_Rate_Monitor.exe")
        print("\n" + "=" * 60)
        print("BUILD SUCCESSFUL!")
        print(f"Standalone executable created at:\n{exe_path}")
        if os.path.exists(exe_path):
            size_mb = os.path.getsize(exe_path) / (1024 * 1024)
            print(f"File size: {size_mb:.2f} MB")
        print("=" * 60)
    else:
        print("\nBuild failed with code:", res.returncode)

if __name__ == "__main__":
    build()
