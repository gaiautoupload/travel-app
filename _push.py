import subprocess
import os

os.chdir(r"C:\Users\III-AIPC-02\.nanobot\workspace\travel_app")

subprocess.run(["git", "add", "."], check=True)
subprocess.run(["git", "commit", "-m", "Fix: test import path for cross-platform compatibility"], check=True)
result = subprocess.run(["git", "push", "origin", "master"], capture_output=True, text=True, encoding="utf-8", errors="replace")
print("STDOUT:", result.stdout)
print("STDERR:", result.stderr)
print("Return code:", result.returncode)
