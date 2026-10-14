import time
from unittest.mock import MagicMock, patch

from hsf_app.os_resources import MuestreadorCPU, _variables_entorno_relevantes, obtener_snapshot_recursos


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


def test_path_se_resume_en_vez_de_volcarse_completo(monkeypatch):
    monkeypatch.setenv("PATH", "C:\\a\\b" + (";C:\\x\\y" * 50))
    monkeypatch.setenv("USERNAME", "alguien")

    variables = _variables_entorno_relevantes()

    assert "PATH" in variables
    assert "C:\\a\\b" not in variables["PATH"]
    assert "entradas" in variables["PATH"]
    assert variables["USERNAME"] == "alguien"


def _esperar(condicion, segundos=2.0):
    limite = time.time() + segundos
    while time.time() < limite and not condicion():
        time.sleep(0.01)


@patch("hsf_app.os_resources.psutil")
def test_muestreador_cpu_mide_siempre_en_el_mismo_hilo(mock_psutil):
    mock_psutil.cpu_percent.return_value = 37.5
    muestreador = MuestreadorCPU(intervalo=0.01)

    muestreador.iniciar()
    _esperar(lambda: muestreador.ultimo is not None)
    muestreador.detener()

    assert muestreador.ultimo == 37.5
    assert all(c.kwargs.get("interval") == 0.01 for c in mock_psutil.cpu_percent.call_args_list)


def test_muestreador_sin_psutil_no_mide():
    with patch("hsf_app.os_resources.psutil", None):
        muestreador = MuestreadorCPU(intervalo=0.01)
        muestreador.iniciar()
        time.sleep(0.05)
        muestreador.detener()

    assert muestreador.ultimo is None
