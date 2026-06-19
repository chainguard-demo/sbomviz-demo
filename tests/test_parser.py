"""Unit tests for sbomviz.parser."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sbomviz.parser import (
    ParsedSbom,
    _index_packages,
    _package_label,
    filter_dependencies,
    parse_spdx_json,
)

from .conftest import SAMPLES_DIR


class TestIndexPackages:
    def test_indexes_by_spdxid(self):
        packages = [
            {"SPDXID": "SPDXRef-A", "name": "a"},
            {"SPDXID": "SPDXRef-B", "name": "b"},
        ]
        index = _index_packages(packages)
        assert set(index) == {"SPDXRef-A", "SPDXRef-B"}
        assert index["SPDXRef-A"]["name"] == "a"

    def test_skips_packages_without_spdxid(self):
        packages = [
            {"SPDXID": "SPDXRef-A", "name": "a"},
            {"name": "no-id"},
            {"SPDXID": "", "name": "empty-id"},
        ]
        index = _index_packages(packages)
        assert set(index) == {"SPDXRef-A"}

    def test_empty_list(self):
        assert _index_packages([]) == {}


class TestPackageLabel:
    def test_falls_back_to_id_when_pkg_missing(self):
        assert _package_label(None, "SPDXRef-X") == "SPDXRef-X"

    def test_name_with_version(self):
        pkg = {"name": "glibc", "versionInfo": "2.39"}
        assert _package_label(pkg, "SPDXRef-X") == "glibc@2.39"

    def test_name_without_version(self):
        pkg = {"name": "glibc"}
        assert _package_label(pkg, "SPDXRef-X") == "glibc"

    def test_empty_dict_is_falsy_and_uses_fallback(self):
        # An empty dict is falsy, so the fallback id is returned.
        assert _package_label({}, "SPDXRef-X") == "SPDXRef-X"

    def test_missing_name_uses_unknown(self):
        assert _package_label({"SPDXID": "SPDXRef-X"}, "SPDXRef-X") == "unknown"

    def test_missing_name_with_version(self):
        pkg = {"SPDXID": "SPDXRef-X", "versionInfo": "1.0"}
        assert _package_label(pkg, "SPDXRef-X") == "unknown@1.0"


class TestParseSpdxJson:
    def test_returns_parsed_sbom(self, sample_spdx_json: str):
        parsed = parse_spdx_json(sample_spdx_json)
        assert isinstance(parsed, ParsedSbom)

    def test_document_metadata(self, sample_spdx_json: str):
        parsed = parse_spdx_json(sample_spdx_json)
        assert parsed.document_name == "test-sbom"
        assert parsed.spdx_version == "SPDX-2.3"
        assert parsed.created == "2026-01-01T00:00:00Z"
        assert parsed.creators == [
            "Tool: sbomviz-tests",
            "Organization: Example",
        ]

    def test_packages_passed_through(self, sample_spdx_json: str):
        parsed = parse_spdx_json(sample_spdx_json)
        assert len(parsed.packages) == 3

    def test_dependencies_built_from_relationships(self, sample_spdx_json: str):
        parsed = parse_spdx_json(sample_spdx_json)
        assert len(parsed.dependencies) == 3
        first = parsed.dependencies[0]
        assert first["from_id"] == "SPDXRef-Package-app"
        assert first["from_name"] == "app@1.0.0"
        assert first["to_id"] == "SPDXRef-Package-glibc"
        assert first["to_name"] == "glibc@2.39"
        assert first["relationship_type"] == "DEPENDS_ON"

    def test_unknown_related_element_uses_id_as_label(self, sample_spdx_json: str):
        parsed = parse_spdx_json(sample_spdx_json)
        missing = parsed.dependencies[2]
        assert missing["to_id"] == "SPDXRef-Package-missing"
        assert missing["to_name"] == "SPDXRef-Package-missing"

    def test_search_blob_is_lowercased(self, sample_spdx_json: str):
        parsed = parse_spdx_json(sample_spdx_json)
        blob = parsed.dependencies[0]["search_blob"]
        assert blob == blob.lower()
        assert "depends_on" in blob
        assert "glibc@2.39" in blob

    def test_defaults_for_missing_fields(self):
        parsed = parse_spdx_json("{}")
        assert parsed.document_name == "Unnamed SPDX document"
        assert parsed.spdx_version == "Unknown"
        assert parsed.created == "Unknown"
        assert parsed.creators == []
        assert parsed.packages == []
        assert parsed.dependencies == []

    def test_relationship_type_defaults_to_unknown(self):
        raw = json.dumps(
            {
                "relationships": [
                    {
                        "spdxElementId": "SPDXRef-A",
                        "relatedSpdxElement": "SPDXRef-B",
                    }
                ]
            }
        )
        parsed = parse_spdx_json(raw)
        assert parsed.dependencies[0]["relationship_type"] == "UNKNOWN"

    def test_creators_coerced_to_strings(self):
        raw = json.dumps({"creationInfo": {"creators": [123, True]}})
        parsed = parse_spdx_json(raw)
        assert parsed.creators == ["123", "True"]

    def test_invalid_json_raises(self):
        with pytest.raises(json.JSONDecodeError):
            parse_spdx_json("not json")


class TestFilterDependencies:
    @pytest.fixture
    def dependencies(self, sample_spdx_json: str):
        return parse_spdx_json(sample_spdx_json).dependencies

    def test_empty_query_returns_all(self, dependencies):
        assert filter_dependencies(dependencies, "") == dependencies

    def test_whitespace_query_returns_all(self, dependencies):
        assert filter_dependencies(dependencies, "   ") == dependencies

    def test_matches_by_substring(self, dependencies):
        result = filter_dependencies(dependencies, "glibc")
        assert len(result) == 1
        assert result[0]["to_name"] == "glibc@2.39"

    def test_is_case_insensitive(self, dependencies):
        assert filter_dependencies(dependencies, "GLIBC") == filter_dependencies(
            dependencies, "glibc"
        )

    def test_matches_relationship_type(self, dependencies):
        result = filter_dependencies(dependencies, "contains")
        assert len(result) == 1
        assert result[0]["relationship_type"] == "CONTAINS"

    def test_no_match_returns_empty(self, dependencies):
        assert filter_dependencies(dependencies, "does-not-exist") == []


class TestRealSampleFiles:
    @pytest.mark.parametrize("sample_name", ["python.spdx", "static.spdx"])
    def test_parses_bundled_samples(self, sample_name: str):
        sample_path = SAMPLES_DIR / sample_name
        if not sample_path.exists():
            pytest.skip(f"sample {sample_name} not present")
        parsed = parse_spdx_json(sample_path.read_text(encoding="utf-8"))
        assert isinstance(parsed, ParsedSbom)
        assert len(parsed.packages) > 0
        # Every relationship should be represented as a dependency row.
        for dep in parsed.dependencies:
            assert "search_blob" in dep
            assert dep["relationship_type"]
