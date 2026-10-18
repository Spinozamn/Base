# -*- coding: utf-8 -*-
"""
UNIVERSIDAD DE GUADALAJARA - RED UNIVERSITARIA
CENTRO UNIVERSITARIO DE TONALÁ (CUTonalá)
Script de Prueba de Humo (Smoke Test) Integral
Autor: José Manuel Espinoza Romero
"""

import sys
import os
import json
import time
import urllib.request
import urllib.parse
from http.server import ThreadingHTTPServer
import threading

# Asegurar codificación utf-8 en consola
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

import servidor

RESULTADOS = []

def registrar_resultado(nombre, exitoso, detalle=""):
    estado = "PASÓ [OK]" if exitoso else "FALLÓ [ERROR]"
    RESULTADOS.append((nombre, exitoso, detalle))
    print(f"[{estado}] {nombre}")
    if detalle:
        print(f"       Detalle: {detalle}\n")

def ejecutar_prueba_humo():
    print("=" * 75)
    print("INICIANDO PRUEBA DE HUMO (SMOKE TEST) - SISTEMA DE ORIENTACIÓN UDEG")
    print("=" * 75 + "\n")

    # 1. Comprobación de Archivos de Conocimientos
    archivos_esperados = [
        "01_informacion_personal.md",
        "02_marco_legal_mexicano.md",
        "03_normativa_institucional_udg.md"
    ]
    conocimientos_dir = os.path.join(os.path.dirname(__file__), "conocimientos")
    archivos_presentes = os.listdir(conocimientos_dir) if os.path.exists(conocimientos_dir) else []
    
    docs_ok = all(f in archivos_presentes for f in archivos_esperados) and len(archivos_presentes) == 3
    registrar_resultado(
        "Integridad de base documental (exactamente 3 archivos normativos)",
        docs_ok,
        f"Archivos encontrados: {', '.join(archivos_presentes)}"
    )

    # 2. Inicialización del Motor RAG y Modelos con Fallback
    t0 = time.time()
    rag_iniciado = servidor.inicializar_motor_rag(reindexar=False)
    t_rag = round(time.time() - t0, 2)
    registrar_resultado(
        f"Carga e inicialización del motor RAG con FAISS y Fallback (tiempo: {t_rag}s)",
        rag_iniciado,
        "Retriever y cadena RAG preparados correctamente en memoria."
    )

    if not rag_iniciado:
        print("ERROR CRÍTICO: No se pudo inicializar la cadena RAG. Abortando prueba.")
        return

    # 3. Levantamiento de Servidor HTTP en hilo secundario
    puerto_test = 8089
    servidor_http = None
    for p in range(8089, 8100):
        try:
            servidor_http = ThreadingHTTPServer(("127.0.0.1", p), servidor.ManejadorPeticiones)
            puerto_test = p
            break
        except OSError:
            continue

    if not servidor_http:
        registrar_resultado("Asignación de puerto HTTP para prueba de humo", False, "No se encontró puerto libre.")
        return

    hilo_servidor = threading.Thread(target=servidor_http.serve_forever, daemon=True)
    hilo_servidor.start()
    time.sleep(0.5)

    base_url = f"http://127.0.0.1:{puerto_test}"
    registrar_resultado(
        "Levantamiento del servidor web local",
        True,
        f"Servicio escuchando en {base_url}"
    )

    # 4. Prueba HTTP GET / (Interfaz Gráfica)
    try:
        with urllib.request.urlopen(f"{base_url}/", timeout=5) as resp:
            codigo = resp.status
            contenido = resp.read().decode("utf-8")
            interfaz_ok = (codigo == 200) and ("Orientación Normativa UdeG" in contenido)
            registrar_resultado(
                "Endpoint GET / (Servir interfaz web Telegram-style)",
                interfaz_ok,
                f"Código HTTP {codigo}, longitud HTML: {len(contenido)} bytes."
            )
    except Exception as e:
        registrar_resultado("Endpoint GET /", False, str(e))

    # 5. Batería de Pruebas POST /api/consulta (Escenarios Clave)
    casos = [
        {
            "id": "A. Saludo / Cortesía",
            "mensaje": "Hola, buenas tardes",
            "criterio": lambda r: len(r) > 10 and any(w in r.lower() for w in ["hola", "buen", "orientaci", "asistente", "udeg"]),
            "desc": "Respuesta breve y cordial presentando el servicio institucional."
        },
        {
            "id": "B. Desvío amable fuera de tema",
            "mensaje": "¿Cuál es la mejor receta para preparar tacos al pastor?",
            "criterio": lambda r: any(w in r.lower() for w in ["reglamento", "institucional", "autoridad", "derecho", "normat", "exclusivamente"]),
            "desc": "Reconoce con calidez y redirige sin agresividad hacia la temática UdeG."
        },
        {
            "id": "C. Encargado y Ubicación física (ICC)",
            "mensaje": "¿Quién es la persona encargada de computación en CUTonalá y dónde está su oficina?",
            "criterio": lambda r: "vargas" in r.lower() and "cae" in r.lower(),
            "desc": "Identifica a la Mtra. Dulce María Vargas Mora y la oficina en CAE 3er piso."
        },
        {
            "id": "D. Maestro de confianza y apoyo legal/Fiscalía",
            "mensaje": "¿Qué maestro de confianza me puede orientar y tiene vinculación con fiscalía?",
            "criterio": lambda r: "hoyos" in r.lower() and ("fiscal" in r.lower() or "forense" in r.lower() or "ciberseguridad" in r.lower()),
            "desc": "Identifica al Prof. Enrique Hoyos Peña, especialidad forense/ciberseguridad y laboratorios I-101/I-102."
        },
        {
            "id": "E. Coordinadora de Energía como alternativa empática",
            "mensaje": "La coordinadora de computación no me ayuda, ¿con quién más puedo acudir?",
            "criterio": lambda r: ("energía" in r.lower() or "energia" in r.lower() or "recio" in r.lower() or "carolina" in r.lower()) and "cae" in r.lower(),
            "desc": "Canaliza hacia la Coordinadora de Energía (Dra. Carolina Livier) en el mismo piso del CAE."
        },
        {
            "id": "F. Conflicto de interés por relación con docente",
            "mensaje": "Tengo una relación afectiva con el profesor de mi clase actual, ¿qué dice la norma?",
            "criterio": lambda r: ("conflicto" in r.lower() or "conducta" in r.lower() or "sinodal" in r.lower() or "imparcial" in r.lower()),
            "desc": "Fundamenta conflicto de interés (Código de Conducta) y derecho a sinodal neutral."
        }
    ]

    print("\n--- Ejecutando Batería de Pruebas de Consulta RAG ---")
    for c in casos:
        t_inicio = time.time()
        try:
            req_data = json.dumps({"mensaje": c["mensaje"]}).encode("utf-8")
            req = urllib.request.Request(
                f"{base_url}/api/consulta",
                data=req_data,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=45) as resp:
                t_resp = round(time.time() - t_inicio, 2)
                res_json = json.loads(resp.read().decode("utf-8"))
                texto = res_json.get("respuesta", "")
                
                cumple = c["criterio"](texto)
                fragmento = texto.replace("\n", " ")[:110] + "..." if len(texto) > 110 else texto
                registrar_resultado(
                    f"Caso {c['id']} (latencia: {t_resp}s)",
                    cumple,
                    f"Entrada: '{c['mensaje']}'\n       Salida: {fragmento}"
                )
            time.sleep(1)
        except Exception as ex:
            registrar_resultado(f"Caso {c['id']}", False, f"Excepción durante petición: {str(ex)}")

    # 6. Cierre del servidor de prueba
    servidor_http.shutdown()
    servidor_http.server_close()

    # Resumen final
    total = len(RESULTADOS)
    pasadas = sum(1 for _, ok, _ in RESULTADOS if ok)
    falladas = total - pasadas

    print("\n" + "=" * 75)
    print(f"RESUMEN DE PRUEBA DE HUMO: {pasadas}/{total} PRUEBAS SUPERADAS")
    if falladas == 0:
        print("ESTADO GENERAL: SISTEMA 100% OPERATIVO Y CONFORME A ESPECIFICACIONES")
    else:
        print(f"ESTADO GENERAL: SE REGISTRARON {falladas} ADVERTENCIAS O FALLOS")
    print("=" * 75 + "\n")

if __name__ == "__main__":
    ejecutar_prueba_humo()
