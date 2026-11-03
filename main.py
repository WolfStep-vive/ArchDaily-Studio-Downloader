"""
ArchDaily Studio Downloader - Minimalist Architecture Edition.
Ultra-lightweight entry point.
"""

import sys
import os

def run():
    # If launched with CLI arguments
    if len(sys.argv) > 1 and sys.argv[1] not in ["--gui", "-g"]:
        from archdaily_engine import ArchDailyProject, ProjectDownloader
        arg = sys.argv[1]
        if arg in ["--help", "-h"]:
            print("ArchDaily Studio Downloader (Minimalist Edition)")
            print("Uso:")
            print("  ArchDaily_Studio_Downloader.exe                  (Inicia la Interfaz Minimalista)")
            print("  ArchDaily_Studio_Downloader.exe <URL_o_ID>       (Descarga por consola)")
            return
        
        print(f"[ArchDaily Studio] Analizando proyecto: {arg}")
        proj = ArchDailyProject(arg)
        proj.fetch_details()
        print(f"Proyecto: {proj.title}")
        print(f"Arquitectos: {proj.architects}")
        print(f"Total archivos: {len(proj.gallery_items)} ({proj.plans_count} planos, {proj.photos_count} fotos)")
        
        dest = os.path.join(os.path.expanduser("~"), "Downloads", "ArchDaily_Studio")
        dl = ProjectDownloader(
            proj,
            dest,
            quality="original",
            on_progress=lambda cur, tot, fn, pct: print(f"[{cur}/{tot}] ({pct:.0f}%): {fn}"),
            on_status=lambda msg: print(f"-> {msg}")
        )
        out = dl.run()
        print(f"Completado en: {out}")
    else:
        from webview_app import run_app
        run_app()

if __name__ == "__main__":
    run()
