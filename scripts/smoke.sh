#!/usr/bin/env bash
set -euo pipefail
curl -sS http://127.0.0.1:8010/health | grep -q '"ok":true'
