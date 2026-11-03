# ArchDaily Studio Downloader 🏛️

[![Release](https://img.shields.io/badge/Release-v1.0-blue.svg)](https://github.com/WolfStep-vive/ArchDaily-Studio-Downloader/releases)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-black.svg)]()
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)]()
[![License](https://img.shields.io/badge/License-MIT-green.svg)]()

> **Herramienta de investigación y archivo para arquitectos, urbanistas y diseñadores.**
> Descarga planos en máxima resolución original, clasifica fotografías de obra y traduce automáticamente la memoria descriptiva al español con un clic.

---

## ✨ Características Principales

- 📐 **Planos en Alta Resolución:** Extrae planos técnicos, cortes, elevaciones, axonométricas y diagramas en su resolución nativa original sin compresión.
- 📸 **Fotografías Clasificadas:** Separa automáticamente en carpetas independientes los `Planos` de las `Fotografías de Obra`.
- 🌐 **Memoria Descriptiva Bilingüe:** Traduce la ficha técnica y memoria arquitectónica al español con soporte para retraducción instantánea y copiado al portapapeles.
- 📑 **Dossier del Proyecto:** Genera automáticamente un archivo `.txt` y `.md` con todos los metadatos: arquitectos, año, área, ubicación y descripción completa.
- 🪟 **Interfaz Minimalista Liquid Glass:** Diseño moderno y limpio, tipografía monoespaciada/sans técnica, sin publicidad ni elementos invasivos.
- ⚡ **100% Portable:** Ejecutable único de solo ~17 MB sin instaladores ni dependencias externas.

---

## 🚀 Descarga Rápida (Windows)

Descarga la última versión ejecutable desde la sección de **[Releases](https://github.com/WolfStep-vive/ArchDaily-Studio-Downloader/releases)**:

1. Descarga **`ArchDaily_Studio_Downloader_v1.0.zip`**.
2. Descomprime el archivo en cualquier carpeta.
3. Ejecuta **`ArchDaily_Studio_Downloader.exe`**.

> **Nota sobre Windows SmartScreen:**  
> Al ser un ejecutable independiente de código abierto, la primera vez que lo abras Windows podría mostrar una ventana azul de protección. Solo haz clic en **"Más información"** ➔ **"Ejecutar de todas formas"**.

---

## 🛠️ Ejecución desde el Código Fuente

Si deseas ejecutar o modificar el código fuente en Python:

### Requisitos
- Python 3.10 o superior

### Instalación
```bash
# Clonar el repositorio
git clone https://github.com/WolfStep-vive/ArchDaily-Studio-Downloader.git
cd ArchDaily-Studio-Downloader

# Instalar dependencias
pip install -r requirements.txt

# Iniciar la aplicación
python main.py
```

### Compilar el Ejecutable (.exe)
```bash
python -m PyInstaller ArchDaily_Studio_Downloader.spec
```

---

## 📂 Estructura del Proyecto

```text
├── archdaily_engine.py      # Motor de extracción HTTP y procesamiento de imágenes y traducciones
├── webview_app.py           # Puente nativo pywebview y API JavaScript
├── main.py                  # Punto de entrada de la aplicación
├── ui/                      # Interfaz gráfica moderna (HTML5, CSS3, JS)
│   └── index.html
├── icon.ico                 # Icono monocromático minimalista
├── requirements.txt         # Dependencias Python
└── ArchDaily_Studio_Downloader.spec # Configuración PyInstaller optimizada con UPX
```

---

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Consulta el archivo `LICENSE` para más detalles.

---

## 🙏 Créditos y Reconocimientos / Credits

Este proyecto está inspirado y basado en la idea original de **[Bahram Jannesar](https://github.com/BahramJannesar)** ([ArchdailyProjectDownloader](https://github.com/BahramJannesar/ArchdailyProjectDownloader)).

Agradecimiento especial al autor original por el concepto de recopilación de proyectos. Esta edición (**ArchDaily Studio Downloader**) rediseña y potencia la herramienta con:
- **Nueva interfaz de usuario:** Diseño moderno de escritorio con estética *Liquid Glass* y experiencia fluida pensada para arquitectos.
- **Sin Selenium ni ChromeDrivers:** Motor de red directo, ultra ligero y con descargas multihilo simultáneas.
- **Traducción bilingüe integrada:** Traducción automática de memorias descriptivas al español con botón interactivo de retraducción.
- **Clasificación inteligente:** Separación de planos técnicos y fotografías en alta resolución.
- **Distribución portable:** Binario optimizado y firmado para Windows de solo 17 MB.
