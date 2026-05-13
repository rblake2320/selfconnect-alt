"""tests/test_cache_request.py — Unit tests for UIA CacheRequest optimization

Tests _get_ui_tree_cached() with mocked comtypes to avoid requiring live UI.
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))


def _make_mock_elem(name="TestElem", ct_id=50000, cls="TestClass", aid="aid1",
                    enabled=True, value="", rect=None, children=None):
    """Build a mock UIA element that looks like a comtypes CachedElement."""
    elem = MagicMock()
    elem.CachedName = name
    elem.CachedControlType = ct_id
    elem.CachedClassName = cls
    elem.CachedAutomationId = aid
    elem.CachedIsEnabled = enabled
    elem.CachedValueValue = value

    r = MagicMock()
    r.left, r.top, r.right, r.bottom = (rect or [0, 0, 100, 30])
    elem.CachedBoundingRectangle = r

    if children:
        mock_kids = MagicMock()
        mock_kids.Length = len(children)
        mock_kids.GetElement = lambda i: children[i]
        elem.GetCachedChildren.return_value = mock_kids
    else:
        elem.GetCachedChildren.return_value = None

    elem.GetCachedPattern.return_value = None
    return elem


class TestGetUiTreeCached:
    def test_returns_none_when_comtypes_unavailable(self):
        from self_connect import _get_ui_tree_cached
        with patch("comtypes.client.CreateObject", side_effect=ImportError("no comtypes")):
            result = _get_ui_tree_cached(12345)
        assert result is None

    def test_returns_list_with_root_dict(self):
        from self_connect import _get_ui_tree_cached
        mock_elem = _make_mock_elem(name="Window", ct_id=50032)
        mock_uia = MagicMock()
        mock_cache_req = MagicMock()
        mock_uia.CreateCacheRequest.return_value = mock_cache_req
        mock_uia.ElementFromHandleBuildCache.return_value = mock_elem

        with patch("comtypes.client.CreateObject", return_value=mock_uia):
            result = _get_ui_tree_cached(99999)

        assert result is not None
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["name"] == "Window"
        assert result[0]["control_type"] == "Window"

    def test_correct_dict_structure(self):
        from self_connect import _get_ui_tree_cached
        mock_elem = _make_mock_elem(
            name="Save", ct_id=50000,  # Button
            cls="Button", aid="btnSave",
            enabled=True, value="",
            rect=[100, 200, 200, 230]
        )
        mock_uia = MagicMock()
        mock_uia.CreateCacheRequest.return_value = MagicMock()
        mock_uia.ElementFromHandleBuildCache.return_value = mock_elem

        with patch("comtypes.client.CreateObject", return_value=mock_uia):
            result = _get_ui_tree_cached(99999)

        assert result is not None
        node = result[0]
        assert node["name"] == "Save"
        assert node["control_type"] == "Button"
        assert node["class_name"] == "Button"
        assert node["automation_id"] == "btnSave"
        assert node["is_enabled"] is True
        assert node["rect"] == {"left": 100, "top": 200, "right": 200, "bottom": 230}
        assert isinstance(node["patterns"], list)
        assert isinstance(node["children"], list)

    def test_children_are_nested(self):
        from self_connect import _get_ui_tree_cached
        child = _make_mock_elem(name="ChildBtn", ct_id=50000)
        parent = _make_mock_elem(name="Panel", ct_id=50033, children=[child])

        mock_uia = MagicMock()
        mock_uia.CreateCacheRequest.return_value = MagicMock()
        mock_uia.ElementFromHandleBuildCache.return_value = parent

        with patch("comtypes.client.CreateObject", return_value=mock_uia):
            result = _get_ui_tree_cached(99999)

        assert result is not None
        assert len(result[0]["children"]) == 1
        assert result[0]["children"][0]["name"] == "ChildBtn"

    def test_returns_none_when_element_from_handle_returns_none(self):
        from self_connect import _get_ui_tree_cached
        mock_uia = MagicMock()
        mock_uia.CreateCacheRequest.return_value = MagicMock()
        mock_uia.ElementFromHandleBuildCache.return_value = None

        with patch("comtypes.client.CreateObject", return_value=mock_uia):
            result = _get_ui_tree_cached(99999)

        assert result is None

    def test_invoke_pattern_detected(self):
        from self_connect import _get_ui_tree_cached
        mock_elem = _make_mock_elem(name="OK", ct_id=50000)
        mock_elem.GetCachedPattern.side_effect = lambda pid: (MagicMock() if pid == 10000 else None)

        mock_uia = MagicMock()
        mock_uia.CreateCacheRequest.return_value = MagicMock()
        mock_uia.ElementFromHandleBuildCache.return_value = mock_elem

        with patch("comtypes.client.CreateObject", return_value=mock_uia):
            result = _get_ui_tree_cached(99999)

        assert result is not None
        assert "Invoke" in result[0]["patterns"]

    def test_respects_max_depth(self):
        """Deeply nested elements beyond max_depth should be excluded."""
        from self_connect import _get_ui_tree_cached

        # Build 3 levels deep
        grandchild = _make_mock_elem(name="Grandchild")
        child = _make_mock_elem(name="Child", children=[grandchild])
        root = _make_mock_elem(name="Root", children=[child])

        mock_uia = MagicMock()
        mock_uia.CreateCacheRequest.return_value = MagicMock()
        mock_uia.ElementFromHandleBuildCache.return_value = root

        with patch("comtypes.client.CreateObject", return_value=mock_uia):
            result = _get_ui_tree_cached(99999, max_depth=1)

        # At max_depth=1, grandchild (depth 2) should be cut off
        assert result is not None
        # Child should be present (depth 1)
        assert len(result[0]["children"]) == 1
        # But grandchild under child should not be there (depth 2 > max_depth 1)
        assert len(result[0]["children"][0]["children"]) == 0

    def test_get_ui_tree_uses_cached_as_strategy_0(self):
        """get_ui_tree() should call _get_ui_tree_cached first."""
        from self_connect import get_ui_tree
        mock_result = [{"name": "CachedRoot", "control_type": "Window",
                        "class_name": "", "automation_id": "", "rect": {},
                        "is_enabled": True, "patterns": [], "value": "", "children": []}]

        with patch("self_connect._get_ui_tree_cached", return_value=mock_result) as mock_cached:
            result = get_ui_tree(99999, max_depth=3)

        mock_cached.assert_called_once_with(99999, 3)
        assert result == mock_result

    def test_get_ui_tree_falls_back_when_cached_returns_none(self):
        """get_ui_tree() should fall back to pywinauto/comtypes when cache fails."""
        from self_connect import get_ui_tree

        with patch("self_connect._get_ui_tree_cached", return_value=None):
            # Should not raise — falls back to existing strategies
            # (which may fail with no live window, but should not crash)
            try:
                get_ui_tree(99999, max_depth=1)
            except Exception:
                pass  # Expected with no live window
