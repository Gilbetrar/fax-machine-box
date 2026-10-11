"""Dev helper: poll `git fetch` until origin/<branch> moves off <sha> (or timeout)."""
import subprocess
import sys
import time

branch, sha, minutes = sys.argv[1], sys.argv[2], float(sys.argv[3])
end = time.time() + minutes * 60
while time.time() < end:
    subprocess.run(["git", "fetch", "-q", "origin"], check=False)
    cur = subprocess.run(["git", "rev-parse", f"origin/{branch}"], capture_output=True, text=True).stdout.strip()
    if not cur.startswith(sha):
        print("moved", cur)
        print(subprocess.run(["git", "log", "--oneline", "-4", f"origin/{branch}"], capture_output=True, text=True).stdout)
        sys.exit(0)
    time.sleep(150)
print("no new commit")
