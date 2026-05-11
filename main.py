"""
main.py — Orquestador del reporte semanal
"""

import os
from sn_fetch import fetch_all_data
from claude_report import generar_html

def main():
    print("🚀 Iniciando reporte semanal...")

    # 1. Descargar datos de ServiceNow
    print("📡 Conectando a ServiceNow...")
    datos = fetch_all_data()
    print(f"✅ Descargados: {datos['total_ritm']} RITM")

    # 2. Generar HTML con Claude
    print("🤖 Generando reporte con Claude...")
    html = generar_html(datos)
    print("✅ HTML generado")

    # 3. Guardar HTML (lo toma GitHub Actions como artefacto)
    with open("reporte_semanal.html", "w", encoding="utf-8") as f:
        f.write(html)

    print("🎉 Reporte guardado como reporte_semanal.html")

if __name__ == "__main__":
    main()
