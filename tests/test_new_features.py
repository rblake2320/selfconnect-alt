"""tests/test_new_features.py — Tests for SendInput batching, dxcam, SharedMemChannel"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestSendStringBatchedSendInput:
    def test_empty_string_does_nothing(self):
        from self_connect import _send_string_batched_sendinput
        with patch("self_connect.user32") as mock_u32:
            _send_string_batched_sendinput("")
        mock_u32.SendInput.assert_not_called()

    def test_calls_sendinput_once_for_any_length(self):
        """Should call SendInput exactly once regardless of string length."""
        from self_connect import _send_string_batched_sendinput
        with patch("self_connect.user32") as mock_u32:
            _send_string_batched_sendinput("hello world this is a long string " * 10)
        assert mock_u32.SendInput.call_count == 1

    def test_single_char_produces_keydown_and_keyup(self):
        """A single character should produce 2 INPUT structs (down + up)."""
        from self_connect import _send_string_batched_sendinput
        called_with = {}

        def capture(*args):
            called_with["count"] = args[0]

        with patch("self_connect.user32") as mock_u32:
            mock_u32.SendInput.side_effect = capture
            _send_string_batched_sendinput("X")
        assert called_with.get("count") == 2  # down + up


class TestCaptureDxcam:
    def test_returns_none_when_dxcam_unavailable(self):
        """_capture_dxcam should return None when dxcam is not installed."""
        from self_connect import _capture_dxcam
        # Force ImportError for dxcam by removing it from sys.modules if present
        # and patching the import
        with patch.dict("sys.modules", {"dxcam": None}):
            result = _capture_dxcam(12345)
        assert result is None

    def test_returns_none_on_invalid_rect(self):
        """_capture_dxcam should return None when GetWindowRect fails."""
        from self_connect import _capture_dxcam
        mock_dxcam = MagicMock()
        with patch.dict("sys.modules", {"dxcam": mock_dxcam}):
            with patch("self_connect.user32") as mock_u32:
                mock_u32.GetWindowRect.return_value = False
                result = _capture_dxcam(99999)
        assert result is None

    def test_capture_window_attempts_dxcam_first(self):
        """capture_window() should try dxcam before PrintWindow."""
        from self_connect import capture_window

        fake_img = MagicMock()
        with patch("self_connect._capture_dxcam", return_value=fake_img) as mock_dxcam:
            result = capture_window(99999)
        mock_dxcam.assert_called_once_with(99999)
        assert result is fake_img


class TestSharedMemChannel:
    def test_send_recv_roundtrip(self):
        """Data written via send() should be returned by recv()."""
        from self_connect import SharedMemChannel

        with SharedMemChannel("TestChannel_SCUnit", size=4096) as writer:
            with SharedMemChannel("TestChannel_SCUnit", size=4096) as reader:
                test_data = b"hello from agent A"
                writer.send(test_data)
                received = reader.recv(timeout=2.0)

        assert received == test_data

    def test_recv_timeout_returns_none(self):
        """recv() should return None when nothing is sent within timeout."""
        from self_connect import SharedMemChannel

        with SharedMemChannel("TestChannel_Timeout_SC", size=4096) as ch:
            result = ch.recv(timeout=0.1)
        assert result is None

    def test_send_raises_on_oversized_data(self):
        """send() should raise ValueError when data exceeds channel capacity."""
        import pytest
        from self_connect import SharedMemChannel

        with SharedMemChannel("TestChannel_OversizeSC", size=64) as ch:
            with pytest.raises(ValueError, match="too large"):
                ch.send(b"x" * 1000)

    def test_multiple_sends(self):
        """Last sent value should be readable."""
        from self_connect import SharedMemChannel

        with SharedMemChannel("TestChannel_MultiSC", size=4096) as writer:
            with SharedMemChannel("TestChannel_MultiSC", size=4096) as reader:
                writer.send(b"first")
                reader.recv(timeout=0.5)  # consume first
                writer.send(b"second")
                received = reader.recv(timeout=0.5)
        assert received == b"second"

    def test_context_manager(self):
        """SharedMemChannel should work as context manager."""
        from self_connect import SharedMemChannel

        with SharedMemChannel("TestChannel_CTX_SC", size=1024) as ch:
            ch.send(b"test")
            data = ch.recv(timeout=0.5)
        assert data == b"test"
