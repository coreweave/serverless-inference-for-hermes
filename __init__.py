# SPDX-FileCopyrightText: 2026 CoreWeave, Inc.
# SPDX-License-Identifier: MIT
# SPDX-PackageName: serverless-inference-for-hermes

"""Hermes Agent provider profile for CoreWeave Serverless Inference."""

from providers import register_provider
from providers.base import ProviderProfile


coreweave = ProviderProfile(
    name="coreweave",
    api_mode="chat_completions",
    display_name="CoreWeave Inference",
    description="CoreWeave Serverless Inference using its OpenAI-compatible API.",
    signup_url="https://wandb.ai/authorize",
    env_vars=("COREWEAVE_API_KEY",),
    base_url="https://api.inference.wandb.ai/v1",
    auth_type="api_key",
)

register_provider(coreweave)
