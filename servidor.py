"""
Sistema de Orientacion y Consulta Normativa Institucional
Servidor Web Local e Interfaz Grafica
Desarrollado por: Jose Manuel Espinoza Romero
Universidad de Guadalajara
"""

import os
import sys
import json
import webbrowser
import threading
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from dotenv import load_dotenv

CONOCIMIENTOS_DIR = "conocimientos"
DB_PATH = "faiss_index"
HOST = "127.0.0.1"
PORT = 5000

rag_chain = None
rag_lock = threading.Lock()

def obtener_api_key():
    """Obtiene la clave de API desde el entorno o archivo .env."""
    load_dotenv(override=True)
    clave = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if clave and clave.strip() and clave.strip() != "tu_clave_de_gemini_aqui":
        return clave.strip()
    return None

def guardar_api_key(clave):
    """Registra la clave de API en el archivo .env y reinicializa el motor."""
    clave = clave.strip()
    if not clave:
        return False
    
    os.environ["GOOGLE_API_KEY"] = clave
    ruta_env = os.path.join(os.path.dirname(__file__), ".env")
    lineas = []
    reemplazado = False
    
    if os.path.exists(ruta_env):
        with open(ruta_env, "r", encoding="utf-8") as f:
            for linea in f:
                if linea.startswith("GOOGLE_API_KEY="):
                    lineas.append(f"GOOGLE_API_KEY={clave}\n")
                    reemplazado = True
                else:
                    lineas.append(linea)
    
    if not reemplazado:
        lineas.append(f"GOOGLE_API_KEY={clave}\n")
        
    with open(ruta_env, "w", encoding="utf-8") as f:
        f.writelines(lineas)
        
    return inicializar_motor_rag(reindexar=False)

def cargar_documentos():
    """Carga documentos normativos exclusivamente desde la carpeta conocimientos (Markdown, TXT y PDF)."""
    docs = []
    from langchain_community.document_loaders import PyPDFDirectoryLoader, DirectoryLoader, TextLoader
    
    if os.path.exists(CONOCIMIENTOS_DIR):
        docs.extend(DirectoryLoader(CONOCIMIENTOS_DIR, glob="**/*.md", loader_cls=TextLoader, loader_kwargs={'encoding': 'utf-8'}).load())
        docs.extend(DirectoryLoader(CONOCIMIENTOS_DIR, glob="**/*.txt", loader_cls=TextLoader, loader_kwargs={'encoding': 'utf-8'}).load())
        docs.extend(PyPDFDirectoryLoader(CONOCIMIENTOS_DIR).load())
    return docs

def inicializar_motor_rag(reindexar=False):
    """Inicializa la cadena RAG con respuestas cortas, asertivas y desvio amable fuera de tema."""
    global rag_chain
    api_key = obtener_api_key()
    if not api_key:
        return False

    with rag_lock:
        try:
            from langchain_text_splitters import RecursiveCharacterTextSplitter
            from langchain_community.vectorstores import FAISS
            from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
            from langchain_core.prompts import ChatPromptTemplate
            from langchain_core.runnables import RunnablePassthrough
            from langchain_core.output_parsers import StrOutputParser

            embeddings = GoogleGenerativeAIEmbeddings(model="gemini-embedding-2")
            
            if os.path.exists(DB_PATH) and not reindexar:
                vector_store = FAISS.load_local(DB_PATH, embeddings, allow_dangerous_deserialization=True)
            else:
                docs = cargar_documentos()
                if not docs:
                    if os.path.exists(DB_PATH):
                        vector_store = FAISS.load_local(DB_PATH, embeddings, allow_dangerous_deserialization=True)
                    else:
                        return False
                else:
                    text_splitter = RecursiveCharacterTextSplitter(
                        chunk_size=1000,
                        chunk_overlap=200,
                        separators=["\nArtículo ", "\nARTÍCULO ", "\nCapítulo ", "\nCAPÍTULO ", "\n## ", "\n# ", "\n\n", "\n", " "]
                    )
                    chunks = text_splitter.split_documents(docs)
                    vector_store = FAISS.from_documents(chunks, embeddings)
                    vector_store.save_local(DB_PATH)

            retriever = vector_store.as_retriever(search_kwargs={"k": 5})
            llm_principal = ChatGoogleGenerativeAI(model="gemini-3.5-flash", temperature=0.0)
            llm_respaldo1 = ChatGoogleGenerativeAI(model="gemini-3.5-flash-lite", temperature=0.0)
            llm_respaldo2 = ChatGoogleGenerativeAI(model="gemini-3.8-flash", temperature=0.0, max_retries=0)
            llm = llm_principal.with_fallbacks([llm_respaldo1, llm_respaldo2])

            PROMPT_SISTEMA = """
Eres el Asesor Especializado en Relaciones con la Autoridad y Convivencia Institucional de la Universidad de Guadalajara (UdeG).

ESTILO Y TONO:
- Respuestas CORTAS, ASERTIVAS, CLARAS Y DIRECTAS al punto.
- Tono respetuoso, formal y empático, sin saturar al alumno con textos largos ni burocracia innecesaria.
- Comunica con naturalidad y precisión técnica.

PROTOCOLO DE ATENCIÓN SEGÚN EL TIPO DE MENSAJE:

A. SALUDOS O MENSAJES DE CORTESÍA (ej. "Hola", "Buenos días", "¿Quién eres?"):
- Responde de forma cordial en 1 o 2 líneas breves, presentándote como el asistente de orientación normativa de la UdeG y preguntándole en qué situación con algún docente o autoridad universitaria le puedes apoyar hoy.

B. PREGUNTAS FUERA DE TEMA (Temas ajenos a la UdeG, tareas generales, cocina, chistes, etc.):
- Sé amable, cálido y asertivo; NUNCA suenes agresivo ni regañes al usuario.
- En 2 oraciones breves, reconoce la consulta y redirígelo con gentileza hacia el tema central:
"Comprendo tu pregunta, sin embargo, mi función como asistente institucional está especializada exclusivamente en orientarte sobre reglamentos de la UdeG, derechos estudiantiles y relaciones o conflictos con profesores y autoridades. Si tienes alguna duda o situación académica en tu centro universitario, con mucho gusto te oriento."

C. CONSULTAS SOBRE SITUACIONES, CONFLICTOS O DUDAS NORMATIVAS DE LA UDEG:
Estructura tu respuesta de forma breve y asertiva en 3 puntos claros:
1. Orientación Directa (Máximo 2 párrafos cortos): Explica con claridad la regla esencial que aplica a su caso (asimetría de poder, conflicto de interés, derecho a revisión o protección ante represalias/hostigamiento).
2. Pregunta de Diagnóstico (1 pregunta concisa): Haz una pregunta clave para entender mejor su situación (ej. si el docente lo evalúa actualmente, si cursa en preparatoria o licenciatura, o si ha sufrido afectaciones en sus notas).
3. Opciones de Ayuda: Indícale de forma puntual que si lo requiere, puedes:
   - Desglosarle los artículos específicos de la normativa oficial.
   - Facilitarle el formato u oficio formal listo para llenar (cambio de sinodal, queja, etc.).
   - Compartirle los datos de contacto de profesores orientadores o enlaces de apoyo de su centro universitario registrados en el catálogo institucional.

D. SOLICITUD DE CONTACTO CON MAESTROS DE APOYO:
- Si el estudiante solicita maestros de apoyo o enlaces de confianza, consulta el archivo del catálogo en el contexto.
- Si para su centro el catálogo aún está en registro preliminar, indícale amablemente que el padrón de su centro está en actualización e infórmale que puede acudir de inmediato a su Coordinación de Carrera o a la Defensoría de los Derechos Universitarios (DDU en Lerdo de Tejada #2640 o teléfono 33 3540 3028).

E. RESPUESTA A CONSULTAS ESPECÍFICAS DE GESTIÓN (ENCARGADO, UBICACIÓN, PROGRAMA, JUSTIFICACIÓN, COORDINADORA):
Cuando el estudiante pregunte específicamente sobre alguno de estos aspectos, responde de manera directa, asertiva y precisa:
- "Nombre del encargado": Proporciona el nombre de la autoridad académica o enlace competente según el contexto (en CUTonalá ICC: Coordinadora Mtra. Dulce María Vargas Mora; Enlace DDU; Primer Contacto).
- "Dónde lo encuentro": Indica la ubicación física exacta del campus (ej. Centro de Atención a Estudiantes - CAE, 3er piso para Coordinación ICC; CAE planta baja para DDU y Primer Contacto; Centro de Recursos Tecnológicos - CRT, 3er piso para la Dirección de DIIT).
- "Vías de contacto": Facilita los correos institucionales oficiales (`cd.computacion@cutonala.udg.mx`, `ddu.cutonala@redudg.udg.mx`), teléfonos y extensiones (Ext. 64117).
- "En qué consiste el programa": Explica con claridad el Protocolo PPASE de la UdeG y el marco de la DDU (medidas cautelares inmediatas de separación y sinodal neutral), y el mecanismo de revisión colegiada (Arts. 49-52 RGEPA).
- "La relación entre mi caso y el programa (Justificación)": Fundamenta con rigor técnico por qué su caso encuadra en el programa (asimetría de poder estructural, conflicto de interés objetivo que vicia la imparcialidad docente, o presunción de hostigamiento/represalias tras desacuerdo o ruptura).
- "Asesoría adicional (Coordinadora)": Detalla las facultades concretas de apoyo de la Coordinadora de Carrera (reubicación de grupo sin daño de horario/créditos, solicitud de sinodal alterno ante Jefatura, seguimiento confidencial de kardex en SIAU y canalización prioritaria).

REGLA DE RIGOR DOCUMENTAL:
- Responde únicamente con fundamento en la documentación oficial disponible en el contexto. Si un dato no existe en los documentos, indícalo con transparencia sin inventar.

Contexto normativo y casuística disponible:
{context}

Consulta del estudiante:
{input}

Orientación Institucional:
"""
            prompt_template = ChatPromptTemplate.from_template(PROMPT_SISTEMA)

            def formatear_contexto(d):
                salida = []
                for doc in d:
                    fuente = os.path.basename(doc.metadata.get("source", "Ordenamiento"))
                    pag = doc.metadata.get("page", None)
                    p_info = f" (Página {pag + 1})" if pag is not None else ""
                    salida.append(f"--- Documento: {fuente}{p_info} ---\n{doc.page_content}")
                return "\n\n".join(salida)

            rag_chain = (
                {"context": retriever | formatear_contexto, "input": RunnablePassthrough()}
                | prompt_template
                | llm
                | StrOutputParser()
            )
            return True
        except Exception as e:
            print(f"[Aviso de inicializacion]: {e}")
            return False

class ManejadorPeticiones(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            ruta_html = os.path.join(os.path.dirname(__file__), "interfaz.html")
            if os.path.exists(ruta_html):
                with open(ruta_html, "rb") as f:
                    contenido = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(contenido)))
                self.end_headers()
                self.wfile.write(contenido)
            else:
                self.send_error(404, "Archivo de interfaz no encontrado")
        elif self.path == "/api/estado":
            tiene_clave = bool(obtener_api_key())
            resp = json.dumps({"tiene_clave": tiene_clave}).encode("utf-8")
            self._enviar_json(resp)
        else:
            self.send_error(404)

    def do_POST(self):
        longitud = int(self.headers.get("Content-Length", 0))
        cuerpo = self.rfile.read(longitud).decode("utf-8") if longitud > 0 else "{}"

        if self.path == "/api/consulta":
            try:
                datos = json.loads(cuerpo)
                mensaje = datos.get("mensaje", "").strip()
                
                if not mensaje:
                    respuesta_json = json.dumps({"error": "Consulta vacia"}).encode("utf-8")
                else:
                    global rag_chain
                    if rag_chain is None:
                        exito = inicializar_motor_rag()
                        if not exito or rag_chain is None:
                            respuesta_json = json.dumps({
                                "error": "No se ha configurado la clave de API. Por favor, ingresa tu clave para habilitar las consultas.",
                                "requiere_clave": True
                            }).encode("utf-8")
                            self._enviar_json(respuesta_json)
                            return
                    
                    texto_respuesta = str(rag_chain.invoke(mensaje))
                    respuesta_json = json.dumps({"respuesta": texto_respuesta}).encode("utf-8")
            except Exception as e:
                respuesta_json = json.dumps({"error": f"Error al emitir respuesta: {str(e)}"}).encode("utf-8")

            self._enviar_json(respuesta_json)

        elif self.path == "/api/configurar_clave":
            try:
                datos = json.loads(cuerpo)
                clave = datos.get("clave", "").strip()
                if not clave:
                    respuesta_json = json.dumps({"status": "error", "mensaje": "La clave no puede estar vacía"}).encode("utf-8")
                else:
                    guardar_api_key(clave)
                    respuesta_json = json.dumps({"status": "ok"}).encode("utf-8")
            except Exception as e:
                respuesta_json = json.dumps({"status": "error", "mensaje": str(e)}).encode("utf-8")
            self._enviar_json(respuesta_json)

        elif self.path == "/api/reindexar":
            try:
                exito = inicializar_motor_rag(reindexar=True)
                if exito:
                    respuesta_json = json.dumps({"status": "ok"}).encode("utf-8")
                else:
                    respuesta_json = json.dumps({"status": "error", "mensaje": "Verifique que la clave de API esté registrada"}).encode("utf-8")
            except Exception as e:
                respuesta_json = json.dumps({"status": "error", "mensaje": str(e)}).encode("utf-8")

            self._enviar_json(respuesta_json)
        else:
            self.send_error(404)

    def _enviar_json(self, bytes_data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(bytes_data)))
        self.end_headers()
        self.wfile.write(bytes_data)

def abrir_navegador(url):
    threading.Timer(1.2, lambda: webbrowser.open(url)).start()

def iniciar_servidor():
    print("=" * 72)
    print("UNIVERSIDAD DE GUADALAJARA - RED UNIVERSITARIA")
    print("Sistema de Orientacion y Consulta Normativa Institucional")
    print("Desarrollado por: Jose Manuel Espinoza Romero")
    print("Modulo: Respuestas Asertivas, Matriz de Escenarios y Atencion Guiada")
    print("=" * 72)

    clave_actual = obtener_api_key()
    if clave_actual:
        print("Estado: Clave de API verificada en archivo de configuracion local.")
    else:
        print("Estado: No se ha detectado clave de API.")
        print("La interfaz solicitara la clave automaticamente al abrirse.")

    puerto_actual = PORT
    servidor = None

    for intento in range(5):
        try:
            servidor = ThreadingHTTPServer((HOST, puerto_actual), ManejadorPeticiones)
            break
        except OSError:
            puerto_actual += 1

    if not servidor:
        print("No fue posible asignar un puerto de red disponible.")
        return

    url = f"http://{HOST}:{puerto_actual}"
    print(f"Servicio iniciado correctamente en: {url}")
    print("Abriendo interfaz web en el navegador...")
    print("Presione Ctrl + C en esta ventana para detener el servicio.")
    print("-" * 72)

    if clave_actual:
        inicializar_motor_rag(reindexar=False)

    abrir_navegador(url)

    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nCerrando servicio...")
    finally:
        servidor.server_close()

if __name__ == "__main__":
    iniciar_servidor()
