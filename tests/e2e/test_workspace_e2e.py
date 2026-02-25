"""E2E tests: full stack through FastAPI -> DufsWorkspaceProvider -> dufs."""

from __future__ import annotations

import io
import uuid

import pytest
from fastapi.testclient import TestClient

from .conftest import requires_dufs

pytestmark = [requires_dufs, pytest.mark.dufs, pytest.mark.e2e]


def _room_id() -> str:
    return f"e2e-{uuid.uuid4().hex[:8]}"


def _create_workspace(client: TestClient, room_id: str):
    return client.post(
        f"/v1/rooms/{room_id}/workspace",
        json={"name": "E2E Room"},
    )


def _delete_workspace(client: TestClient, room_id: str):
    return client.delete(f"/v1/rooms/{room_id}/workspace")


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


class TestFullLifecycle:
    def test_full_lifecycle(self, e2e_client):
        rid = _room_id()
        try:
            resp = _create_workspace(e2e_client, rid)
            assert resp.status_code == 201

            resp = _upload(e2e_client, rid, "/hello.txt", b"hello world")
            assert resp.status_code == 201

            resp = e2e_client.get(f"/v1/rooms/{rid}/workspace/files")
            assert resp.status_code == 200
            names = [f["name"] for f in resp.json()["files"]]
            assert "hello.txt" in names

            resp = e2e_client.get(
                f"/v1/rooms/{rid}/workspace/files/download",
                params={"path": "/hello.txt"},
            )
            assert resp.status_code == 200
            assert resp.content == b"hello world"

            resp = e2e_client.delete(
                f"/v1/rooms/{rid}/workspace/files",
                params={"path": "/hello.txt"},
            )
            assert resp.status_code == 204

            _delete_workspace(e2e_client, rid)
        finally:
            _delete_workspace(e2e_client, rid)


class TestUploadDownloadRoundtrip:
    def test_pdf_roundtrip(self, e2e_client):
        rid = _room_id()
        pdf_bytes = b"%PDF-1.4 fake pdf content here"
        try:
            _create_workspace(e2e_client, rid)
            _upload(e2e_client, rid, "/test.pdf", pdf_bytes, "test.pdf")
            resp = e2e_client.get(
                f"/v1/rooms/{rid}/workspace/files/download",
                params={"path": "/test.pdf"},
            )
            assert resp.content == pdf_bytes
        finally:
            _delete_workspace(e2e_client, rid)

    def test_image_roundtrip(self, e2e_client):
        rid = _room_id()
        png_header = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        try:
            _create_workspace(e2e_client, rid)
            _upload(e2e_client, rid, "/img.png", png_header, "img.png")
            resp = e2e_client.get(
                f"/v1/rooms/{rid}/workspace/files/download",
                params={"path": "/img.png"},
            )
            assert resp.content == png_header
        finally:
            _delete_workspace(e2e_client, rid)


class TestFolderOperations:
    def test_folder_ops(self, e2e_client):
        rid = _room_id()
        try:
            _create_workspace(e2e_client, rid)

            e2e_client.post(
                f"/v1/rooms/{rid}/workspace/folders",
                json={"path": "/docs"},
            )

            _upload(e2e_client, rid, "/docs/readme.txt", b"readme")

            resp = e2e_client.get(
                f"/v1/rooms/{rid}/workspace/files",
                params={"path": "/docs"},
            )
            names = [f["name"] for f in resp.json()["files"]]
            assert "readme.txt" in names

            e2e_client.post(
                f"/v1/rooms/{rid}/workspace/files/move",
                json={"src": "/docs/readme.txt", "dst": "/readme.txt"},
            )

            resp = e2e_client.get(
                f"/v1/rooms/{rid}/workspace/files/download",
                params={"path": "/readme.txt"},
            )
            assert resp.content == b"readme"
        finally:
            _delete_workspace(e2e_client, rid)


class TestMoveAcrossFolders:
    def test_move_across_folders(self, e2e_client):
        rid = _room_id()
        try:
            _create_workspace(e2e_client, rid)
            e2e_client.post(
                f"/v1/rooms/{rid}/workspace/folders",
                json={"path": "/a"},
            )
            e2e_client.post(
                f"/v1/rooms/{rid}/workspace/folders",
                json={"path": "/b"},
            )
            _upload(e2e_client, rid, "/a/file.txt", b"data")
            e2e_client.post(
                f"/v1/rooms/{rid}/workspace/files/move",
                json={"src": "/a/file.txt", "dst": "/b/file.txt"},
            )
            resp = e2e_client.get(
                f"/v1/rooms/{rid}/workspace/files/download",
                params={"path": "/b/file.txt"},
            )
            assert resp.content == b"data"
        finally:
            _delete_workspace(e2e_client, rid)


class TestOverwriteSemantics:
    def test_overwrite(self, e2e_client):
        rid = _room_id()
        try:
            _create_workspace(e2e_client, rid)
            _upload(e2e_client, rid, "/f.txt", b"v1")
            _upload(e2e_client, rid, "/f.txt", b"v2")
            resp = e2e_client.get(
                f"/v1/rooms/{rid}/workspace/files/download",
                params={"path": "/f.txt"},
            )
            assert resp.content == b"v2"
        finally:
            _delete_workspace(e2e_client, rid)


class TestCrossRoomIsolation:
    def test_isolation(self, e2e_client):
        rid_a = _room_id()
        rid_b = _room_id()
        try:
            _create_workspace(e2e_client, rid_a)
            _create_workspace(e2e_client, rid_b)
            _upload(e2e_client, rid_a, "/secret.txt", b"secret")
            resp = e2e_client.get(f"/v1/rooms/{rid_b}/workspace/files")
            names = [f["name"] for f in resp.json()["files"]]
            assert "secret.txt" not in names
        finally:
            _delete_workspace(e2e_client, rid_a)
            _delete_workspace(e2e_client, rid_b)


class TestErrorResponsesAreJson:
    def test_404_is_json(self, e2e_client):
        rid = _room_id()
        try:
            _create_workspace(e2e_client, rid)
            resp = e2e_client.get(
                f"/v1/rooms/{rid}/workspace/files/download",
                params={"path": "/nonexistent.txt"},
            )
            assert resp.status_code == 404
            assert "detail" in resp.json()
        finally:
            _delete_workspace(e2e_client, rid)

    def test_400_is_json(self, e2e_client):
        rid = _room_id()
        try:
            _create_workspace(e2e_client, rid)
            resp = e2e_client.get(
                f"/v1/rooms/{rid}/workspace/files",
                params={"path": "/../../../etc/passwd"},
            )
            assert resp.status_code == 400
            assert "detail" in resp.json()
        finally:
            _delete_workspace(e2e_client, rid)


class TestPathTraversalBlocked:
    def test_traversal_blocked(self, e2e_client):
        rid = _room_id()
        try:
            _create_workspace(e2e_client, rid)
            resp = _upload(e2e_client, rid, "/../../../etc/passwd", b"hack")
            assert resp.status_code == 400
        finally:
            _delete_workspace(e2e_client, rid)


class TestConcurrentUploads:
    def test_concurrent_uploads(self, e2e_client):
        rid = _room_id()
        try:
            _create_workspace(e2e_client, rid)
            for i in range(5):
                resp = _upload(
                    e2e_client,
                    rid,
                    f"/file-{i}.txt",
                    f"content-{i}".encode(),
                )
                assert resp.status_code == 201
            resp = e2e_client.get(f"/v1/rooms/{rid}/workspace/files")
            assert len(resp.json()["files"]) == 5
        finally:
            _delete_workspace(e2e_client, rid)


class TestDeleteWorkspaceCleansUp:
    def test_cleanup(self, e2e_client):
        rid = _room_id()
        _create_workspace(e2e_client, rid)
        _upload(e2e_client, rid, "/file.txt", b"data")
        _delete_workspace(e2e_client, rid)
        resp = e2e_client.get(f"/v1/rooms/{rid}/workspace")
        assert resp.status_code == 404


class TestLargeFile:
    def test_large_file(self, e2e_client):
        rid = _room_id()
        content = b"x" * (5 * 1024 * 1024)  # 5MB
        try:
            _create_workspace(e2e_client, rid)
            _upload(e2e_client, rid, "/large.bin", content)
            resp = e2e_client.get(
                f"/v1/rooms/{rid}/workspace/files/download",
                params={"path": "/large.bin"},
            )
            assert len(resp.content) == len(content)
        finally:
            _delete_workspace(e2e_client, rid)


class TestSpecialFilenames:
    def test_special_filenames(self, e2e_client):
        rid = _room_id()
        try:
            _create_workspace(e2e_client, rid)
            _upload(
                e2e_client,
                rid,
                "/my file (1).txt",
                b"data",
            )
            resp = e2e_client.get(
                f"/v1/rooms/{rid}/workspace/files/download",
                params={"path": "/my file (1).txt"},
            )
            assert resp.content == b"data"
        finally:
            _delete_workspace(e2e_client, rid)
