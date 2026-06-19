#!/bin/sh
set -eu

if [ -z "${CHAINGUARD_JAVASCRIPT_IDENTITY_ID:-}" ] || [ -z "${CHAINGUARD_JAVASCRIPT_TOKEN:-}" ]; then
  echo "Missing Chainguard JavaScript auth env vars."
  echo "Run: eval \"\$(chainctl auth pull-token --output env --repository=javascript)\""
  exit 1
fi

npm_auth="$(printf '%s:%s' "$CHAINGUARD_JAVASCRIPT_IDENTITY_ID" "$CHAINGUARD_JAVASCRIPT_TOKEN" | base64 | tr -d '\n')"

cat > .npmrc <<EOF
registry=https://libraries.cgr.dev/javascript/
//libraries.cgr.dev/javascript/:_auth=${npm_auth}
EOF
