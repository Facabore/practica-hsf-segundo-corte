import pytest

from hsf_app.validation import ErrorValidacion, validar_lectura


def _lectura_valida(**overrides):
    base = {
        "device_id": "SIM-001",
        "timestamp": "2026-10-06T10:00:00",
        "temperatura_c": 22.5,
        "humedad_pct": 45.0,
        "vibracion_mm_s": 1.2,
    }
    base.update(overrides)
    return base


def test_lectura_valida_no_lanza_error():
    validar_lectura(_lectura_valida())  # no debe lanzar


def test_falta_un_campo_requerido():
    lectura = _lectura_valida()
    del lectura["humedad_pct"]
    with pytest.raises(ErrorValidacion, match="humedad_pct"):
        validar_lectura(lectura)


def test_tipo_incorrecto_en_campo_numerico():
    lectura = _lectura_valida(temperatura_c="veintidos")
    with pytest.raises(ErrorValidacion, match="temperatura_c"):
        validar_lectura(lectura)


def test_valor_fuera_del_rango_fisicamente_valido():
    lectura = _lectura_valida(humedad_pct=250.0)
    with pytest.raises(ErrorValidacion, match="humedad_pct"):
        validar_lectura(lectura)


def test_device_id_vacio_es_invalido():
    lectura = _lectura_valida(device_id="")
    with pytest.raises(ErrorValidacion, match="device_id"):
        validar_lectura(lectura)


def test_entrada_que_no_es_diccionario():
    with pytest.raises(ErrorValidacion):
        validar_lectura("esto no es un dict")
