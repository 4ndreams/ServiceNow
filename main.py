import os
from sn_fetch import fetch_all_data
from claude_report import generar_html
from send_email import enviar_correo

def main():
    print("🚀 Iniciando reporte semanal...")

    print("📡 Conectando a ServiceNow...")
    datos = fetch_all_data()
    print(f"✅ Descargados: {datos['total_ritm']} RITM")

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
