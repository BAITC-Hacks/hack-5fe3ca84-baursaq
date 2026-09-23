"""One-command setup: python run.py --setup. Subsequent runs: python run.py."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import venv

ROOT = Path(__file__).resolve().parent


def run(*args):
    subprocess.run([str(a) for a in args], cwd=ROOT, check=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--setup', action='store_true', help='Create .venv, install dependencies and build UI')
    parser.add_argument('--build', action='store_true', help='Rebuild frontend')
    args = parser.parse_args()
    python = ROOT / '.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    if args.setup:
        npm = shutil.which('npm.cmd' if os.name == 'nt' else 'npm')
        if not npm:
            raise SystemExit('Install Node.js 22+ with npm first.')
        if not python.exists():
            venv.EnvBuilder(with_pip=True).create(ROOT / '.venv')
        run(python, '-m', 'pip', 'install', '-r', 'requirements.txt')
        run(npm, '--prefix', 'frontend', 'ci')
        run(npm, '--prefix', 'frontend', 'run', 'build')
    elif args.build:
        npm = shutil.which('npm.cmd' if os.name == 'nt' else 'npm')
        if not npm:
            raise SystemExit('Install Node.js 22+ with npm first.')
        run(npm, '--prefix', 'frontend', 'run', 'build')
    executable = python if python.exists() else sys.executable
    if not (ROOT / 'frontend' / 'dist' / 'index.html').exists():
        raise SystemExit('Frontend missing. First run: python run.py --setup')
    print('Career Quest: http://127.0.0.1:' + os.getenv('PORT', '8000'), flush=True)
    run(executable, '-m', 'uvicorn', 'backend.app.main:app', '--host', '127.0.0.1', '--port', os.getenv('PORT', '8000'))
