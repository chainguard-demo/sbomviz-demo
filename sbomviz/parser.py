"""Utilities for parsing SPDX JSON SBOMs into report-friendly structures."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass
class ParsedSbom:
    document_name: str
    spdx_version: str
    created: str
    creators: list[str]
    packages: list[dict[str, Any]]
    dependencies: list[dict[str, str]]


def _index_packages(packages: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {pkg.get("SPDXID", ""): pkg for pkg in packages if pkg.get("SPDXID")}


def _package_label(pkg: dict[str, Any] | None, fallback_id: str) -> str:
    if not pkg:
        return fallback_id
    name = pkg.get("name", "unknown")
    version = pkg.get("versionInfo")
    if version:
        return f"{name}@{version}"
    return str(name)


def parse_spdx_json(raw_content: str) -> ParsedSbom:
    data = json.loads(raw_content)
    packages = data.get("packages", [])
    relationships = data.get("relationships", [])
    package_index = _index_packages(packages)

    dependencies: list[dict[str, str]] = []
    for rel in relationships:
        from_id = rel.get("spdxElementId", "")
        to_id = rel.get("relatedSpdxElement", "")
        rel_type = rel.get("relationshipType", "UNKNOWN")
        from_pkg = package_index.get(from_id)
        to_pkg = package_index.get(to_id)
        dependencies.append(
            {
                "from_id": from_id,
                "from_name": _package_label(from_pkg, from_id),
                "to_id": to_id,
                "to_name": _package_label(to_pkg, to_id),
                "relationship_type": rel_type,
                "search_blob": " ".join(
                    [
                        from_id,
                        to_id,
                        rel_type,
                        _package_label(from_pkg, from_id),
                        _package_label(to_pkg, to_id),
                    ]
                ).lower(),
            }
        )

    creators = data.get("creationInfo", {}).get("creators", [])
    return ParsedSbom(
        document_name=data.get("name", "Unnamed SPDX document"),
        spdx_version=data.get("spdxVersion", "Unknown"),
        created=data.get("creationInfo", {}).get("created", "Unknown"),
        creators=[str(creator) for creator in creators],
        packages=packages,
        dependencies=dependencies,
    )


def filter_dependencies(
    dependencies: list[dict[str, str]], query: str
) -> list[dict[str, str]]:
    trimmed = query.strip().lower()
    if not trimmed:
        return dependencies
    return [dep for dep in dependencies if trimmed in dep["search_blob"]]
