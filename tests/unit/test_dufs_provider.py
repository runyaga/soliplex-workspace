"""Tests for DufsWorkspaceProvider with mocked HTTP via respx."""

from __future__ import annotations

import httpx
import pytest
import respx

from soliplex_workspace.exceptions import DirectoryNotEmptyError
from soliplex_workspace.exceptions import InvalidPathError
from soliplex_workspace.exceptions import QuotaExceededError
from soliplex_workspace.exceptions import WorkspaceFileNotFoundError
from soliplex_workspace.exceptions import WorkspaceNotFoundError
from soliplex_workspace.providers.dufs import DufsWorkspaceProvider

BASE = "http://dufs.test:5000"

MULTISTATUS_DIR = """\
<?xml version="1.0" encoding="utf-8"?>
<multistatus xmlns="DAV:">
  <response>
    <href>/rooms/room-1/</href>
    <propstat>
      <prop>
        <resourcetype><collection/></resourcetype>
      </prop>
    </propstat>
  </response>
</multistatus>"""

MULTISTATUS_FILE = """\
<?xml version="1.0" encoding="utf-8"?>
<multistatus xmlns="DAV:">
  <response>
    <href>/rooms/room-1/doc.pdf</href>
    <propstat>
      <prop>
        <getcontentlength>1024</getcontentlength>
        <getcontenttype>application/pdf</getcontenttype>
        <getetag>"abc123"</getetag>
        <resourcetype/>
      </prop>
    </propstat>
  </response>
</multistatus>"""

MULTISTATUS_LISTING = """\
<?xml version="1.0" encoding="utf-8"?>
<multistatus xmlns="DAV:">
  <response>
    <href>/rooms/room-1/</href>
    <propstat>
      <prop>
        <resourcetype><collection/></resourcetype>
      </prop>
    </propstat>
  </response>
  <response>
    <href>/rooms/room-1/notes/</href>
    <propstat>
      <prop>
        <resourcetype><collection/></resourcetype>
      </prop>
    </propstat>
  </response>
  <response>
    <href>/rooms/room-1/doc.pdf</href>
    <propstat>
      <prop>
        <getcontentlength>512</getcontentlength>
        <getcontenttype>application/pdf</getcontenttype>
        <resourcetype/>
      </prop>
    </propstat>
  </response>
</multistatus>"""

MULTISTATUS_EMPTY = """\
<?xml version="1.0" encoding="utf-8"?>
<multistatus xmlns="DAV:">
  <response>
    <href>/rooms/room-1/</href>
    <propstat>
      <prop>
        <resourcetype><collection/></resourcetype>
      </prop>
    </propstat>
  </response>
</multistatus>"""


@pytest.fixture
def provider():
    """DufsWorkspaceProvider with mocked HTTP."""
    client = httpx.AsyncClient()
    return DufsWorkspaceProvider(BASE, client=client)


class TestCreateWorkspace:
    @respx.mock
    async def test_create_returns_workspace_info(self, provider):
        respx.route(method="PROPFIND", url=f"{BASE}/rooms/room-1/").mock(
            return_value=httpx.Response(404)
        )
        respx.route(method="MKCOL", url=f"{BASE}/rooms/room-1/").mock(
            return_value=httpx.Response(201)
        )
        info = await provider.create_workspace("room-1", "Test Room")
        assert info.room_id == "room-1"
        assert info.name == "Test Room"

    @respx.mock
    async def test_create_with_quota(self, provider):
        respx.route(method="PROPFIND", url=f"{BASE}/rooms/room-1/").mock(
            return_value=httpx.Response(404)
        )
        respx.route(method="MKCOL", url=f"{BASE}/rooms/room-1/").mock(
            return_value=httpx.Response(201)
        )
        info = await provider.create_workspace(
            "room-1", "Test", quota_bytes=1024
        )
        assert info.quota_bytes == 1024

    @respx.mock
    async def test_create_duplicate_is_idempotent(self, provider):
        respx.route(method="PROPFIND", url=f"{BASE}/rooms/room-1/").mock(
            return_value=httpx.Response(200, text=MULTISTATUS_DIR)
        )
        result = await provider.create_workspace("room-1", "Test")
        assert result.room_id == "room-1"


class TestDeleteWorkspace:
    @respx.mock
    async def test_delete_workspace(self, provider):
        respx.route(method="DELETE", url=f"{BASE}/rooms/room-1/").mock(
            return_value=httpx.Response(204)
        )
        await provider.delete_workspace("room-1")

    @respx.mock
    async def test_delete_nonexistent_is_noop(self, provider):
        respx.route(method="DELETE", url=f"{BASE}/rooms/room-1/").mock(
            return_value=httpx.Response(404)
        )
        await provider.delete_workspace("room-1")


class TestGetWorkspace:
    @respx.mock
    async def test_get_existing(self, provider):
        respx.route(method="PROPFIND", url=f"{BASE}/rooms/room-1/").mock(
            return_value=httpx.Response(207, text=MULTISTATUS_DIR)
        )
        info = await provider.get_workspace("room-1")
        assert info is not None
        assert info.room_id == "room-1"

    @respx.mock
    async def test_get_nonexistent(self, provider):
        respx.route(method="PROPFIND", url=f"{BASE}/rooms/room-1/").mock(
            return_value=httpx.Response(404)
        )
        result = await provider.get_workspace("room-1")
        assert result is None


class TestGetFileInfo:
    @respx.mock
    async def test_get_file_info(self, provider):
        respx.route(
            method="PROPFIND", url=f"{BASE}/rooms/room-1/doc.pdf"
        ).mock(return_value=httpx.Response(207, text=MULTISTATUS_FILE))
        info = await provider.get_file_info("room-1", "/doc.pdf")
        assert info.name == "doc.pdf"
        assert info.size_bytes == 1024
        assert info.content_type == "application/pdf"
        assert info.etag == "abc123"
        assert info.is_directory is False

    @respx.mock
    async def test_get_directory_info(self, provider):
        respx.route(method="PROPFIND", url=f"{BASE}/rooms/room-1/").mock(
            return_value=httpx.Response(207, text=MULTISTATUS_DIR)
        )
        info = await provider.get_file_info("room-1", "/")
        assert info.is_directory is True
        assert info.name == "/"

    @respx.mock
    async def test_get_nonexistent_raises(self, provider):
        respx.route(
            method="PROPFIND", url=f"{BASE}/rooms/room-1/nope.txt"
        ).mock(return_value=httpx.Response(404))
        with pytest.raises(WorkspaceFileNotFoundError):
            await provider.get_file_info("room-1", "/nope.txt")


class TestListFiles:
    @respx.mock
    async def test_list_root(self, provider):
        respx.route(method="PROPFIND", url=f"{BASE}/rooms/room-1/").mock(
            return_value=httpx.Response(207, text=MULTISTATUS_LISTING)
        )
        files = await provider.list_files("room-1")
        assert len(files) == 2
        assert files[0].name == "notes"
        assert files[0].is_directory is True
        assert files[1].name == "doc.pdf"
        assert files[1].size_bytes == 512

    @respx.mock
    async def test_list_empty(self, provider):
        respx.route(method="PROPFIND", url=f"{BASE}/rooms/room-1/").mock(
            return_value=httpx.Response(207, text=MULTISTATUS_EMPTY)
        )
        files = await provider.list_files("room-1")
        assert files == []

    @respx.mock
    async def test_list_nonexistent_workspace(self, provider):
        respx.route(method="PROPFIND", url=f"{BASE}/rooms/room-1/").mock(
            return_value=httpx.Response(404)
        )
        with pytest.raises(WorkspaceNotFoundError):
            await provider.list_files("room-1")


class TestUploadFile:
    @respx.mock
    async def test_upload_returns_file_info(self, provider):
        respx.route(method="PROPFIND", url=f"{BASE}/rooms/room-1/").mock(
            return_value=httpx.Response(207, text=MULTISTATUS_DIR)
        )
        respx.route(method="PUT", url=f"{BASE}/rooms/room-1/doc.pdf").mock(
            return_value=httpx.Response(201)
        )
        info = await provider.upload_file("room-1", "/doc.pdf", b"pdf-content")
        assert info.name == "doc.pdf"
        assert info.path == "/doc.pdf"
        assert info.size_bytes == 11

    @respx.mock
    async def test_upload_to_nonexistent_workspace(self, provider):
        respx.route(method="PROPFIND", url=f"{BASE}/rooms/nope/").mock(
            return_value=httpx.Response(404)
        )
        with pytest.raises(WorkspaceNotFoundError):
            await provider.upload_file("nope", "/doc.pdf", b"content")

    @respx.mock
    async def test_upload_quota_exceeded(self, provider):
        respx.route(method="PROPFIND", url=f"{BASE}/rooms/room-1/").mock(
            return_value=httpx.Response(207, text=MULTISTATUS_DIR)
        )
        respx.route(method="PUT", url=f"{BASE}/rooms/room-1/big.bin").mock(
            return_value=httpx.Response(507)
        )
        with pytest.raises(QuotaExceededError):
            await provider.upload_file("room-1", "/big.bin", b"x" * 100)

    @respx.mock
    async def test_upload_creates_parent_dirs(self, provider):
        respx.route(method="PROPFIND", url=f"{BASE}/rooms/room-1/").mock(
            return_value=httpx.Response(207, text=MULTISTATUS_DIR)
        )
        respx.route(method="MKCOL", url=f"{BASE}/rooms/room-1/sub/").mock(
            return_value=httpx.Response(201)
        )
        respx.route(
            method="PUT", url=f"{BASE}/rooms/room-1/sub/file.txt"
        ).mock(return_value=httpx.Response(201))
        info = await provider.upload_file("room-1", "/sub/file.txt", b"hello")
        assert info.path == "/sub/file.txt"


class TestDownloadFile:
    @respx.mock
    async def test_download_existing(self, provider):
        respx.route(method="GET", url=f"{BASE}/rooms/room-1/doc.pdf").mock(
            return_value=httpx.Response(200, content=b"pdf-bytes")
        )
        content = await provider.download_file("room-1", "/doc.pdf")
        assert content == b"pdf-bytes"

    @respx.mock
    async def test_download_nonexistent(self, provider):
        respx.route(method="GET", url=f"{BASE}/rooms/room-1/nope.txt").mock(
            return_value=httpx.Response(404)
        )
        with pytest.raises(WorkspaceFileNotFoundError):
            await provider.download_file("room-1", "/nope.txt")


class TestDeleteFile:
    @respx.mock
    async def test_delete_file(self, provider):
        respx.route(method="DELETE", url=f"{BASE}/rooms/room-1/doc.pdf").mock(
            return_value=httpx.Response(204)
        )
        await provider.delete_file("room-1", "/doc.pdf")

    @respx.mock
    async def test_delete_nonexistent_raises(self, provider):
        respx.route(method="DELETE", url=f"{BASE}/rooms/room-1/nope.txt").mock(
            return_value=httpx.Response(404)
        )
        with pytest.raises(WorkspaceFileNotFoundError):
            await provider.delete_file("room-1", "/nope.txt")

    @respx.mock
    async def test_delete_nonempty_dir_raises(self, provider):
        respx.route(method="DELETE", url=f"{BASE}/rooms/room-1/notes").mock(
            return_value=httpx.Response(409)
        )
        with pytest.raises(DirectoryNotEmptyError):
            await provider.delete_file("room-1", "/notes")


class TestCreateFolder:
    @respx.mock
    async def test_create_folder_returns_dir_info(self, provider):
        respx.route(method="PROPFIND", url=f"{BASE}/rooms/room-1/").mock(
            return_value=httpx.Response(207, text=MULTISTATUS_DIR)
        )
        respx.route(method="MKCOL", url=f"{BASE}/rooms/room-1/notes/").mock(
            return_value=httpx.Response(201)
        )
        info = await provider.create_folder("room-1", "/notes")
        assert info.is_directory is True
        assert info.name == "notes"
        assert info.path == "/notes"

    @respx.mock
    async def test_create_nested_folder(self, provider):
        respx.route(method="PROPFIND", url=f"{BASE}/rooms/room-1/").mock(
            return_value=httpx.Response(207, text=MULTISTATUS_DIR)
        )
        respx.route(method="MKCOL", url=f"{BASE}/rooms/room-1/a/").mock(
            return_value=httpx.Response(201)
        )
        respx.route(method="MKCOL", url=f"{BASE}/rooms/room-1/a/b/").mock(
            return_value=httpx.Response(201)
        )
        info = await provider.create_folder("room-1", "/a/b")
        assert info.path == "/a/b"


class TestMove:
    @respx.mock
    async def test_move_file(self, provider):
        respx.route(method="MOVE", url=f"{BASE}/rooms/room-1/a.txt").mock(
            return_value=httpx.Response(201)
        )
        respx.route(method="PROPFIND", url=f"{BASE}/rooms/room-1/b.txt").mock(
            return_value=httpx.Response(
                207,
                text=MULTISTATUS_FILE.replace("doc.pdf", "b.txt"),
            )
        )
        info = await provider.move("room-1", "/a.txt", "/b.txt")
        assert info.path == "/b.txt"

    @respx.mock
    async def test_move_nonexistent_raises(self, provider):
        respx.route(method="MOVE", url=f"{BASE}/rooms/room-1/nope.txt").mock(
            return_value=httpx.Response(404)
        )
        with pytest.raises(WorkspaceFileNotFoundError):
            await provider.move("room-1", "/nope.txt", "/b.txt")

    async def test_move_into_self_rejected(self, provider):
        with pytest.raises(InvalidPathError):
            await provider.move("room-1", "/a", "/a/b")

    async def test_move_to_same_path_rejected(self, provider):
        with pytest.raises(InvalidPathError):
            await provider.move("room-1", "/a.txt", "/a.txt")


class TestPathTraversal:
    async def test_dot_dot_rejected(self, provider):
        with pytest.raises(InvalidPathError):
            await provider.upload_file("room-1", "../secret", b"content")

    async def test_nested_traversal_rejected(self, provider):
        with pytest.raises(InvalidPathError):
            await provider.download_file("room-1", "/a/../../etc/passwd")


class TestUrlMethods:
    async def test_web_ui_url(self, provider):
        url = await provider.get_web_ui_url("room-1")
        assert url == f"{BASE}/rooms/room-1/"

    async def test_webdav_url(self, provider):
        url = await provider.get_webdav_url("room-1")
        assert url == f"{BASE}/rooms/room-1/"


class TestPathConstruction:
    def test_room_path(self, provider):
        assert provider._room_path("room-1") == "/rooms/room-1"

    def test_url_root(self, provider):
        assert provider._url("room-1") == f"{BASE}/rooms/room-1/"

    def test_url_file(self, provider):
        assert (
            provider._url("room-1", "/doc.pdf")
            == f"{BASE}/rooms/room-1/doc.pdf"
        )


class TestContentTypeDetection:
    @respx.mock
    async def test_pdf_content_type(self, provider):
        respx.route(method="PROPFIND", url=f"{BASE}/rooms/room-1/").mock(
            return_value=httpx.Response(207, text=MULTISTATUS_DIR)
        )
        respx.route(method="PUT", url=f"{BASE}/rooms/room-1/test.pdf").mock(
            return_value=httpx.Response(201)
        )
        info = await provider.upload_file("room-1", "/test.pdf", b"pdf")
        assert info.content_type == "application/pdf"

    @respx.mock
    async def test_txt_content_type(self, provider):
        respx.route(method="PROPFIND", url=f"{BASE}/rooms/room-1/").mock(
            return_value=httpx.Response(207, text=MULTISTATUS_DIR)
        )
        respx.route(method="PUT", url=f"{BASE}/rooms/room-1/readme.txt").mock(
            return_value=httpx.Response(201)
        )
        info = await provider.upload_file("room-1", "/readme.txt", b"text")
        assert info.content_type == "text/plain"

    @respx.mock
    async def test_png_content_type(self, provider):
        respx.route(method="PROPFIND", url=f"{BASE}/rooms/room-1/").mock(
            return_value=httpx.Response(207, text=MULTISTATUS_DIR)
        )
        respx.route(method="PUT", url=f"{BASE}/rooms/room-1/img.png").mock(
            return_value=httpx.Response(201)
        )
        info = await provider.upload_file("room-1", "/img.png", b"png")
        assert info.content_type == "image/png"

    @respx.mock
    async def test_unknown_content_type(self, provider):
        respx.route(method="PROPFIND", url=f"{BASE}/rooms/room-1/").mock(
            return_value=httpx.Response(207, text=MULTISTATUS_DIR)
        )
        respx.route(method="PUT", url=f"{BASE}/rooms/room-1/data.xyz").mock(
            return_value=httpx.Response(201)
        )
        info = await provider.upload_file("room-1", "/data.xyz", b"binary")
        assert info.content_type == "application/octet-stream"


class TestProtocolCompliance:
    def test_is_workspace_provider(self, provider):
        from soliplex_workspace.protocol import WorkspaceProvider

        assert isinstance(provider, WorkspaceProvider)


class TestPropfindParsing:
    """Test the XML parser handles edge cases."""

    @respx.mock
    async def test_empty_propfind_response(self, provider):
        respx.route(method="PROPFIND", url=f"{BASE}/rooms/room-1/bad").mock(
            return_value=httpx.Response(207, text="not xml")
        )
        with pytest.raises(WorkspaceFileNotFoundError):
            await provider.get_file_info("room-1", "/bad")

    @respx.mock
    async def test_propfind_no_propstat(self, provider):
        xml = """\
<?xml version="1.0" encoding="utf-8"?>
<multistatus xmlns="DAV:">
  <response>
    <href>/rooms/room-1/file.txt</href>
  </response>
</multistatus>"""
        respx.route(
            method="PROPFIND", url=f"{BASE}/rooms/room-1/file.txt"
        ).mock(return_value=httpx.Response(207, text=xml))
        info = await provider.get_file_info("room-1", "/file.txt")
        assert info.name == "file.txt"


class TestListFilesSubpath:
    """Cover list_files with non-root path (url += '/' branch)."""

    @respx.mock
    async def test_list_subdir(self, provider):
        xml = """\
<?xml version="1.0" encoding="utf-8"?>
<multistatus xmlns="DAV:">
  <response>
    <href>/rooms/room-1/sub/</href>
    <propstat>
      <prop>
        <resourcetype><collection/></resourcetype>
      </prop>
    </propstat>
  </response>
  <response>
    <href>/rooms/room-1/sub/file.txt</href>
    <propstat>
      <prop>
        <getcontentlength>5</getcontentlength>
        <resourcetype/>
      </prop>
    </propstat>
  </response>
  <response>
    <href>/rooms/room-1/sub/deep/nested.txt</href>
    <propstat>
      <prop>
        <getcontentlength>3</getcontentlength>
        <resourcetype/>
      </prop>
    </propstat>
  </response>
</multistatus>"""
        respx.route(
            method="PROPFIND",
            url=f"{BASE}/rooms/room-1/sub/",
        ).mock(return_value=httpx.Response(207, text=xml))
        files = await provider.list_files("room-1", "/sub")
        assert len(files) == 1
        assert files[0].name == "file.txt"


class TestPropfindNoProp:
    """Cover propstat without <prop> child (lines 383-384)."""

    @respx.mock
    async def test_propfind_no_prop_element(self, provider):
        xml = """\
<?xml version="1.0" encoding="utf-8"?>
<multistatus xmlns="DAV:">
  <response>
    <href>/rooms/room-1/file.txt</href>
    <propstat>
      <status>HTTP/1.1 200 OK</status>
    </propstat>
  </response>
</multistatus>"""
        respx.route(
            method="PROPFIND",
            url=f"{BASE}/rooms/room-1/file.txt",
        ).mock(return_value=httpx.Response(207, text=xml))
        info = await provider.get_file_info("room-1", "/file.txt")
        assert info.name == "file.txt"


class TestPropfindNoResourceType:
    """Cover missing <resourcetype> element (line 387->391)."""

    @respx.mock
    async def test_no_resourcetype(self, provider):
        xml = """\
<?xml version="1.0" encoding="utf-8"?>
<multistatus xmlns="DAV:">
  <response>
    <href>/rooms/room-1/file.txt</href>
    <propstat>
      <prop>
        <getcontentlength>100</getcontentlength>
      </prop>
    </propstat>
  </response>
</multistatus>"""
        respx.route(
            method="PROPFIND",
            url=f"{BASE}/rooms/room-1/file.txt",
        ).mock(return_value=httpx.Response(207, text=xml))
        info = await provider.get_file_info("room-1", "/file.txt")
        assert info.is_directory is False
        assert info.size_bytes == 100


class TestListFilesRecursive:
    @respx.mock
    async def test_recursive_bfs(self, provider):
        # Root listing: one subdir
        respx.route(method="PROPFIND", url=f"{BASE}/rooms/room-1/").mock(
            return_value=httpx.Response(207, text=MULTISTATUS_LISTING)
        )
        # Subdir listing: one file
        sub_xml = """\
<?xml version="1.0" encoding="utf-8"?>
<multistatus xmlns="DAV:">
  <response>
    <href>/rooms/room-1/notes/</href>
    <propstat><prop>
      <resourcetype><collection/></resourcetype>
    </prop></propstat>
  </response>
  <response>
    <href>/rooms/room-1/notes/readme.md</href>
    <propstat><prop>
      <getcontentlength>42</getcontentlength>
      <resourcetype/>
    </prop></propstat>
  </response>
</multistatus>"""
        respx.route(method="PROPFIND", url=f"{BASE}/rooms/room-1/notes/").mock(
            return_value=httpx.Response(207, text=sub_xml)
        )
        result = await provider.list_files_recursive("room-1")
        paths = [f.path for f in result]
        assert "/notes" in paths
        assert "/doc.pdf" in paths
        assert "/notes/readme.md" in paths

    @respx.mock
    async def test_recursive_max_depth_clamped(self, provider):
        respx.route(method="PROPFIND", url=f"{BASE}/rooms/room-1/").mock(
            return_value=httpx.Response(207, text=MULTISTATUS_EMPTY)
        )
        result = await provider.list_files_recursive("room-1", max_depth=999)
        assert isinstance(result, list)


class TestReadText:
    @respx.mock
    async def test_read_text(self, provider):
        respx.route(method="GET", url=f"{BASE}/rooms/room-1/file.txt").mock(
            return_value=httpx.Response(200, content=b"hello world")
        )
        text = await provider.read_text("room-1", "/file.txt")
        assert text == "hello world"

    @respx.mock
    async def test_read_text_truncated(self, provider):
        respx.route(method="GET", url=f"{BASE}/rooms/room-1/big.txt").mock(
            return_value=httpx.Response(200, content=b"x" * 200)
        )
        text = await provider.read_text("room-1", "/big.txt", max_bytes=50)
        assert len(text) == 50

    @respx.mock
    async def test_read_text_nonexistent(self, provider):
        respx.route(method="GET", url=f"{BASE}/rooms/room-1/nope.txt").mock(
            return_value=httpx.Response(404)
        )
        with pytest.raises(WorkspaceFileNotFoundError):
            await provider.read_text("room-1", "/nope.txt")


class TestWriteText:
    @respx.mock
    async def test_write_text(self, provider):
        respx.route(method="PROPFIND", url=f"{BASE}/rooms/room-1/").mock(
            return_value=httpx.Response(207, text=MULTISTATUS_DIR)
        )
        respx.route(method="PUT", url=f"{BASE}/rooms/room-1/note.txt").mock(
            return_value=httpx.Response(201)
        )
        info = await provider.write_text("room-1", "/note.txt", "hello")
        assert info.name == "note.txt"
        assert info.size_bytes == 5


class TestCloseClient:
    async def test_close_owned_client(self):
        p = DufsWorkspaceProvider(BASE)
        await p.close()

    async def test_close_external_client(self):
        client = httpx.AsyncClient()
        p = DufsWorkspaceProvider(BASE, client=client)
        await p.close()
        # External client should NOT be closed
        assert not client.is_closed
        await client.aclose()
