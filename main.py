"""
main.py — Orquestador del reporte semanal
Llama a ServiceNow, procesa los datos, genera el HTML con Claude y manda el correo.
"""

import os
from sn_fetch import fetch_all_data
from claude_report import generar_html
from send_email import enviar_correo

def main():
    print("🚀 Iniciando reporte semanal...")

    # 1. Descargar datos de ServiceNow
    print("📡 Conectando a ServiceNow...")
    datos = fetch_all_data()
    print(f"✅ Descargados: {datos['total_ritm']} RITM, {datos['total_tasks']} tareas, {datos['total_approvals']} aprobaciones")

    # 2. Generar HTML con Claude
    print("🤖 Generando reporte con Claude...")
    html = generar_html(datos)
    print("✅ HTML generado")

    # 3. Guardar HTML localmente (opcional, para debug)
    with open("reporte_semanal.html", "w", encoding="utf-8") as f:
        f.write(html)

    # 4. Enviar correo
    print("📧 Enviando correo...")
    destinatarios = os.environ["EMAIL_RECIPIENTS"].split(",")
    enviar_correo(
        destinatarios=destinatarios,
        asunto="📊 Reporte Semanal — Tickets Proyecto Workflow IT",
        html=html
    )
    print("✅ Correo enviado a:", destinatarios)
    print("🎉 Reporte completado exitosamente")

if __name__ == "__main__":
    main()
