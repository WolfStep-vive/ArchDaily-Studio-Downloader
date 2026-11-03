"""
ArchDaily Studio Downloader - Apple Liquid Glass & Modern Architecture Edition.
PyWebView + Edge WebView2 Backend Bridge.
"""

import os
import sys
import json
import threading
import subprocess
import webview
from typing import Dict, Any

from archdaily_engine import ArchDailyProject, ProjectDownloader

def get_asset_path(relative_path: str) -> str:
    """Gets absolute path to bundled resource (works in dev and PyInstaller)."""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

class StudioAPI:
    def __init__(self):
        self._window = None
        self.current_project: ArchDailyProject = None
        self.downloader: ProjectDownloader = None
        self.default_dir = os.path.join(os.path.expanduser("~"), "Downloads", "ArchDaily_Studio")
        os.makedirs(self.default_dir, exist_ok=True)

    def set_window(self, window):
        self._window = window

    def get_default_folder(self) -> str:
        return self.default_dir

    def get_clipboard(self) -> str:
        try:
            # Use PowerShell to grab clipboard without opening heavy GUI windows
            cmd = "Get-Clipboard -Raw"
            p = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True, timeout=2)
            if p.returncode == 0:
                return p.stdout.strip()
        except Exception as e:
            print("Clipboard error:", e)
        return ""

    def select_folder(self) -> str:
        if not self._window:
            return ""
        result = self._window.create_file_dialog(
            dialog_type=webview.FOLDER_DIALOG,
            directory=self.default_dir
        )
        if result and len(result) > 0:
            return result[0]
        return ""

    def open_folder(self, folder_path: str):
        if folder_path and os.path.exists(folder_path):
            os.startfile(folder_path)

    def fetch_project_data(self, user_input: str) -> Dict[str, Any]:
        proj = ArchDailyProject(user_input)
        proj.fetch_details()
        self.current_project = proj

        desc_orig = ""
        if proj.description_paragraphs:
            desc_orig = "\n\n".join(proj.description_paragraphs)
            
        desc_es = ""
        if proj.description_spanish_paragraphs:
            desc_es = "\n\n".join(proj.description_spanish_paragraphs)
        else:
            desc_es = desc_orig

        return {
            "project_id": proj.project_id,
            "title": proj.title,
            "architects": proj.architects,
            "location": proj.location,
            "year": proj.year,
            "area": proj.area,
            "category": proj.category,
            "photographs": proj.photographs,
            "hero_image_url": proj.hero_image_url,
            "plans_count": proj.plans_count,
            "photos_count": proj.photos_count,
            "total_count": len(proj.gallery_items),
            "description_original": desc_orig,
            "description_es": desc_es
        }

    def translate_custom_text(self, text: str, target_lang: str = "es") -> str:
        if not text or not text.strip():
            return ""
        try:
            from archdaily_engine import translate_text
            res = translate_text(text, target_lang=target_lang)
            if self.current_project and target_lang == "es" and res:
                self.current_project.description_spanish_paragraphs = [p.strip() for p in res.split("\n\n") if p.strip()]
            return res
        except Exception as e:
            print("Translation error:", e)
            return text

    def start_download(self, opts: Dict[str, Any]):
        if not self.current_project:
            return

        dest = opts.get("dest_folder") or self.default_dir
        quality = opts.get("quality", "original")
        download_plans = opts.get("download_plans", True)
        download_photos = opts.get("download_photos", True)
        separate_folders = opts.get("separate_folders", True)
        save_dossier = opts.get("save_dossier", True)

        def on_prog(cur, tot, fn, pct):
            if self._window:
                payload = json.dumps({"current": cur, "total": tot, "filename": fn, "percent": pct})
                self._window.evaluate_js(f"window.onProgress({payload});")

        def on_stat(msg):
            if self._window:
                escaped = json.dumps(msg)
                self._window.evaluate_js(f"window.onStatus({escaped});")

        self.downloader = ProjectDownloader(
            project=self.current_project,
            dest_folder=dest,
            quality=quality,
            download_photos=download_photos,
            download_plans=download_plans,
            separate_folders=separate_folders,
            save_dossier=save_dossier,
            max_threads=4,
            on_progress=on_prog,
            on_status=on_stat
        )

        def worker():
            try:
                out_dir = self.downloader.run()
                if self._window:
                    escaped_dir = json.dumps(out_dir)
                    self._window.evaluate_js(f"window.onDownloadFinished({escaped_dir});")
            except Exception as e:
                if self._window:
                    err_msg = json.dumps(str(e))
                    self._window.evaluate_js(f"window.onDownloadError({err_msg});")

        threading.Thread(target=worker, daemon=True).start()

    def cancel_download(self):
        if self.downloader:
            self.downloader.cancel()

def run_app():
    api = StudioAPI()
    html_path = get_asset_path(os.path.join("ui", "index.html"))

    # Configure modern window
    window = webview.create_window(
        title="ArchDaily // Studio Downloader",
        url=html_path,
        js_api=api,
        width=1080,
        height=820,
        min_size=(920, 680),
        background_color="#08090b"
    )
    api.set_window(window)

    # Start Edge WebView2 engine with GPU acceleration
    webview.start(debug=False)

if __name__ == "__main__":
    run_app()
