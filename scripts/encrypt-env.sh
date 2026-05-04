#!/usr/bin/env bash
set -euo pipefail

# ColorForge AI — Encrypt .env file using sops+age
# Usage: ./scripts/encrypt-env.sh [age-recipient-public-key]

AGE_RECIPIENT="${1:-}"

if [ -z "$AGE_RECIPIENT" ]; then
  echo "Usage: ./scripts/encrypt-env.sh <age-recipient-public-key>"
  echo "Example: ./scripts/encrypt-env.sh age1xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
  exit 1
fi

if [ ! -f .env ]; then
  echo "Error: .env file not found"
  exit 1
fi

command -v sops >/dev/null 2>&1 || { echo "sops required: brew install sops"; exit 1; }

sops --encrypt --age "$AGE_RECIPIENT" .env > .env.encrypted
echo "Encrypted .env -> .env.encrypted"
echo "Add .env.encrypted to git, never commit .env"
