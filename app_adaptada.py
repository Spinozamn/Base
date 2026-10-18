"""
Sistema de Orientacion y Consulta Normativa Institucional
Modulo: Relaciones con la Autoridad y Convivencia Universitaria
Desarrollado por: Jose Manuel Espinoza Romero
Universidad de Guadalajara
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

from langchain_community.document_loaders import PyPDFDirectoryLoader, DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

CONOCIMIENTOS_DIR = "conocimientos"
DB_PATH = "faiss_index"

embeddings = GoogleGenerativeAIEmbeddings(model="gemini-embedding-2")

def cargar_documentos():
    """Recopila y carga archivos documentales en formatos PDF, Markdown y Texto plano exclusivamente desde conocimientos/."""
    documentos_totales = []
    
    if os.path.exists(CONOCIMIENTOS_DIR):
        md_loader = DirectoryLoader(CONOCIMIENTOS_DIR, glob="**/*.md", loader_cls=TextLoader, loader_kwargs={'encoding': 'utf-8'}).load()
        txt_loader = DirectoryLoader(CONOCIMIENTOS_DIR, glob="**/*.txt", loader_cls=TextLoader, loader_kwargs={'encoding': 'utf-8'}).load()
        pdf_loader_con = PyPDFDirectoryLoader(CONOCIMIENTOS_DIR)
        documentos_totales.extend(md_loader.load())
        documentos_totales.extend(txt_loader.load())
        documentos_totales.extend(pdf_loader_con.load())

    return documentos_totales

def inicializar_almacen_vectorial(reindexar=False):
    """Carga la base de datos vectorial local o genera una nueva indexacion documental."""
    if os.path.exists(DB_PATH) and not reindexar:
        print("Cargando base de conocimiento previamente indexada...")
        return FAISS.load_local(DB_PATH, embeddings, allow_dangerous_deserialization=True)
    
    print("Iniciando procesamiento e indexacion del acervo normativo...")
    documentos = cargar_documentos()
    
    if not documentos:
        if os.path.exists(DB_PATH):
            print("No se encontraron nuevos archivos. Utilizando indice existente...")
            return FAISS.load_local(DB_PATH, embeddings, allow_dangerous_deserialization=True)
        else:
            raise FileNotFoundError("No se localizaron documentos normativos en las rutas especificadas.")

    divisor_texto = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=["\nArtículo ", "\nARTÍCULO ", "\nCapítulo ", "\nCAPÍTULO ", "\n## ", "\n# ", "\n\n", "\n", " "]
    )
    fragmentos = divisor_texto.split_documents(documentos)
    print(f"Indexando {len(fragmentos)} segmentos documentales...")
    
    almacen = FAISS.from_documents(fragmentos, embeddings)
    almacen.save_local(DB_PATH)
    print("Base de conocimiento actualizada con exito en directorio local.\n")
    return almacen

forzar_actualizacion = "--reindex" in sys.argv
vector_store = inicializar_almacen_vectorial(reindexar=forzar_actualizacion)
retriever = vector_store.as_retriever(search_kwargs={"k": 5})

# Temperatura 0.0 para maxima precision documental con respaldo ante limites de cuota
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

Contexto documental normativo disponible:
{context}

Consulta planteada por el estudiante:
{input}

Orientación Institucional:
"""

prompt_template = ChatPromptTemplate.from_template(PROMPT_SISTEMA)

def formatear_contexto(docs):
    salida = []
    for doc in docs:
        fuente = os.path.basename(doc.metadata.get("source", "Documento Oficial"))
        pagina = doc.metadata.get("page", None)
        info_pag = f" (Página {pagina + 1})" if pagina is not None else ""
        salida.append(f"--- Documento: {fuente}{info_pag} ---\n{doc.page_content}")
    return "\n\n".join(salida)

rag_chain = (
    {"context": retriever | formatear_contexto, "input": RunnablePassthrough()}
    | prompt_template
    | llm
    | StrOutputParser()
)

def ejecutar_consola():
    print("=" * 72)
    print("UNIVERSIDAD DE GUADALAJARA - RED UNIVERSITARIA")
    print("Sistema de Orientacion y Consulta Normativa Institucional")
    print("Modulo: Relaciones con la Autoridad y Convivencia Universitaria")
    print("Modelo: Respuestas Asertivas, Matriz de Escenarios y Atencion Guiada")
    print("Investigacion y Desarrollo: Jose Manuel Espinoza Romero")
    print("=" * 72)
    print("Instrucciones: Ingrese su consulta o escriba 'salir' para terminar.")
    print("Para actualizar la base documental ejecute: python app_adaptada.py --reindex")
    print("-" * 72)

    while True:
        try:
            entrada = input("\nConsulta de Estudiante: ")
        except (KeyboardInterrupt, EOFError):
            break
            
        if entrada.lower().strip() == 'salir':
            print("\nSesion concluida. Registro cerrado.")
            break
            
        if entrada.strip() == "":
            continue

        print("\nConsultando normativa y estructurando orientacion asertiva...")
        try:
            respuesta = rag_chain.invoke(entrada)
            print(f"\n{respuesta}")
        except Exception as error:
            print(f"\nError de ejecucion: {error}")
            print("Verifique la configuracion de credenciales en el archivo .env.")

if __name__ == "__main__":
    ejecutar_consola()
