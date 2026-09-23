"""Build and serve Career Quest with one command: python run.py."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--skip-build", action="store_true", help="Reuse an existing frontend production build")
    parser.add_argument("--setup-only", action="store_true", help="Install and build without starting the server")
    args = parser.parse_args()
    uv = shutil.which("uv")
    npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
    if not uv or (not args.skip_build and not npm):
        print("Required: Python 3.11+, uv, Node.js 22+ and npm on PATH.", file=sys.stderr)
        return 2
    try:
        subprocess.run([uv, "sync", "--frozen"], cwd=ROOT / "backend", check=True)
        if not args.skip_build:
            subprocess.run([npm, "ci"], cwd=ROOT / "frontend", check=True)
            subprocess.run([npm, "run", "build"], cwd=ROOT / "frontend", check=True)
        if not (ROOT / "frontend/dist/index.html").is_file():
            print("Frontend build missing: run without --skip-build.", file=sys.stderr)
            return 2
        if args.setup_only:
            return 0
        print(f"Career Quest: http://{args.host}:{args.port} (Ctrl+C to stop)", flush=True)
        return subprocess.call(
            [uv, "run", "--no-sync", "uvicorn", "app.main:app", "--host", args.host, "--port", str(args.port)],
            cwd=ROOT / "backend",
        )
    except subprocess.CalledProcessError as exc:
        print(f"Setup failed (exit {exc.returncode}); see command output above.", file=sys.stderr)
        return exc.returncode
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
