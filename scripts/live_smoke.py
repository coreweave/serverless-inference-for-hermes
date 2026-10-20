# SPDX-FileCopyrightText: 2026 CoreWeave, Inc.
# SPDX-License-Identifier: MIT
# SPDX-PackageName: serverless-inference-for-hermes

"""Run explicitly inside an approved sandbox with a separate demo credential."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from urllib.parse import urlsplit

REVISION = "d923a5eb487a17c0a68801bba9ef0f56c81040a8"
PLUGIN = Path(__file__).resolve().parents[1]


def main():
    if sys.platform != "linux":
        raise SystemExit("Use an approved Linux sandbox; do not run Hermes on this Mac.")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hermes", type=Path, required=True)
    parser.add_argument("--model", required=True, help="An account-authorized, tool-capable model ID")
    args = parser.parse_args()
    hermes = args.hermes.resolve()
    head = subprocess.check_output(["git", "-C", str(hermes), "rev-parse", "HEAD"], text=True).strip()
    if head != REVISION:
        raise SystemExit("Unexpected Hermes revision; review compatibility before changing the pin.")
    if subprocess.check_output(
        ["git", "-C", str(hermes), "status", "--porcelain", "--untracked-files=all"], text=True).strip():
        raise SystemExit("Use a clean Hermes checkout; tracked and untracked changes are not allowed.")
    key = os.environ.get("COREWEAVE_API_KEY", "").strip()
    if not key:
        raise SystemExit("Supply the approved demo key through COREWEAVE_API_KEY; never a command argument.")
    os.umask(0o077)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run = PLUGIN / ".local" / ("live-" + stamp)
    home = run / "home"
    installed = home / "plugins" / "serverless-inference-for-hermes"
    installed.mkdir(parents=True)
    plugin_file_sha256 = {}
    for name in ("__init__.py", "plugin.yaml"):
        shutil.copyfile(PLUGIN / name, installed / name)
        plugin_file_sha256[name] = hashlib.sha256((installed / name).read_bytes()).hexdigest()
    # Configuration deliberately contains no custom provider entry: discovery must use the plugin.
    (home / "config.yaml").write_text(json.dumps({"model": {"provider": "coreweave", "default": args.model}}))
    work = run / "work"
    work.mkdir()
    (work / "input.txt").write_text("coreweave-plugin-ok\n")
    prompt = work / "prompt.txt"
    prompt.write_text("Use read_file to read input.txt. Use write_file to copy its exact contents to output.txt. "
                      "Use read_file to verify output.txt, then say whether it matches. Use only file tools.")
    env = {"PATH": os.environ["PATH"], "HOME": str(home), "HERMES_HOME": str(home),
           "HERMES_RUNTIME_DIR": str(run / "runtime"), "PYTHONPATH": str(hermes),
           "COREWEAVE_API_KEY": key}
    # Keep the sandbox's egress proxy and trust roots without inheriting other credentials.
    proxy_values = []
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
        value = os.environ.get(name)
        if value:
            try:
                proxy = urlsplit(value)
                valid = (proxy.scheme in ("http", "https") and proxy.hostname
                         and proxy.username is None and proxy.password is None)
            except ValueError:
                valid = False
            if not valid:
                raise SystemExit(f"{name} must be an HTTP(S) proxy URL without credentials.")
            env[name] = value
            proxy_values.append(value)
    for name in ("SSL_CERT_FILE", "REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE", "NODE_EXTRA_CA_CERTS"):
        value = os.environ.get(name)
        if value:
            certificate = Path(value).resolve()
            if not certificate.is_file() or not os.access(certificate, os.R_OK):
                raise SystemExit(f"{name} must name a readable certificate bundle.")
            env[name] = str(certificate)
    if "SSL_CERT_FILE" in env:
        env["GIT_SSL_CAINFO"] = env["SSL_CERT_FILE"]
    command = ["bash", str(hermes / "scripts/run-in-hermes-env"), "python3", str(hermes / "hermes"),
               "chat", "--provider", "coreweave", "--model", args.model, "--toolsets", "file",
               "--max-turns", "8", "--oneshot", "--query-file", str(prompt), "--format", "stream-json"]
    print("Running the plugin file-task smoke test; credentials will not be printed.", flush=True)
    try:
        result = subprocess.run(command, cwd=work, env=env, capture_output=True, text=True, timeout=600)
    except subprocess.TimeoutExpired:
        raise SystemExit("Smoke test timed out; no successful result recorded.") from None
    transcript, runtime_log = result.stdout, result.stderr
    for value in (key, *proxy_values):
        transcript = transcript.replace(value, "[REDACTED]")
        runtime_log = runtime_log.replace(value, "[REDACTED]")
    (run / "transcript.jsonl").write_text(transcript)
    (run / "runtime.log").write_text(runtime_log)
    events = []
    for line in transcript.splitlines():
        try:
            event = json.loads(line)
            if isinstance(event, dict):
                events.append(event)
        except ValueError:
            continue
    used = [e.get("name") for e in events if e.get("type") == "tool_use"]
    completed = [e for e in events if e.get("type") == "result" and e.get("exit_code") == 0 and e.get("text")]
    failures = [e for e in events if e.get("type") == "tool_result" and e.get("is_error")]
    output = work / "output.txt"
    passed = (result.returncode == 0 and output.is_file() and output.read_text() == "coreweave-plugin-ok\n"
              and used.count("read_file") >= 2 and "write_file" in used and bool(completed) and not failures)
    (run / "verification.json").write_text(json.dumps({"passed": passed, "hermes_revision": head,
        "plugin_file_sha256": plugin_file_sha256,
        "plugin_install": "local filesystem discovery", "tool_calls": used,
        "tool_errors": len(failures), "exit_code": result.returncode,
        "not_verified": ["public repository installation", "HTTP streaming", "project attribution",
                         "live invalid-key and denied-model handling"]}, indent=2) + "\n")
    print(("PASS" if passed else "FAIL") + ": plugin agent file task. Evidence: " + str(run))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
