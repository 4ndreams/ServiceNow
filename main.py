import os
import json
from sn_fetch import fetch_all_data
from claude_report import generar_html
from send_email import enviar_correo

def main():
    print("🚀 Iniciando reporte semanal...")

    print("📡 Conectando a ServiceNow...")
    datos = fetch_all_data()
    print(f"✅ Descargados: {datos['total_ritm']} RITM")

    # DEBUG — ver qué datos llegan
    print("\n=== DEBUG DATOS ===")
    print(f"Años disponibles: {list(datos['ritm_por_anio'].keys())}")
    print(f"RITM por año: {datos['ritm_por_anio']}")
    print(f"SLA prom por año: {datos['sla_prom_por_anio']}")
    print(f"Meses disponibles: {list(datos['resumen_mes'].keys())[:6]}")
    print(f"Formularios: {list(datos['por_form_anio'].keys())}")
    print("=== FIN DEBUG ===\n")

    print("🤖 Generando reporte con Claude...")
    html = generar_html(datos)
    print("✅ HTML generado")

    with open("reporte_semanal.html", "w", encoding="utf-8") as f:
        f.write(html)

    print("📧 Enviando correo...")
    destinatarios = os.environ["EMAIL_RECIPIENTS"].split(",")
    enviar_correo(
        destinatarios=[d.strip() for d in destinatarios],
        asunto="Reporte Semanal — Tickets Proyecto Workflow IT",
        html=html
    )
    print("🎉 Reporte completado y enviado")

if __name__ == "__main__":
    main()
