"""Shared fixtures and sample data for the sbomviz test suite."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import app as app_module

REPO_ROOT = Path(__file__).resolve().parent.parent
SAMPLES_DIR = REPO_ROOT / "samples"

# A small, self-contained SPDX document used across parser and route tests.
SAMPLE_SPDX_DICT = {
    "SPDXID": "SPDXRef-DOCUMENT",
    "spdxVersion": "SPDX-2.3",
    "name": "test-sbom",
    "creationInfo": {
        "created": "2026-01-01T00:00:00Z",
        "creators": ["Tool: sbomviz-tests", "Organization: Example"],
    },
    "packages": [
        {
            "SPDXID": "SPDXRef-Package-app",
            "name": "app",
            "versionInfo": "1.0.0",
            "supplier": "Organization: Example",
        },
        {
            "SPDXID": "SPDXRef-Package-glibc",
            "name": "glibc",
            "versionInfo": "2.39",
            "supplier": "Organization: Wolfi",
        },
        {
            # No versionInfo on purpose to exercise the label fallback.
            "SPDXID": "SPDXRef-Package-noversion",
            "name": "noversion",
        },
    ],
    "relationships": [
        {
            "spdxElementId": "SPDXRef-Package-app",
            "relatedSpdxElement": "SPDXRef-Package-glibc",
            "relationshipType": "DEPENDS_ON",
        },
        {
            "spdxElementId": "SPDXRef-Package-app",
            "relatedSpdxElement": "SPDXRef-Package-noversion",
            "relationshipType": "CONTAINS",
        },
        {
            # References an element that is not in the package index.
            "spdxElementId": "SPDXRef-Package-app",
            "relatedSpdxElement": "SPDXRef-Package-missing",
            "relationshipType": "DEPENDS_ON",
        },
    ],
}


@pytest.fixture
def sample_spdx_dict() -> dict:
    """A fresh copy of the sample SPDX document as a Python dict."""
    return json.loads(json.dumps(SAMPLE_SPDX_DICT))


@pytest.fixture
def sample_spdx_json(sample_spdx_dict: dict) -> str:
    """The sample SPDX document serialized to JSON text."""
    return json.dumps(sample_spdx_dict)


@pytest.fixture
def client():
    """A Flask test client with an isolated, empty report store."""
    app_module.app.config.update(TESTING=True)
    app_module._REPORT_STORE.clear()
    with app_module.app.test_client() as test_client:
        yield test_client
    app_module._REPORT_STORE.clear()
