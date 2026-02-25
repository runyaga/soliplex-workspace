"""API integration tests using TestClient + MockWorkspaceProvider."""

from __future__ import annotations

import io

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from soliplex_workspace.api.integration import mount_workspace_api
from soliplex_workspace.providers.disabled import DisabledWorkspaceProvider
from soliplex_workspace.providers.mock import MockWorkspaceProvider


def _create_app(
    provider: MockWorkspaceProvider | DisabledWorkspaceProvider,
) -> FastAPI:
    app = FastAPI()
    mount_workspace_api(app, provider)
    return app


@pytest.fixture
def mock_app():
    provider = MockWorkspaceProvider()
    app = _create_app(provider)
    return app, provider


@pytest.fixture
def client(mock_app):
    app, _ = mock_app
    return TestClient(app)


@pytest.fixture
def disabled_client():
    app = _create_app(DisabledWorkspaceProvider())
    return TestClient(app)


def _create_workspace(client: TestClient, room_id: str = "room-1"):
    return client.post(
        f"/v1/rooms/{room_id}/workspace",
        json={"name": "Test Room"},
    )


def _upload_file(
    client: TestClient,
    room_id: str = "room-1",
    path: str = "/doc.pdf",
    content: bytes = b"pdf-content",
    filename: str = "doc.pdf",
):
    return client.post(
        f"/v1/rooms/{room_id}/workspace/files/upload",
        params={"path": path},
        files={"file": (filename, io.BytesIO(content), "application/pdf")},
    )


class TestCreateWorkspace:
    def test_create_returns_201(self, client):
        resp = _create_workspace(client)
        assert resp.status_code == 201
        data = resp.json()
        assert data["room_id"] == "room-1"
        assert data["name"] == "Test Room"

    def test_create_duplicate_is_idempotent(self, client):
        _create_workspace(client)
        resp = _create_workspace(client)
        assert resp.status_code == 201
        assert resp.json()["room_id"] == "room-1"


class TestGetWorkspace:
    def test_get_workspace_returns_200(self, client):
        _create_workspace(client)
        resp = client.get("/v1/rooms/room-1/workspace")
        assert resp.status_code == 200
        assert resp.json()["room_id"] == "room-1"

    def test_get_nonexistent_returns_404(self, client):
        resp = client.get("/v1/rooms/nope/workspace")
        assert resp.status_code == 404


class TestDeleteWorkspace:
    def test_delete_returns_204(self, client):
        _create_workspace(client)
        resp = client.delete("/v1/rooms/room-1/workspace")
        assert resp.status_code == 204


class TestListFiles:
    def test_list_empty_returns_200(self, client):
        _create_workspace(client)
        resp = client.get("/v1/rooms/room-1/workspace/files")
        assert resp.status_code == 200
        assert resp.json()["files"] == []


class TestUploadFile:
    def test_upload_returns_201(self, client):
        _create_workspace(client)
        resp = _upload_file(client)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "doc.pdf"
        assert data["size_bytes"] == 11

    def test_upload_missing_content_returns_422(self, client):
        _create_workspace(client)
        resp = client.post(
            "/v1/rooms/room-1/workspace/files/upload",
            params={"path": "/doc.pdf"},
        )
        assert resp.status_code == 422


class TestDownloadFile:
    def test_download_returns_bytes(self, client):
        _create_workspace(client)
        _upload_file(client)
        resp = client.get(
            "/v1/rooms/room-1/workspace/files/download",
            params={"path": "/doc.pdf"},
        )
        assert resp.status_code == 200
        assert resp.content == b"pdf-content"

    def test_download_nonexistent_returns_404(self, client):
        _create_workspace(client)
        resp = client.get(
            "/v1/rooms/room-1/workspace/files/download",
            params={"path": "/nope.txt"},
        )
        assert resp.status_code == 404


class TestDeleteFile:
    def test_delete_file_returns_204(self, client):
        _create_workspace(client)
        _upload_file(client)
        resp = client.delete(
            "/v1/rooms/room-1/workspace/files",
            params={"path": "/doc.pdf"},
        )
        assert resp.status_code == 204

    def test_delete_nonexistent_returns_404(self, client):
        _create_workspace(client)
        resp = client.delete(
            "/v1/rooms/room-1/workspace/files",
            params={"path": "/nope.txt"},
        )
        assert resp.status_code == 404


class TestCreateFolder:
    def test_create_folder_returns_201(self, client):
        _create_workspace(client)
        resp = client.post(
            "/v1/rooms/room-1/workspace/folders",
            json={"path": "/notes"},
        )
        assert resp.status_code == 201
        assert resp.json()["is_directory"] is True


class TestMoveFile:
    def test_move_returns_200(self, client):
        _create_workspace(client)
        _upload_file(client)
        resp = client.post(
            "/v1/rooms/room-1/workspace/files/move",
            json={"src": "/doc.pdf", "dst": "/renamed.pdf"},
        )
        assert resp.status_code == 200
        assert resp.json()["path"] == "/renamed.pdf"

    def test_move_with_traversal_returns_400(self, client):
        _create_workspace(client)
        resp = client.post(
            "/v1/rooms/room-1/workspace/files/move",
            json={"src": "/doc.pdf", "dst": "/../../../etc/passwd"},
        )
        assert resp.status_code == 400


class TestPathTraversal:
    def test_path_traversal_in_query_returns_400(self, client):
        _create_workspace(client)
        resp = client.get(
            "/v1/rooms/room-1/workspace/files",
            params={"path": "/../../../etc/passwd"},
        )
        assert resp.status_code == 400


class TestDisabledProvider:
    def test_workspace_disabled_returns_503(self, disabled_client):
        resp = disabled_client.post(
            "/v1/rooms/room-1/workspace",
            json={"name": "Test"},
        )
        assert resp.status_code == 503


class TestGetFileInfo:
    def test_get_file_info_returns_200(self, client):
        _create_workspace(client)
        _upload_file(client)
        resp = client.get(
            "/v1/rooms/room-1/workspace/files/info",
            params={"path": "/doc.pdf"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "doc.pdf"


class TestListFilesWithPath:
    def test_list_files_with_path_param(self, client):
        _create_workspace(client)
        client.post(
            "/v1/rooms/room-1/workspace/folders",
            json={"path": "/sub"},
        )
        _upload_file(
            client,
            path="/sub/file.txt",
            content=b"data",
            filename="file.txt",
        )
        resp = client.get(
            "/v1/rooms/room-1/workspace/files",
            params={"path": "/sub"},
        )
        assert resp.status_code == 200
        files = resp.json()["files"]
        assert len(files) == 1
        assert files[0]["name"] == "file.txt"
