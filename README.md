<!--
SPDX-FileCopyrightText: 2026 CoreWeave, Inc.
SPDX-License-Identifier: MIT
SPDX-PackageName: serverless-inference-for-hermes
-->

# CoreWeave Inference for Hermes Agent

A standalone model-provider plugin that adds **CoreWeave Inference** to Hermes's
provider setup. It uses Hermes's existing OpenAI-compatible Chat Completions
transport and model discovery. It does not modify Hermes core, prompts, or tool
schemas, and adds no runtime dependencies of its own.

Hermes can already use CoreWeave as a custom endpoint. This plugin supplies the
provider name, endpoint, credential variable, and API-key signup link so users do
not need to enter that configuration themselves.

## Install and configure

Requires Hermes with standalone model-provider support. The integration checks
target Hermes v0.22.2, commit `d923a5eb487a17c0a68801bba9ef0f56c81040a8`.

Installation command:

```bash
hermes plugins install coreweave/serverless-inference-for-hermes
```

For development in an approved workspace, copy only `__init__.py` and
`plugin.yaml` into
`$HERMES_HOME/plugins/model-providers/serverless-inference-for-hermes/`.
Keep private test evidence and local notes outside the installed plugin.

Get an inference-enabled [W&B API key](https://wandb.ai/authorize). Supply it through
your workspace's secret mechanism as `COREWEAVE_API_KEY`, then run `hermes model`
and choose **CoreWeave Inference**. Select a model available to your account.
Do not put the key in source, command arguments, or recorded output.

The endpoint is `https://api.inference.wandb.ai/v1`. An empty or failed catalog
lookup is not proof that a model is available; this plugin deliberately does not
invent a fallback model list or claim capabilities for untested models.

Hermes fetches the model catalog from that endpoint and sends chat requests that
include prompts and tool results. Hermes handles the provider's API key.
The installed plugin reads no credential files, starts no shell commands or
background processes, and adds no telemetry.

## Optional project attribution

Project attribution is not part of the named plugin's initial contract. A bare
`providers.coreweave.extra_headers` block may be bypassed by Hermes's canonical
provider resolution. For explicit attribution, use the separate custom provider
in [examples/project-attribution.yaml](examples/project-attribution.yaml), replace
`TEAM/PROJECT`, and select `--provider custom:coreweave-project`.

This example is source-reviewed, not wire-verified. Confirm that inference requests
carry `openai-project` before relying on it for usage attribution. Do not add
credentials to the YAML file.

## Development and validation

Static checks do not import or run Hermes and need only Python's standard library:

```bash
python3 scripts/check_static.py
bash -n scripts/test_in_sandbox.sh
```

The CI workflow runs only these static checks. It does not establish host or live
API compatibility.

In an approved Linux workspace, prepare a clean official Hermes checkout at the
pinned commit, then run:

```bash
bash scripts/test_in_sandbox.sh /absolute/path/to/hermes-agent
```

The development runners use Hermes's package-manager wrapper, which may download
its pinned runtime dependencies, and read configured proxy settings and certificate
bundle files. The synthetic runner creates disposable settings, supplies synthetic
credentials, and runs the plugin through the real installed-provider discovery
path. Tests cover listing, runtime routing, missing credentials, model discovery,
catalog rejection, and provider discovery across profiles.

On the pinned Hermes revision, sandbox checks passed `hermes plugins doctor`,
all 14 `hermes plugins validate --install-deps` checks with no warnings, and all
six synthetic tests. These checks used manual development installation and no
inference credentials. Optional Chromium and CUA tools were unavailable due to
download restrictions and missing `libX11.so.6`; those tools are outside these
provider checks.

A live smoke test on October 15, 2026 used `moonshotai/Kimi-K2.6` with an
approved demo credential. The authenticated model-catalog preflight returned HTTP
200. Hermes discovered the plugin in a fresh profile, completed five file-tool
calls without tool errors, and produced an exact copy of the synthetic input file.
This verifies the agent file task; it does not establish project attribution.

Separate live API checks through Hermes provider resolution and request construction
verified authenticated model discovery, HTTP streaming with a clean stop, and an
HTTP 401 authentication error for an invalid key. Missing credentials failed without
selecting another provider; a rejected catalog lookup produced no fallback models.
A nonexistent model returned a generic HTTP 404, which Hermes classified as an
unknown, retryable error. Full chat-loop recovery and model-permission denials
remain unverified.

With a separate approved demo identity supplied through `COREWEAVE_API_KEY`, run:

```bash
python3 scripts/live_smoke.py --hermes /absolute/path/to/hermes-agent --model YOUR_MODEL_ID
```

Choose an account-authorized, tool-capable model. The runner uses a fresh profile
with this plugin and no custom-provider entry. It asks Hermes to read a synthetic
file, write a copy, and verify it. It requires successful tool calls and a final
response, redacts the supplied key, and saves evidence under ignored `.local/`.
It refuses macOS. That guard does not itself prove that a Linux workspace is
approved; use your organization's approved environment and credential process.

The recorded tests do not cover public installation, interactive provider/model
selection, full chat-loop recovery, or model-permission denials. Optional project
attribution also needs header capture.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution and validation guidance.
