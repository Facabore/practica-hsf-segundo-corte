from hsf_app.processing import clasificar_lectura


def _lectura(**overrides):
    base = {
        "device_id": "SIM-001",
        "timestamp": "2026-10-06T10:00:00",
        "temperatura_c": 22.5,
        "humedad_pct": 45.0,
        "vibracion_mm_s": 1.2,
    }
    base.update(overrides)
    return base


def test_lectura_dentro_de_rango_es_normal():
    resultado = clasificar_lectura(_lectura())
    assert resultado.estado == "normal"
    assert resultado.variables_anomalas == []


def test_temperatura_sobre_el_umbral_es_anomala():
    resultado = clasificar_lectura(_lectura(temperatura_c=60.0))
    assert resultado.estado == "anomalo"
    assert "temperatura_c" in resultado.variables_anomalas


def test_humedad_fuera_de_rango_es_anomala():
    resultado = clasificar_lectura(_lectura(humedad_pct=5.0))
    assert resultado.estado == "anomalo"
    assert "humedad_pct" in resultado.variables_anomalas


def test_vibracion_alta_es_anomala():
    resultado = clasificar_lectura(_lectura(vibracion_mm_s=8.0))
    assert resultado.estado == "anomalo"
    assert "vibracion_mm_s" in resultado.variables_anomalas


def test_varias_variables_anomalas_a_la_vez():
    resultado = clasificar_lectura(_lectura(temperatura_c=60.0, vibracion_mm_s=8.0))
    assert resultado.estado == "anomalo"
    assert set(resultado.variables_anomalas) == {"temperatura_c", "vibracion_mm_s"}
