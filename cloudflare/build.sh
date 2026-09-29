#!/bin/sh
# Copy exactly what the Worker needs into src/: the app's
# modules and data, never tests, .env files or the local
# usage ledger.
set -eu
cd "$(dirname "$0")"

rm -rf src
mkdir src
cp worker.py src/

for module in ../*.py; do
    case "$(basename "$module")" in
        conftest.py | loadtest.py | live_eval.py | gunicorn.conf.py | test_*.py) ;;
        *) cp "$module" src/ ;;
    esac
done

cp -R ../knowledge ../templates ../static ../wordlists src/
cp ../xeqm_knowledge.txt src/

find src \( -name __pycache__ -o -name .DS_Store \) -prune -exec rm -rf {} +
