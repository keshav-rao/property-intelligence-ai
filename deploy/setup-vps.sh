#!/usr/bin/env bash
# One-time setup on a fresh Ubuntu 22.04/24.04 VPS (2 vCPU / 4 GB RAM is plenty).
# Usage:  DOMAIN=chat.example.com REPO=https://github.com/<you>/property-intelligence-ai.git bash setup-vps.sh
# Before running: point an A record for $DOMAIN at this server's IP.
set -euo pipefail

: "${DOMAIN:?Set DOMAIN, e.g. chat.example.com}"
: "${REPO:?Set REPO to the git URL of this project}"

if ! command -v docker >/dev/null; then
  curl -fsSL https://get.docker.com | sh
fi
sudo ufw allow 22/tcp >/dev/null 2>&1 || true
sudo ufw allow 80/tcp >/dev/null 2>&1 || true
sudo ufw allow 443/tcp >/dev/null 2>&1 || true

if [ ! -d property-intelligence-ai ]; then
  git clone "$REPO" property-intelligence-ai
fi
cd property-intelligence-ai
git pull --ff-only

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Edit .env and set OPENROUTER_API_KEY, then re-run this script."
  exit 1
fi

export DOMAIN
export CORS_ORIGINS="https://$DOMAIN"
docker compose --profile https up -d --build
echo "Deployed. Open https://$DOMAIN (the first certificate can take a minute)."
