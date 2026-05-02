import subprocess
import os

os.chdir(r"C:\Users\III-AIPC-02\.nanobot\workspace\travel_app")

# 設定 credential helper
subprocess.run(["git", "config", "credential.helper", "store --file=.git-credentials"], check=True)

# add & commit
subprocess.run(["git", "add", "."], check=True)
subprocess.run(["git", "commit", "-m", "Fix: model name 27B, clean remote URL, path fix, gitignore"], check=True)

# push
result = subprocess.run(["git", "push", "origin", "master"], capture_output=True, text=True, encoding="utf-8", errors="replace")
print("STDOUT:", result.stdout)
print("STDERR:", result.stderr)
print("Return code:", result.returncode)
