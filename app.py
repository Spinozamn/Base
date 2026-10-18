import os
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
import time

# Inicializar embeddings de Gemini
embeddings = GoogleGenerativeAIEmbeddings(model="gemini-embedding-2")
DB_PATH = "faiss_index"

# 1. Comprobar si ya existe el entrenamiento guardado localmente
if os.path.exists(DB_PATH):
    print("Cargando conocimiento previamente guardado localmente...")
    # Cargamos la base de datos desde el disco sin llamar a la API de Google
    vector_store = FAISS.load_local(DB_PATH, embeddings, allow_dangerous_deserialization=True)
else:
    print("No se encontró base de datos local. Procesando PDFs por primera vez...")
    print("Cargando documentos de conocimiento...")
    loader = PyPDFDirectoryLoader("conocimientos/")
    docs = loader.load()

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = text_splitter.split_documents(docs)

    print(f"Generando indexación de vectores para {len(chunks)} fragmentos...")
    print("Nota: Si sale error 429, espera 1 minuto y vuelve a ejecutar.")
    
    # Creamos e indexamos la base de datos
    vector_store = FAISS.from_documents(chunks, embeddings)
    
    # Guardamos localmente para no volver a gastar cuota de la API jamás
    vector_store.save_local(DB_PATH)
    print("¡Conocimiento guardado con éxito en la carpeta 'faiss_index'!")

retriever = vector_store.as_retriever(search_kwargs={"k": 4})

# 2. Inicializar el modelo LLM de Gemini
llm = ChatGoogleGenerativeAI(model="gemini-3.8-flash", temperature=0.2)

# 3. Definir tu SYSTEM PROMPT
CONSEJERO_SYSTEM_PROMPT = """
Eres el "Tutor de Ética y Normativa Institucional", experto en reglas.
Tu tono es directo, profesional y útil para el estudiante.
Esta es orientación educativa, no asesoría legal.

PRINCIPIOS DE RESPUESTA (ORDEN OBLIGATORIO):

1) PRIORIDAD A LA INTENCIÓN DEL ESTUDIANTE
Primero responde exactamente lo que el estudiante solicita.
Si la consulta es factual y está soportada por documentos.

Utiliza únicamente los siguientes fragmentos de contexto proporcionados para responder la pregunta. 
Si la respuesta no se encuentra en el contexto, menciona amablemente que no posees información oficial al respecto.

Contexto:
{context}

Pregunta del estudiante: {input}
"""

prompt_template = ChatPromptTemplate.from_template(CONSEJERO_SYSTEM_PROMPT)

def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

# 4. Crear la cadena RAG Moderna (LCEL)
rag_chain = (
    {"context": retriever | format_docs, "input": RunnablePassthrough()}
    | prompt_template
    | llm
    | StrOutputParser()
)

print("\n¡Chatbot de Normativa Universitario Listo!")
print("Escribe 'salir' para finalizar.\n" + "-"*50)

while True:
    user_input = input("\nEstudiante: ")
    if user_input.lower() == 'salir':
        break
        
    if user_input.strip() == "":
        continue

    print("Buscando en documentos y generando respuesta...")
    try:
        response = rag_chain.invoke(user_input)
        print(f"\nTutor: {response}")
    except Exception as e:
        print(f"\nOcurrió un error: {e}")