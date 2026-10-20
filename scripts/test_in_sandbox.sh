#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 CoreWeave, Inc.
# SPDX-License-Identifier: MIT
# SPDX-PackageName: serverless-inference-for-hermes

set -euo pipefail
if [[ "$(uname -s)" != "Linux" ]]; then
  echo "Use an approved Linux sandbox; this runner does not run Hermes on macOS." >&2
  exit 2
fi
if [[ $# -ne 1 ]]; then
  echo "Usage: $0 /absolute/path/to/hermes-agent" >&2
  exit 2
fi
plugin_root="$(cd "$(dirname "$0")/.." && pwd)"
hermes_root="$(cd "$1" && pwd)"
expected=d923a5eb487a17c0a68801bba9ef0f56c81040a8
if [[ "$(git -C "$hermes_root" rev-parse HEAD)" != "$expected" ]]; then
  echo "Expected Hermes revision $expected. Review compatibility before changing the pin." >&2
  exit 2
fi
checkout_status="$(git -C "$hermes_root" status --porcelain --untracked-files=all)"
if [[ -n "$checkout_status" ]]; then
  echo "Use a clean Hermes checkout; tracked and untracked changes are not allowed." >&2
  exit 2
fi
sandbox_state="$(mktemp -d)"
trap 'rm -rf -- "$sandbox_state"' EXIT
# No real API key is needed: test_provider.py uses synthetic credentials and blocks network.
cd "$hermes_root"
sandbox_env=(PATH="$PATH" HOME="$sandbox_state" HERMES_HOME="$sandbox_state/hermes"
  HERMES_RUNTIME_DIR="$sandbox_state/runtime" PYTHONPATH="$hermes_root")
for name in HTTP_PROXY HTTPS_PROXY http_proxy https_proxy SSL_CERT_FILE \
  REQUESTS_CA_BUNDLE CURL_CA_BUNDLE NODE_EXTRA_CA_CERTS; do
  if [[ -n "${!name:-}" ]]; then
    sandbox_env+=("$name=${!name}")
  fi
done
if [[ -n "${SSL_CERT_FILE:-}" ]]; then
  sandbox_env+=("GIT_SSL_CAINFO=$SSL_CERT_FILE")
fi
env -i "${sandbox_env[@]}" \
  bash scripts/run-in-hermes-env python3 "$plugin_root/tests/test_provider.py"
