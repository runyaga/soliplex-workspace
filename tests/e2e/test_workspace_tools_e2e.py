"""E2E: REST API full lifecycle + tool functions against dufs."""

from __future__ import annotations

import io
import uuid

import pytest
from fastapi.testclient import TestClient

from .conftest import requires_dufs

pytestmark = [requires_dufs, pytest.mark.dufs, pytest.mark.e2e]


def _room_id() -> str:
    return f"e2e-tools-{uuid.uuid4().hex[:8]}"


def _upload(
    client: TestClient,
    room_id: str,
    path: str,
    content: bytes,
    filename: str = "file.bin",
):
    return client.post(
        f"/v1/rooms/{room_id}/workspace/files/upload",
        params={"path": path},
        files={
            "file": (
                filename,
                io.BytesIO(content),
                "application/octet-stream",
            ),
        },
    )


class TestRestWorkspaceFullLifecycle:
    """Full CRUD lifecycle through the REST API."""

    def test_full_lifecycle(self, e2e_client: TestClient):
        rid = _room_id()
        try:
            # 1. Create workspace
            resp = e2e_client.post(
                f"/v1/rooms/{rid}/workspace",
                json={"name": "E2E Tools Room"},
            )
            assert resp.status_code == 201

            # 2. Create /research folder
            resp = e2e_client.post(
                f"/v1/rooms/{rid}/workspace/folders",
                json={"path": "/research"},
            )
            assert resp.status_code == 201

            # 3. Upload two markdown files
            resp = _upload(
                e2e_client,
                rid,
                "/research/paper1.md",
                b"# Paper 1\nIntro text",
                "paper1.md",
            )
            assert resp.status_code == 201

            resp = _upload(
                e2e_client,
                rid,
                "/research/paper2.md",
                b"# Paper 2\nMore text",
                "paper2.md",
            )
            assert resp.status_code == 201

            # 4. List root — expect 1 dir
            resp = e2e_client.get(f"/v1/rooms/{rid}/workspace/files")
            assert resp.status_code == 200
            files = resp.json()["files"]
            dirs = [f for f in files if f["is_directory"]]
            assert len(dirs) >= 1
            dir_names = [d["name"] for d in dirs]
            assert "research" in dir_names

            # 5. List /research — expect 2 files
            resp = e2e_client.get(
                f"/v1/rooms/{rid}/workspace/files",
                params={"path": "/research"},
            )
            assert resp.status_code == 200
            names = [f["name"] for f in resp.json()["files"]]
            assert "paper1.md" in names
            assert "paper2.md" in names

            # 6. Download paper1.md
            resp = e2e_client.get(
                f"/v1/rooms/{rid}/workspace/files/download",
                params={"path": "/research/paper1.md"},
            )
            assert resp.status_code == 200
            assert b"# Paper 1" in resp.content

            # 7. Get file info
            resp = e2e_client.get(
                f"/v1/rooms/{rid}/workspace/files/info",
                params={"path": "/research/paper1.md"},
            )
            assert resp.status_code == 200
            info = resp.json()
            assert info["name"] == "paper1.md"
            assert info["size_bytes"] > 0

            # 8. Move paper1 to renamed.md
            resp = e2e_client.post(
                f"/v1/rooms/{rid}/workspace/files/move",
                json={
                    "src": "/research/paper1.md",
                    "dst": "/research/renamed.md",
                },
            )
            assert resp.status_code == 200

            # 9. Delete renamed.md
            resp = e2e_client.delete(
                f"/v1/rooms/{rid}/workspace/files",
                params={"path": "/research/renamed.md"},
            )
            assert resp.status_code == 204

            # 10. Delete workspace
            resp = e2e_client.delete(f"/v1/rooms/{rid}/workspace")
            assert resp.status_code == 204
        finally:
            e2e_client.delete(f"/v1/rooms/{rid}/workspace")


class TestRestWorkspaceErrorHandling:
    """Error responses are correct HTTP status + JSON."""

    def test_get_nonexistent_workspace(self, e2e_client: TestClient):
        resp = e2e_client.get("/v1/rooms/nonexistent-room/workspace")
        assert resp.status_code == 404
        assert "detail" in resp.json()

    def test_path_traversal_blocked(self, e2e_client: TestClient):
        rid = _room_id()
        try:
            e2e_client.post(
                f"/v1/rooms/{rid}/workspace",
                json={"name": "Traversal Test"},
            )
            resp = _upload(
                e2e_client,
                rid,
                "/../../../etc/passwd",
                b"hack",
            )
            assert resp.status_code == 400
        finally:
            e2e_client.delete(f"/v1/rooms/{rid}/workspace")

    def test_download_nonexistent_file(self, e2e_client: TestClient):
        rid = _room_id()
        try:
            e2e_client.post(
                f"/v1/rooms/{rid}/workspace",
                json={"name": "404 Test"},
            )
            resp = e2e_client.get(
                f"/v1/rooms/{rid}/workspace/files/download",
                params={"path": "/no-such-file.txt"},
            )
            assert resp.status_code == 404
        finally:
            e2e_client.delete(f"/v1/rooms/{rid}/workspace")

    def test_delete_nonexistent_file(self, e2e_client: TestClient):
        rid = _room_id()
        try:
            e2e_client.post(
                f"/v1/rooms/{rid}/workspace",
                json={"name": "Delete 404 Test"},
            )
            resp = e2e_client.delete(
                f"/v1/rooms/{rid}/workspace/files",
                params={"path": "/ghost.txt"},
            )
            assert resp.status_code == 404
        finally:
            e2e_client.delete(f"/v1/rooms/{rid}/workspace")
