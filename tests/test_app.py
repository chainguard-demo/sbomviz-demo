"""Route and integration tests for the Flask app."""

from __future__ import annotations

import io

import app as app_module


def _upload(client, content: bytes, filename: str = "sbom.json"):
    data = {"sbom_file": (io.BytesIO(content), filename)}
    return client.post(
        "/upload",
        data=data,
        content_type="multipart/form-data",
    )


class TestIndex:
    def test_get_index_ok(self, client):
        response = client.get("/")
        assert response.status_code == 200
        assert b"SPDX SBOM visualizer" in response.data


class TestUpload:
    def test_upload_without_file_shows_error(self, client):
        response = client.post(
            "/upload",
            data={},
            content_type="multipart/form-data",
        )
        assert response.status_code == 200
        assert b"Please choose an SPDX SBOM JSON file" in response.data

    def test_upload_empty_filename_shows_error(self, client):
        response = _upload(client, b"{}", filename="")
        assert response.status_code == 200
        assert b"Please choose an SPDX SBOM JSON file" in response.data

    def test_upload_invalid_json_shows_error(self, client):
        response = _upload(client, b"not valid json")
        assert response.status_code == 200
        assert b"Could not parse file as SPDX JSON" in response.data

    def test_upload_valid_file_redirects_to_report(self, client, sample_spdx_json):
        response = _upload(client, sample_spdx_json.encode("utf-8"))
        assert response.status_code == 302
        assert "/report/" in response.headers["Location"]
        assert len(app_module._REPORT_STORE) == 1

    def test_upload_then_follow_redirect_renders_report(
        self, client, sample_spdx_json
    ):
        response = _upload(
            client, sample_spdx_json.encode("utf-8")
        )
        report = client.get(response.headers["Location"])
        assert report.status_code == 200
        assert b"SBOM report" in report.data
        assert b"test-sbom" in report.data


class TestReport:
    def test_unknown_report_id_returns_404(self, client):
        assert client.get("/report/does-not-exist").status_code == 404

    def test_known_report_renders(self, client, sample_spdx_json):
        location = _upload(
            client, sample_spdx_json.encode("utf-8")
        ).headers["Location"]
        response = client.get(location)
        assert response.status_code == 200
        assert b"glibc" in response.data

    def test_report_accepts_query_param(self, client, sample_spdx_json):
        location = _upload(
            client, sample_spdx_json.encode("utf-8")
        ).headers["Location"]
        response = client.get(location, query_string={"q": "glibc"})
        assert response.status_code == 200
        # The query value is echoed into the search input.
        assert b'value="glibc"' in response.data


class TestTemplateGlobals:
    def test_current_year_is_registered(self):
        current_year = app_module.current_year()
        assert isinstance(current_year, int)
        assert current_year >= 2026
