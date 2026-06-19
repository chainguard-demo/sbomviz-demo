<p align="center">
  <img src="static/logo_sbomviz.png" alt="sbomviz logo" width="320">
</p>

# sbomviz

`sbomviz` is a Python web app that ingests an SPDX SBOM JSON file and presents a human-friendly report with:

- Document metadata (name, SPDX version, creators, creation date)
- Summary cards for package, relationship, relationship-type, and supplier counts
- A searchable package inventory (name, version, SPDX ID, supplier)
- A searchable dependency/relationship table with color-coded relationship types
- A Tailwind CSS dark-themed UI with responsive layout

## Container-only development rule

This project **must be developed and run only in containers**.

- Use the Chainguard-based container defined in `Dockerfile`
- Do **not** install Python dependencies on the host machine
- Do **not** run `python` or `flask` commands on the host
- Use Docker Compose commands below for all execution

## Prerequisites

- Docker with Compose support
- `chainctl` authenticated to Chainguard

## Chainguard Libraries setup (required)

This project installs **Python** and **JavaScript** dependencies from Chainguard Libraries. You need pull tokens for both ecosystems before building or starting containers.

### Python

Obtain Python auth variables from Chainguard:

```bash
eval "$(chainctl auth pull-token --output env --repository=python --parent=example)"
```

Quick check:

```bash
echo "$CHAINGUARD_PYTHON_IDENTITY_ID"
echo "$CHAINGUARD_PYTHON_TOKEN"
```

Python packages are installed during the `sbomviz` image build from:

- `https://libraries.cgr.dev/python/simple/` as the only package index (no PyPI fallback)
- credentials from `CHAINGUARD_PYTHON_IDENTITY_ID` and `CHAINGUARD_PYTHON_TOKEN`

Important: these credentials may include URL-special characters. The Dockerfile URL-encodes both values before constructing `PIP_INDEX_URL`.

### JavaScript

Obtain JavaScript auth variables from Chainguard:

```bash
eval "$(chainctl auth pull-token --output env --repository=javascript --parent=example)"
```

Quick check:

```bash
echo "$CHAINGUARD_JAVASCRIPT_IDENTITY_ID"
echo "$CHAINGUARD_JAVASCRIPT_TOKEN"
```

JavaScript packages are installed from:

- `https://libraries.cgr.dev/javascript/` as the npm registry (no npmjs.org fallback)
- credentials from `CHAINGUARD_JAVASCRIPT_IDENTITY_ID` and `CHAINGUARD_JAVASCRIPT_TOKEN`

The project generates a local `.npmrc` at build/watch time via `scripts/configure-npm-libraries.sh`. This file is gitignored because it contains credentials.

### One-time lockfile migration (JavaScript)

If `package-lock.json` was created against the public npm registry, update integrity hashes before the first Chainguard install:

```bash
eval "$(chainctl auth pull-token --output env --repository=javascript --parent=example)"

docker compose run --rm --no-deps css "./scripts/configure-npm-libraries.sh"

rm -rf node_modules

chainctl libraries update-hashes --replace package-lock.json

docker compose run --rm --no-deps css "npm install"
```

`rm -rf node_modules` is a host filesystem cleanup (not an npm command). `chainctl libraries update-hashes --replace` also runs on the host and replaces npmjs.org integrity hashes with Chainguard checksums (`--replace` is required for `package-lock.json`, which only stores one hash per package).

If `npm install` still reports `EINTEGRITY` for a package listed as "not in Chainguard", remove the lockfile and regenerate it entirely from the Chainguard registry:

```bash
rm -rf package-lock.json node_modules
docker compose run --rm --no-deps css "npm install"
```

If a previous container run left root-owned files in `node_modules`, fix ownership once on the host:

```bash
sudo chown -R "$(id -u)":"$(id -g)" node_modules
```

Or delete `node_modules` on the host and reinstall.

### Persist credentials for Compose

Optional: store all four values in a local `.env` file:

```bash
cat > .env <<EOF
DOCKER_UID=$(id -u)
DOCKER_GID=$(id -g)
CHAINGUARD_PYTHON_IDENTITY_ID=your-python-identity-id
CHAINGUARD_PYTHON_TOKEN=your-python-token
CHAINGUARD_JAVASCRIPT_IDENTITY_ID=your-javascript-identity-id
CHAINGUARD_JAVASCRIPT_TOKEN=your-javascript-token
EOF
```

`DOCKER_UID` and `DOCKER_GID` map the container user to your host user so bind-mounted files (`.npmrc`, `node_modules`, etc.) remain writable.

If any value is empty, run the matching `eval "$(chainctl auth pull-token ...)"` command in the same terminal where you run Docker Compose.

Note: only build/start commands require these variables. Other Docker Compose commands like `docker compose down` do not require them.

Security notes:

- Do not hardcode tokens in committed files
- Keep all `CHAINGUARD_*` credentials in environment variables or a local `.env` file only
- Re-run the `chainctl auth pull-token` commands when token values expire

## Run the app (containerized)

```bash
docker compose up --build
```

The app is available at [http://localhost:8000](http://localhost:8000).

Compose starts two services: the Flask app and a Tailwind CSS watcher that rebuilds `static/styles.css` when templates change.

## Stop the app

```bash
docker compose down
```

To clear tokens from your current shell session:

```bash
unset CHAINGUARD_PYTHON_IDENTITY_ID
unset CHAINGUARD_PYTHON_TOKEN
unset CHAINGUARD_JAVASCRIPT_IDENTITY_ID
unset CHAINGUARD_JAVASCRIPT_TOKEN
```

## Test with provided samples

Upload one of:

- `samples/python.spdx`
- `samples/static.spdx`

Then try the client-side search boxes on the report page:

- **Dependencies** — filter by from/to package, relationship type, or SPDX ID (e.g. `glibc`, `CONTAINS`, `SPDXRef-Package-apk`)
- **Packages** — filter by name, version, SPDX ID, or supplier

## Tests

The suite lives in `tests/` and uses `pytest`. Per the container-only policy,
run it inside a container rather than on the host:

```bash
docker run --rm -v "$PWD":/app -w /app python:3.12-slim \
  sh -c "pip install -r requirements-dev.txt && python -m pytest"
```

What is covered:

- `tests/test_parser.py` - unit tests for SPDX parsing, package labelling, and
  dependency filtering in `sbomviz/parser.py`
- `tests/test_app.py` - route/integration tests for the Flask app (upload
  validation, redirects, report rendering, and 404 handling)

CI runs the same suite on every push and pull request via
`.github/workflows/tests.yml` (Python 3.11, 3.12, and 3.13).

## Project layout

- `app.py` - Flask app with upload and report routes
- `sbomviz/parser.py` - SPDX parsing and dependency filtering logic
- `templates/base.html` - shared layout (header, footer, logo)
- `templates/index.html` - upload page
- `templates/report.html` - SBOM report with summary cards and searchable tables
- `static/logo_sbomviz.png` - app logo
- `static/src/input.css` - Tailwind CSS source
- `static/styles.css` - compiled Tailwind output (generated)
- `package.json` - Tailwind build scripts (run inside containers only)
- `scripts/configure-npm-libraries.sh` - writes `.npmrc` for Chainguard JavaScript Libraries
- `docker-compose.yml` - Flask app and Tailwind CSS watcher services
- `Dockerfile` - multi-stage Chainguard image (CSS build, Python deps, distroless runtime)
- `samples/` - test SBOM files
- `tests/` - pytest suite for the parser and Flask routes
- `requirements-dev.txt` - test dependencies (Flask + pytest)
- `pyproject.toml` - pytest configuration
- `.github/workflows/tests.yml` - CI workflow that runs the test suite
- `AGENTS.md` - agent execution rules, including container-only policy
