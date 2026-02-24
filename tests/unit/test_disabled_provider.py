"""Tests for DisabledWorkspaceProvider."""

import pytest

from soliplex_workspace.exceptions import WorkspaceDisabledError
from soliplex_workspace.providers.disabled import DisabledWorkspaceProvider


@pytest.fixture
def provider():
    return DisabledWorkspaceProvider()


class TestAllMethodsRaise:
    async def test_create_workspace(self, provider):
        with pytest.raises(WorkspaceDisabledError):
            await provider.create_workspace("room-1", "Test")

    async def test_delete_workspace(self, provider):
        with pytest.raises(WorkspaceDisabledError):
            await provider.delete_workspace("room-1")

    async def test_get_workspace(self, provider):
        with pytest.raises(WorkspaceDisabledError):
            await provider.get_workspace("room-1")

    async def test_list_files(self, provider):
        with pytest.raises(WorkspaceDisabledError):
            await provider.list_files("room-1")

    async def test_upload_file(self, provider):
        with pytest.raises(WorkspaceDisabledError):
            await provider.upload_file("room-1", "/doc.pdf", b"content")

    async def test_download_file(self, provider):
        with pytest.raises(WorkspaceDisabledError):
            await provider.download_file("room-1", "/doc.pdf")

    async def test_delete_file(self, provider):
        with pytest.raises(WorkspaceDisabledError):
            await provider.delete_file("room-1", "/doc.pdf")

    async def test_create_folder(self, provider):
        with pytest.raises(WorkspaceDisabledError):
            await provider.create_folder("room-1", "/notes")

    async def test_move(self, provider):
        with pytest.raises(WorkspaceDisabledError):
            await provider.move("room-1", "/a.txt", "/b.txt")

    async def test_get_web_ui_url(self, provider):
        with pytest.raises(WorkspaceDisabledError):
            await provider.get_web_ui_url("room-1")

    async def test_get_webdav_url(self, provider):
        with pytest.raises(WorkspaceDisabledError):
            await provider.get_webdav_url("room-1")
