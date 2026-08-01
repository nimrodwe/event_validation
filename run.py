#!/usr/bin/env python3
"""Start the pipeline from the command line."""

import argparse
import shutil
import subprocess
import sys

from helpers.generator import Generator
from src.config import OUT
from src.pipeline import Sender
from src.receiver import Receiver, connect as connect_receiver
from src.report import Report
from src.validate import Validator


def run_allure():
    """Run pytest with Allure results, then open the local Allure report."""
    results = OUT / "allure-results"
    results.mkdir(parents=True, exist_ok=True)

    print("Running pytest (Allure results → " + str(results) + ")")
    code = subprocess.call([sys.executable, "-m", "pytest", "-v"])

    allure = shutil.which("allure")
    if allure is None:
        print("")
        print("Pytest finished. Install the Allure commandline to open the HTML report:")
        print("  npm install -g allure-commandline")
        print("  # or: scoop install allure")
        print("  # or: choco install allure-commandline")
        print("")
        print("Then run:")
        print("  allure serve " + str(results))
        return code

    print("Opening Allure report...")
    serve_code = subprocess.call([allure, "serve", str(results)])
    if serve_code != 0:
        return serve_code
    return code


def run_docker(docker_args):
    """Start Docker Desktop if needed, then run docker (default: compose up --build)."""
    from src.docker_desktop import ensure_running

    ensure_running()
    if docker_args and docker_args[0] == "--":
        docker_args = docker_args[1:]
    argv = list(docker_args) if docker_args else ["compose", "up", "--build"]
    print("Running: docker " + " ".join(argv))
    return subprocess.call(["docker"] + argv)


class App:
    def __init__(self):
        self.generator = Generator()
        self.sender = Sender()
        self.validator = Validator()
        self.report = Report()

    def run_all(self):
        received_dir = OUT / "received"
        if received_dir.exists():
            shutil.rmtree(received_dir)

        self.generator.generate(OUT)
        server = connect_receiver(received_dir)

        try:
            self.sender.send(OUT / "generated", server.port)

            findings = self.validator.validate_dataset()
            received_findings = self.validator.validate_received(received_dir / "events.jsonl")
            findings = findings + received_findings

            self.report.write(findings)

            if not self.validator.golden_ok(findings):
                print("Golden check failed")
                return 1

            print("Pipeline complete — 26 golden defects found")
            print("")
            print("  Report: " + str(OUT / "report" / "index.html"))
            print("  Dashboard: python run.py")
            print("")
            return 0
        finally:
            server.disconnect()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "cmd",
        nargs="?",
        default="stack",
        choices=["all", "gen", "validate", "serve", "dashboard", "stack", "allure", "docker"],
        help="Command to run (default: stack = dashboard + receiver)",
    )
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-open", action="store_true")
    parser.add_argument(
        "docker_args",
        nargs=argparse.REMAINDER,
        help="Args after 'docker' (default: compose up --build). Example: "
        "python run.py docker -- compose --profile test run --rm test",
    )
    args = parser.parse_args()

    app = App()

    if args.cmd == "gen":
        app.generator.generate()
        print("Generated out/generated/")
        return

    if args.cmd == "validate":
        findings = app.validator.validate_dataset()
        findings = findings + app.validator.validate_received(OUT / "received" / "events.jsonl")
        app.report.write(findings)
        if not app.validator.golden_ok(findings):
            sys.exit(1)
        print("Golden OK: 26 defect rows")
        return

    if args.cmd == "serve":
        Receiver(OUT / "received").start(args.port, blocking=True)
        return

    if args.cmd == "dashboard":
        port = 8080
        if args.port != 8765:
            port = args.port
        open_browser = not args.no_open
        app.report.serve(port, open_browser)
        return

    if args.cmd == "stack":
        from src.local_stack import LocalStack

        LocalStack().run(open_browser=not args.no_open)
        return

    if args.cmd == "allure":
        sys.exit(run_allure())

    if args.cmd == "docker":
        sys.exit(run_docker(args.docker_args))

    # cmd == all
    code = app.run_all()
    sys.exit(code)


if __name__ == "__main__":
    main()
