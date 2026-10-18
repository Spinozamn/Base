# Base: Sistema de Orientación y Consulta Normativa Institucional

Sistema de asesoría y orientación automatizada basado en RAG (Retrieval-Augmented Generation) para la **Universidad de Guadalajara (UdeG)**, contextualizado especialmente para estudiantes de la carrera de **Ingeniería en Ciencias Computacionales (ICC)** en el **Centro Universitario de Tonalá (CUTonalá)**.

El sistema se enfoca en la resolución de situaciones de **relaciones con la autoridad**, prevención de **conflicto de interés** (vínculos sentimentales o personales docente-alumno), **derechos estudiantiles**, **asimetría de poder**, impugnación y revisión objetiva de calificaciones, y canalización directa ante instancias como la Defensoría de los Derechos Universitarios (DDU) y la Coordinación de Carrera.

**Responsable del Proyecto:** José Manuel Espinoza Romero  
**Institución:** Universidad de Guadalajara — CUTonalá  
**Fecha:** Octubre de 2026  

---

## Características Principales

1. **Rigor Normativo y Cero Alucinación:**  
   Funciona con `temperature=0.0` y recuperación vectorial estricta (FAISS) fundamentada exclusivamente en la documentación oficial aprobada.
2. **Estructura Documental en 3 Núcleos (`conocimientos/`):**
   * `01_informacion_personal.md`: Guía estudiantil, casuística, catálogo de profesores de confianza y autoridades en CUTonalá.
   * `02_marco_legal_mexicano.md`: Constitución Política (Art. 1° y 3°), Ley General de Acceso de las Mujeres a una Vida Libre de Violencia, Código Penal y Ley Olimpia.
   * `03_normativa_institucional_udg.md`: Código de Ética (Dictamen IV/2018/117), Código de Conducta (Dictamen IV/2021/514), Protocolo PPASE de Violencia de Género y Reglamento General de Evaluación y Promoción de Alumnos (Arts. 49-52 RGEPA).
3. **Resiliencia Automática Multi-Modelo:**  
   Motor configurado con `gemini-3.5-flash` como modelo principal (alta cuota diaria) y respaldo automático instantáneo en `gemini-3.5-flash-lite` y `gemini-3.8-flash` para garantizar disponibilidad continua.
4. **Interfaz de Usuario Telegram-Style:**  
   Diseño sobrio en escala de grises con botones de consulta rápida para las 6 dimensiones clave:
   * Encargado y ubicación en CUTonalá.
   * Vías de contacto y extensiones oficiales.
   * Explicación del programa de atención y medidas cautelares.
   * Justificación técnica del caso (conflicto de interés y asimetría de poder).
   * Asesoría y apoyos de la Coordinación de Carrera.
   * Gestión modal de la Clave de API de Google Gemini en local.

---

## Estructura del Repositorio

```text
Base/
├── conocimientos/
│   ├── 01_informacion_personal.md       # Datos de CUTonalá, ICC, catálogo de maestros y notas de apoyo
│   ├── 02_marco_legal_mexicano.md       # Marco jurídico federal y estatal aplicable
│   └── 03_normativa_institucional_udg.md# Reglamentos, códigos y protocolos oficiales de la UdeG
├── interfaz.html                        # Interfaz gráfica local estilo Telegram (HTML5/CSS3/Vanilla JS)
├── servidor.py                          # Servidor HTTP y cadena RAG con LangChain, FAISS y Gemini
├── app_adaptada.py                      # Versión interactiva para ejecución en consola de terminal
├── prueba_humo.py                       # Suite de prueba de humo (smoke test) para verificación de salud
├── requirements.txt                     # Dependencias de Python requeridas
├── .env.example                         # Plantilla de variables de entorno
├── iniciar.bat                          # Lanzador automático con doble clic para Windows
├── iniciar_mac.command                  # Lanzador automático con doble clic para macOS
└── README.md                            # Documentación del proyecto
```

---

## Instalación y Puesta en Marcha

### Prerrequisitos
* Python 3.10 o superior instalado.
* Conexión a internet y una Clave de API de Google Gemini ([Google AI Studio](https://aistudio.google.com/)).

### Pasos de Instalación

1. **Clonar el repositorio:**
   ```bash
   git clone <URL_DEL_REPOSITORIO> Base
   cd Base
   ```

2. **Crear y activar entorno virtual:**
   * En Windows:
     ```bash
     python -m venv venv
     .\venv\Scripts\activate
     ```
   * En Linux / macOS:
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```

3. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configurar la Clave de API:**
   Copia el archivo `.env.example` a `.env` y agrega tu clave:
   ```env
   GOOGLE_API_KEY=tu_clave_de_gemini_aqui
   ```
   *(También puedes ingresar la clave directamente desde el botón "Clave API" en la interfaz web).*

5. **Iniciar el Asistente:**
   * En Windows: Doble clic en `iniciar.bat` o ejecuta:
     ```bash
     python servidor.py
     ```
   * En macOS: Doble clic en `iniciar_mac.command` o ejecuta:
     ```bash
     python3 servidor.py
     ```
   El sistema abrirá automáticamente el navegador en `http://127.0.0.1:8000`.

---

## Verificación del Sistema (Prueba de Humo)

El proyecto incluye un script de diagnóstico integral para verificar la integridad de los documentos, el estado de los modelos de IA y todos los casos de uso:

```bash
python prueba_humo.py
```
El reporte validará los 10 puntos de control del sistema (servidor, endpoints, respuestas normativas y desvío amable).
