"""Tests for data models."""

import datetime

import pytest

from soliplex_workspace.models import FileInfo
from soliplex_workspace.models import WorkspaceInfo


class TestWorkspaceInfo:
    def test_required_fields(self):
        info = WorkspaceInfo(room_id="r1", name="Test")
        assert info.room_id == "r1"
        assert info.name == "Test"

    def test_defaults(self):
        info = WorkspaceInfo(room_id="r1", name="Test")
        assert info.quota_bytes is None
        assert info.used_bytes == 0
        assert info.web_ui_url is None
        assert info.webdav_url is None
        assert isinstance(info.created_at, datetime.datetime)

    def test_with_quota(self):
        info = WorkspaceInfo(room_id="r1", name="Test", quota_bytes=1024)
        assert info.quota_bytes == 1024

    def test_frozen(self):
        info = WorkspaceInfo(room_id="r1", name="Test")
        with pytest.raises(AttributeError):
            info.name = "Changed"  # type: ignore[misc]


class TestFileInfo:
    def test_required_fields(self):
        info = FileInfo(name="doc.pdf", path="/doc.pdf")
        assert info.name == "doc.pdf"
        assert info.path == "/doc.pdf"

    def test_defaults(self):
        info = FileInfo(name="doc.pdf", path="/doc.pdf")
        assert info.size_bytes == 0
        assert info.content_type == "application/octet-stream"
        assert info.is_directory is False
        assert isinstance(info.modified_at, datetime.datetime)
        assert info.etag is None

    def test_directory(self):
        info = FileInfo(name="notes", path="/notes", is_directory=True)
        assert info.is_directory is True

    def test_frozen(self):
        info = FileInfo(name="doc.pdf", path="/doc.pdf")
        with pytest.raises(AttributeError):
            info.name = "other.pdf"  # type: ignore[misc]
