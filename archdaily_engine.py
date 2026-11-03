"""
ArchDaily Studio Engine - Robust scraper and downloader for ArchDaily projects.
Does not require Selenium or ChromeDriver; uses direct HTTP requests and JSON gallery extraction.
"""

import os
import re
import json
import html
import time
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Callable, Any

DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
}

def sanitize_filename(name: str) -> str:
    """Sanitizes strings for safe Windows file and folder names."""
    if not name:
        return "archivo"
    # Remove illegal windows characters <>:"/\|?*
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '', name)
    cleaned = cleaned.strip('. ')
    return cleaned[:120] if cleaned else "archivo"

def parse_project_input(user_input: str) -> str:
    """
    Normalizes any ArchDaily input (ID, URL, query string) to a clean project URL.
    Examples:
      - '939894' -> 'https://www.archdaily.com/939894'
      - 'https://www.archdaily.com/939894/zuidplein-theatre...' -> 'https://www.archdaily.com/939894'
      - 'https://www.archdaily.pe/pe/939894/...' -> 'https://www.archdaily.com/939894'
    """
    cleaned = user_input.strip()
    if not cleaned:
        raise ValueError("Por favor introduce un enlace o código de proyecto de ArchDaily.")
    
    # Check if purely numeric
    if cleaned.isdigit():
        return f"https://www.archdaily.com/{cleaned}"
    
    # Extract ID from URL
    match = re.search(r'/(?:[a-z]{2}/)?(\d{5,8})(?:/|$|\?)', cleaned)
    if match:
        proj_id = match.group(1)
        return f"https://www.archdaily.com/{proj_id}"
    
    # If it's a full URL without numeric pattern match
    if cleaned.startswith(('http://', 'https://')):
        return cleaned
    
    # Fallback to ID
    digits = re.findall(r'\d+', cleaned)
    if digits:
        longest = max(digits, key=len)
        if len(longest) >= 5:
            return f"https://www.archdaily.com/{longest}"
            
    raise ValueError(f"No se pudo identificar un código o URL válido de ArchDaily en: '{user_input}'")

def translate_text(text: str, target_lang: str = "es") -> str:
    """Translates text reliably to the target language with chunking and multiple resilient endpoints."""
    if not text or not text.strip():
        return ""

    import urllib.request
    import urllib.parse

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': '*/*',
    }

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        paragraphs = [text.strip()]

    # Group paragraphs into chunks of ~1200 characters to prevent HTTP 414 / length limits
    chunks = []
    current_chunk = []
    current_len = 0
    for p in paragraphs:
        if current_len + len(p) + 2 > 1200:
            if current_chunk:
                chunks.append("\n\n".join(current_chunk))
                current_chunk = []
                current_len = 0
            if len(p) > 1200:
                # Split large single paragraph by sentence boundaries
                sentences = re.split(r'(?<=\. )', p)
                sub_p = ""
                for s in sentences:
                    if len(sub_p) + len(s) > 1200:
                        if sub_p.strip():
                            chunks.append(sub_p.strip())
                        sub_p = s
                    else:
                        sub_p += s
                if sub_p.strip():
                    chunks.append(sub_p.strip())
            else:
                current_chunk.append(p)
                current_len += len(p) + 2
        else:
            current_chunk.append(p)
            current_len += len(p) + 2

    if current_chunk:
        chunks.append("\n\n".join(current_chunk))

    translated_chunks = []
    for chunk in chunks:
        trans_res = None
        # Primary: Google dict-chrome-ex API (clean JSON, instant, highly reliable)
        try:
            url = f"https://clients5.google.com/translate_a/t?client=dict-chrome-ex&sl=auto&tl={target_lang}&q={urllib.parse.quote(chunk)}"
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=7) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                if isinstance(data, list) and len(data) > 0:
                    if isinstance(data[0], list) and len(data[0]) > 0:
                        trans_res = data[0][0]
                    elif isinstance(data[0], str):
                        trans_res = data[0]
        except Exception:
            pass

        # Fallback 1: Google gtx endpoint with browser headers
        if not trans_res:
            try:
                url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl={target_lang}&dt=t&q={urllib.parse.quote(chunk)}"
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=7) as resp:
                    data = json.loads(resp.read().decode('utf-8'))
                    if data and isinstance(data, list) and data[0]:
                        trans_res = "".join([part[0] for part in data[0] if part and part[0]]).strip()
            except Exception:
                pass

        # Fallback 2: MyMemory API
        if not trans_res:
            try:
                url = f"https://api.mymemory.translated.net/get?q={urllib.parse.quote(chunk[:500])}&langpair=auto|{target_lang}"
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=7) as resp:
                    data = json.loads(resp.read().decode('utf-8'))
                    if "responseData" in data and "translatedText" in data["responseData"]:
                        trans_res = data["responseData"]["translatedText"]
            except Exception:
                pass

        translated_chunks.append(trans_res if trans_res else chunk)

    return "\n\n".join(translated_chunks)

class ArchDailyProject:
    def __init__(self, raw_input: str):
        self.raw_input = raw_input
        self.url = parse_project_input(raw_input)
        self.project_id = ""
        self.title = ""
        self.architects = ""
        self.category = ""
        self.year = ""
        self.location = ""
        self.country = ""
        self.area = ""
        self.photographs = ""
        self.specs: Dict[str, str] = {}
        self.description_paragraphs: List[str] = []
        self.hero_image_url = ""
        self.gallery_items: List[Dict[str, Any]] = []
        self.plans_count = 0
        self.photos_count = 0
        
    def fetch_details(self, timeout: int = 15) -> bool:
        """Fetches the project metadata and gallery from ArchDaily."""
        session = requests.Session()
        session.headers.update(DEFAULT_HEADERS)
        
        response = session.get(self.url, timeout=timeout, allow_redirects=True)
        if response.status_code != 200:
            raise RuntimeError(f"Error {response.status_code} al acceder a ArchDaily: {self.url}")
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. Project ID
        id_match = re.search(r'/(\d{5,8})', response.url) or re.search(r'/(\d{5,8})', self.url)
        self.project_id = id_match.group(1) if id_match else "archdaily_project"
        
        # 2. Title
        h1 = soup.find('h1')
        if h1:
            self.title = h1.get_text(' ', strip=True)
        else:
            self.title = soup.title.string.strip() if soup.title else f"Proyecto {self.project_id}"
        self.title = re.sub(r'\s*\|\s*ArchDaily.*$', '', self.title, flags=re.IGNORECASE).strip()
        
        # 3. Clean specs
        self.specs = {}
        for item in soup.find_all(class_='afd-specs__item'):
            k_tag = item.find(class_='afd-specs__key')
            v_tag = item.find(class_='afd-specs__value')
            if k_tag and v_tag:
                key = k_tag.get_text(strip=True).rstrip(':').strip()
                val = v_tag.get_text(' ', strip=True)
                if key and val:
                    self.specs[key] = val
        
        # Map common fields
        self.architects = self.specs.get('Architects', '') or self.specs.get('Arquitectos', '')
        self.year = self.specs.get('Year', '') or self.specs.get('Año', '')
        self.area = self.specs.get('Area', '') or self.specs.get('Área', '')
        self.category = self.specs.get('Category', '') or self.specs.get('Categoría', '')
        self.photographs = self.specs.get('Photographs', '') or self.specs.get('Fotografías', '')
        
        city = self.specs.get('City', '') or self.specs.get('Ciudad', '')
        country = self.specs.get('Country', '') or self.specs.get('País', '')
        if city and country:
            self.location = f"{city}, {country}"
        elif city or country:
            self.location = city or country
        else:
            self.location = "Ubicación no especificada"
            
        # 4. Narrative / Description
        raw_paragraphs = []
        article = soup.find('article', class_='afd-post-content') or soup.find(class_='afd-post-content')
        if article:
            for p in article.find_all('p'):
                txt = p.get_text(strip=True)
                if len(txt) > 20 and not txt.startswith("You'll now receive updates") and not txt.startswith("Curated by"):
                    raw_paragraphs.append(txt)
        
        # Deduplicate while preserving order
        self.description_paragraphs = []
        seen = set()
        for p in raw_paragraphs:
            if p not in seen:
                seen.add(p)
                self.description_paragraphs.append(p)
                
        self.description_spanish_paragraphs: List[str] = []
        # Pre-translate to Spanish
        self.translate_description(target_lang="es")
        
        # 5. Gallery items extraction
        self._fetch_gallery(session, soup, timeout)
        
        return True

    def translate_description(self, target_lang: str = "es", force: bool = False) -> str:
        """Translates the project description into Spanish (or target language)."""
        if not self.description_paragraphs:
            return ""
        if self.description_spanish_paragraphs and not force:
            return "\n\n".join(self.description_spanish_paragraphs)
            
        full_text = "\n\n".join(self.description_paragraphs)
        try:
            translated = translate_text(full_text, target_lang=target_lang)
            if translated and translated.strip():
                self.description_spanish_paragraphs = [p.strip() for p in translated.split("\n\n") if p.strip()]
                return "\n\n".join(self.description_spanish_paragraphs)
        except Exception as e:
            print(f"Translation notice: {e}")
            
        return full_text

    def _fetch_gallery(self, session: requests.Session, soup: BeautifulSoup, timeout: int):
        """Locates the gallery subpage and decodes the complete data-images JSON array."""
        self.gallery_items = []
        
        # Find gallery sublink in the page
        gallery_url = None
        for a in soup.find_all('a', href=True):
            href = a['href']
            # ArchDaily gallery sublinks match /{id}/{slug}/{hex_id}-{slug}-{photo|plan}
            if re.search(r'/\d{5,8}/[^/]+/[0-9a-f]{24}-', href):
                gallery_url = href
                break
                
        if gallery_url:
            if not gallery_url.startswith('http'):
                gallery_url = 'https://www.archdaily.com' + gallery_url
                
            try:
                r_gal = session.get(gallery_url, timeout=timeout)
                if r_gal.status_code == 200:
                    soup_gal = BeautifulSoup(r_gal.text, 'html.parser')
                    gal_tag = soup_gal.find(id='gallery-items')
                    if gal_tag and gal_tag.get('data-images'):
                        raw_json = html.unescape(gal_tag['data-images'])
                        self.gallery_items = json.loads(raw_json)
            except Exception as e:
                print(f"Error fetching gallery JSON: {e}")
                
        # Fallback if no sublink or JSON found: harvest all adsttc images in page
        if not self.gallery_items:
            img_urls = set(re.findall(r'https?://images\.adsttc\.com/media/images/[a-f0-9]{24}/(?:large_jpg|medium_jpg|slideshow)/[^\s"\'<>]+\.jpg', str(soup)))
            for idx, u in enumerate(img_urls):
                clean_url = u.split('?')[0]
                self.gallery_items.append({
                    "url_large": clean_url,
                    "url_medium": clean_url.replace('/large_jpg/', '/medium_jpg/'),
                    "type": "MediaPlan" if "plan" in clean_url.lower() or "drawings" in clean_url.lower() else "MediaPicture",
                    "caption": f"Imagen {idx+1}",
                    "image_alt": f"{self.title} - Imagen {idx+1}"
                })
                
        # Count plans and photos
        self.plans_count = sum(1 for it in self.gallery_items if it.get('type') == 'MediaPlan')
        self.photos_count = len(self.gallery_items) - self.plans_count
        
        # Select hero cover image
        if self.gallery_items:
            first = self.gallery_items[0]
            self.hero_image_url = first.get('url_medium') or first.get('url_large') or ""

    def get_dossier_text(self) -> str:
        """Formats an architectural project dossier text."""
        sep = "=" * 70
        sub_sep = "-" * 70
        lines = [
            sep,
            f" ARCHDAILY PROJECT DOSSIER // FICHA ARQUITECTÓNICA",
            sep,
            f"Proyecto:    {self.title}",
            f"Código ID:   {self.project_id}",
            f"Arquitectos: {self.architects or 'No especificado'}",
            f"Ubicación:   {self.location}",
            f"Año:         {self.year or 'No especificado'}",
            f"Área:        {self.area or 'No especificado'}",
            f"Tipología:   {self.category or 'No especificado'}",
            f"Fotografías: {self.photographs or 'No especificado'}",
            f"Enlace Web:  {self.url}",
            sub_sep,
            " ESPECIFICACIONES TÉCNICAS COMPLETAS:",
            sub_sep,
        ]
        for k, v in self.specs.items():
            lines.append(f" • {k}: {v}")
            
        if self.description_spanish_paragraphs:
            lines.extend([
                sub_sep,
                " MEMORIA DESCRIPTIVA (ESPAÑOL):",
                sub_sep,
            ])
            for p in self.description_spanish_paragraphs:
                lines.append(p)
                lines.append("")

        lines.extend([
            sub_sep,
            " MEMORIA DESCRIPTIVA (TEXTO ORIGINAL):",
            sub_sep,
        ])
        if self.description_paragraphs:
            for p in self.description_paragraphs:
                lines.append(p)
                lines.append("")
        else:
            lines.append("No se encontró texto descriptivo detallado.")
            
        lines.extend([
            sub_sep,
            f"TOTAL DE ARCHIVOS EN GALERÍA: {len(self.gallery_items)}",
            f" • Fotografías:                 {self.photos_count}",
            f" • Planos y Dibujos Técnicos:  {self.plans_count}",
            sep,
        ])
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "Project ID": self.project_id,
            "Project Title": self.title,
            "Architects": self.architects,
            "Location": self.location,
            "Year": self.year,
            "Area": self.area,
            "Category": self.category,
            "Photographs": self.photographs,
            "URL": self.url,
            "Specifications": self.specs,
            "Description": self.description_paragraphs,
            "Description_Spanish": self.description_spanish_paragraphs,
            "Total Items": len(self.gallery_items),
            "Photos Count": self.photos_count,
            "Plans Count": self.plans_count,
            "Gallery": self.gallery_items
        }

class ProjectDownloader:
    def __init__(
        self,
        project: ArchDailyProject,
        dest_folder: str,
        quality: str = "original", # "original", "large", "slideshow"
        download_photos: bool = True,
        download_plans: bool = True,
        separate_folders: bool = True,
        save_dossier: bool = True,
        max_threads: int = 4,
        on_progress: Optional[Callable[[int, int, str, float], None]] = None,
        on_status: Optional[Callable[[str], None]] = None
    ):
        self.project = project
        self.dest_folder = dest_folder
        self.quality = quality
        self.download_photos = download_photos
        self.download_plans = download_plans
        self.separate_folders = separate_folders
        self.save_dossier = save_dossier
        self.max_threads = max(1, min(max_threads, 8))
        self.on_progress = on_progress
        self.on_status = on_status
        self.is_cancelled = False
        
    def cancel(self):
        self.is_cancelled = True
        
    def _resolve_image_url(self, item: Dict[str, Any], session: requests.Session) -> str:
        url_large = item.get('url_large', '')
        if not url_large:
            return item.get('url_medium', '')
            
        if self.quality == "original":
            # Attempt original resolution
            url_original = url_large.replace('/large_jpg/', '/original/')
            try:
                res = session.head(url_original, timeout=5)
                if res.status_code == 200:
                    return url_original
            except Exception:
                pass
            return url_large
        elif self.quality == "slideshow":
            return item.get('url_slideshow') or url_large.replace('/large_jpg/', '/slideshow/')
        else: # "large"
            return url_large

    def run(self) -> str:
        """Executes the download process. Returns the project directory path."""
        # 1. Base project directory
        folder_name = sanitize_filename(f"[{self.project.project_id}] {self.project.title}")
        project_dir = os.path.join(self.dest_folder, folder_name)
        os.makedirs(project_dir, exist_ok=True)
        
        # 2. Subdirectories
        if self.separate_folders:
            plans_dir = os.path.join(project_dir, "01_Planos_y_Dibujos")
            photos_dir = os.path.join(project_dir, "02_Fotografias")
            os.makedirs(plans_dir, exist_ok=True)
            os.makedirs(photos_dir, exist_ok=True)
        else:
            plans_dir = project_dir
            photos_dir = project_dir
            
        # 3. Save Dossier & JSON
        if self.save_dossier:
            if self.on_status:
                self.on_status("Generando memoria descriptiva y ficha técnica...")
            dossier_path = os.path.join(project_dir, "MEMORIA_DESCRIPTIVA.txt")
            with open(dossier_path, 'w', encoding='utf-8') as f:
                f.write(self.project.get_dossier_text())
                
            json_path = os.path.join(project_dir, "ficha_proyecto.json")
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(self.project.to_dict(), f, indent=2, ensure_ascii=False)
                
        # 4. Filter items
        tasks = []
        plan_idx = 1
        photo_idx = 1
        
        for item in self.project.gallery_items:
            is_plan = (item.get('type') == 'MediaPlan')
            if is_plan and not self.download_plans:
                continue
            if not is_plan and not self.download_photos:
                continue
                
            if is_plan:
                target_dir = plans_dir
                num_prefix = f"PLANO_{plan_idx:03d}"
                plan_idx += 1
            else:
                target_dir = photos_dir
                num_prefix = f"FOTO_{photo_idx:03d}"
                photo_idx += 1
                
            # Descriptive filename
            alt_name = item.get('caption') or item.get('image_alt') or "detalle"
            # Extract simple name from alt
            alt_name = re.sub(r'^[^-]+-\s*', '', alt_name).strip()
            clean_label = sanitize_filename(alt_name)[:45]
            filename = f"{num_prefix}_{clean_label}.jpg"
            save_path = os.path.join(target_dir, filename)
            
            tasks.append((item, save_path, filename))
            
        total_files = len(tasks)
        if total_files == 0:
            if self.on_status:
                self.on_status("No se seleccionaron archivos para descargar.")
            return project_dir
            
        completed = 0
        session = requests.Session()
        session.headers.update(DEFAULT_HEADERS)
        
        if self.on_status:
            self.on_status(f"Iniciando descarga de {total_files} archivos...")
            
        def download_single(task):
            if self.is_cancelled:
                return None
            item, target_path, fname = task
            # If already exists and size > 10KB, skip re-download
            if os.path.exists(target_path) and os.path.getsize(target_path) > 10240:
                return fname
                
            img_url = self._resolve_image_url(item, session)
            r = session.get(img_url, stream=True, timeout=20)
            if r.status_code == 200:
                with open(target_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=65536):
                        if self.is_cancelled:
                            break
                        if chunk:
                            f.write(chunk)
                return fname
            return None

        with ThreadPoolExecutor(max_workers=self.max_threads) as executor:
            future_to_task = {executor.submit(download_single, task): task for task in tasks}
            for future in as_completed(future_to_task):
                if self.is_cancelled:
                    if self.on_status:
                        self.on_status("Descarga cancelada por el usuario.")
                    break
                completed += 1
                task = future_to_task[future]
                fname = task[2]
                percent = (completed / total_files) * 100.0
                if self.on_progress:
                    self.on_progress(completed, total_files, fname, percent)
                if self.on_status:
                    self.on_status(f"Descargando [{completed}/{total_files}]: {fname}")
                    
        if not self.is_cancelled and self.on_status:
            self.on_status(f"¡Descarga completada con éxito! ({completed}/{total_files} archivos guardados)")
            
        return project_dir
