import io
import json
import queue

import pytest

from firmware.firmware_simulador import crear_servidor, escribir_manifiesto, escuchar_comandos, generar_trama, interpretar_comando
from hsf_app.processing import clasificar_lectura
from hsf_app.validation import ErrorValidacion, validar_lectura


def test_trama_normal_es_json_valido_con_device_id():
    lectura = json.loads(generar_trama(1, None))

    validar_lectura(lectura)
    assert lectura["device_id"] == "SIM-001"


def test_comando_dato_corrupto_produce_una_linea_que_no_es_json():
    linea = generar_trama(1, "dato_corrupto")

    assert linea.endswith(b"\n")
    with pytest.raises(json.JSONDecodeError):
        json.loads(linea)


def test_comando_fuera_de_rango_es_rechazado_por_la_validacion():
    lectura = json.loads(generar_trama(1, "fuera_de_rango"))

    with pytest.raises(ErrorValidacion):
        validar_lectura(lectura)


def test_comando_forzar_anomalia_es_valido_pero_anomalo():
    lectura = json.loads(generar_trama(1, "forzar_anomalia"))

    validar_lectura(lectura)
    assert clasificar_lectura(lectura).estado == "anomalo"


def test_interpretar_comando_acepta_solo_la_lista_cerrada():
    assert interpretar_comando("  DATO_CORRUPTO \n") == "dato_corrupto"
    assert interpretar_comando("rm -rf /") is None
    assert interpretar_comando("") is None


def test_escuchar_comandos_encola_solo_los_validos():
    cola = queue.Queue()

    escuchar_comandos(cola, io.StringIO("dato_corrupto\nborrar_todo\nforzar_anomalia\n"))

    assert cola.get_nowait() == "dato_corrupto"
    assert cola.get_nowait() == "forzar_anomalia"
    assert cola.empty()


def test_no_puede_haber_dos_firmwares_en_el_mismo_puerto():
    primero = crear_servidor("127.0.0.1", 0)
    try:
        puerto = primero.getsockname()[1]
        with pytest.raises(OSError):
            crear_servidor("127.0.0.1", puerto).close()
    finally:
        primero.close()


def test_la_trama_lleva_el_device_id_configurado():
    lectura = json.loads(generar_trama(1, None, device_id="SIM-002"))

    assert lectura["device_id"] == "SIM-002"


def test_la_anomalia_periodica_respeta_los_ciclos_configurados():
    normal = json.loads(generar_trama(7, None, ciclos=11))
    anomala = json.loads(generar_trama(11, None, ciclos=11))

    assert clasificar_lectura(normal).estado == "normal"
    assert clasificar_lectura(anomala).estado == "anomalo"


def test_el_manifiesto_se_escribe_aparte_por_dispositivo(tmp_path):
    escribir_manifiesto("SIM-009", 9999, directorio=tmp_path)

    datos = json.loads((tmp_path / "device_manifest_SIM-009.json").read_text(encoding="utf-8"))
    assert datos["device_id"] == "SIM-009"
    assert datos["puerto"] == 9999
