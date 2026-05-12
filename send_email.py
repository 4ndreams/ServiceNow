import os
import base64
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition
from datetime import datetime


def enviar_correo(destinatarios: list, asunto: str, html: str, url_reporte: str = "", fecha: str = ""):
    remitente = os.environ["EMAIL_SENDER"]
    api_key   = os.environ["SENDGRID_API_KEY"]
    fecha_fmt = fecha or datetime.now().strftime("%d/%m/%Y %H:%M")

    # Cuerpo del correo — liviano, con el link al dashboard
    cuerpo = f"""
    <html><body style="font-family:Segoe UI,Arial,sans-serif;background:#f5f5f5;padding:20px;margin:0">
    <div style="max-width:600px;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.1)">

      <div style="background:linear-gradient(135deg,#0c3c6e,#1a5fa8);color:#fff;padding:28px 32px">
        <div style="font-size:20px;margin-bottom:4px">📊 Reporte Semanal</div>
        <div style="font-size:16px;font-weight:600">Tickets Proyecto Workflow IT</div>
        <div style="font-size:13px;opacity:.8;margin-top:4px">AFP Capital · Ingeniería TI · {fecha_fmt}</div>
      </div>

      <div style="padding:28px 32px">
        <p style="color:#374151;font-size:15px;margin-bottom:20px">
          El reporte semanal ya está disponible con los datos actualizados de ServiceNow.
        </p>

        {"" if not url_reporte else f'''
        <div style="text-align:center;margin:24px 0">
          <a href="{url_reporte}"
             style="display:inline-block;background:#0c3c6e;color:#fff;text-decoration:none;
                    padding:14px 32px;border-radius:8px;font-size:15px;font-weight:600">
            Ver Dashboard Completo →
          </a>
          <div style="font-size:11px;color:#9ca3af;margin-top:8px">{url_reporte}</div>
        </div>
        '''}

        <div style="background:#f8fafc;border-radius:8px;padding:16px;margin:20px 0;border:1px solid #e5e7eb">
          <div style="font-size:11px;color:#6b7280;font-weight:600;text-transform:uppercase;letter-spacing:.5px;margin-bottom:10px">
            El dashboard incluye
          </div>
          <table style="width:100%;font-size:13px;color:#374151">
            <tr><td style="padding:4px 0">📊</td><td style="padding:4px 8px">Resumen ejecutivo — Volumetría y SLA 2025 vs 2026</td></tr>
            <tr><td style="padding:4px 0">🗂</td><td style="padding:4px 8px">Vista operativa por formulario con cuellos de botella</td></tr>
            <tr><td style="padding:4px 0">📋</td><td style="padding:4px 8px">Detalle de los tickets con mayor SLA por año</td></tr>
            <tr><td style="padding:4px 0">⏱</td><td style="padding:4px 8px">Análisis de tiempos por grupo resolutor y aprobadores</td></tr>
            <tr><td style="padding:4px 0">🚀</td><td style="padding:4px 8px">Impacto de automatización y mejora vs 2025</td></tr>
          </table>
        </div>

        <div style="margin-top:24px;padding-top:16px;border-top:1px solid #e5e7eb;font-size:11px;color:#9ca3af">
          Reporte generado automáticamente cada lunes. Datos extraídos directamente de ServiceNow.
        </div>
      </div>
    </div>
    </body></html>
    """

    msg = Mail(
        from_email=remitente,
        subject=f"{asunto} — {datetime.now().strftime('%d/%m/%Y')}",
        html_content=cuerpo,
        to_emails=destinatarios
    )

    sg = SendGridAPIClient(api_key)
    resp = sg.send(msg)
    print(f"✅ Correo enviado — Status: {resp.status_code}")
    print(f"   Destinatarios: {destinatarios}")
    print(f"   Link reporte: {url_reporte}")
