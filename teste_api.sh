#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
printf '%s\n' 'AVISO: este teste chama sua API paga e pode gerar custo.'
python3 thigas_wiki.py --teste-api
