from unittest.mock import MagicMock, patch

from hsf_app.os_resources import obtener_snapshot_recursos


@patch("hsf_app.os_resources.psutil")
def test_snapshot_incluye_cpu_y_memoria(mock_psutil):
    mock_psutil.cpu_percent.return_value = 12.5
    mock_psutil.virtual_memory.return_value = MagicMock(percent=55.0, available=2_000_000_000)
    mock_psutil.disk_usage.return_value = MagicMock(percent=70.0, free=10_000_000_000)
    mock_psutil.Process.return_value = MagicMock(pid=1234, memory_info=lambda: MagicMock(rss=50_000_000))

    snapshot = obtener_snapshot_recursos()

    assert snapshot["cpu_percent"] == 12.5
    assert snapshot["memoria_percent"] == 55.0
    assert snapshot["disco_percent"] == 70.0
    assert snapshot["proceso_pid"] == 1234
    assert "variables_entorno_relevantes" in snapshot


def test_snapshot_sin_psutil_usa_fallback():
    with patch("hsf_app.os_resources.psutil", None):
        snapshot = obtener_snapshot_recursos()

    assert snapshot["cpu_percent"] is None
    assert snapshot["memoria_percent"] is None
    assert "proceso_pid" in snapshot
    assert "variables_entorno_relevantes" in snapshot
