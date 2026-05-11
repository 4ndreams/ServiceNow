"""
send_email.py — Envía el reporte HTML por correo
Usa Gmail con contraseña de app (no requiere servicios externos pagados).
"""

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime


def enviar_correo(destinatarios: list, asunto: str, html: str):
    """
    Envía el reporte por correo.
    - El HTML se adjunta como archivo descargable
    - El cuerpo del correo incluye un resumen con los KPIs principales
    """

    remitente = os.environ["EMAIL_SENDER"]       # tu Gmail
    password  = os.environ["EMAIL_APP_PASSWORD"]  # contraseña de app de Gmail

    fecha = datetime.now().strftime("%d/%m/%Y")
    nombre_archivo = f"Reporte_WorkflowIT_{datetime.now().strftime('%Y%m%d')}.html"

    # Cuerpo del correo (resumen simple en HTML)
    cuerpo_html = f"""
    <html><body style="font-family: Segoe UI, sans-serif; background: #f5f5f5; padding: 20px;">
    <div style="max-width: 600px; margin: 0 auto; background: #fff; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,.1);">

      <div style="background: linear-gradient(135deg, #0c3c6e, #1a5fa8); color: #fff; padding: 24px 28px;">
        <h2 style="margin:0;font-size:18px">📊 Reporte Semanal — Tickets Proyecto Workflow IT</h2>
        <p style="margin:6px 0 0;opacity:.8;font-size:13px">AFP Capital · Ingeniería TI · {fecha}</p>
      </div>

      <div style="padding: 24px 28px;">
        <p style="color:#374151;font-size:14px">Hola,</p>
        <p style="color:#374151;font-size:14px">
          Se adjunta el reporte semanal actualizado con los datos más recientes de ServiceNow.
        </p>

        <div style="background:#f8fafc;border-radius:8px;padding:16px;margin:16px 0;border:1px solid #e5e7eb">
          <p style="font-size:12px;color:#6b7280;margin:0 0 8px;font-weight:600;text-transform:uppercase;letter-spacing:.5px">
            El reporte incluye
          </p>
          <ul style="color:#374151;font-size:13px;margin:0;padding-left:18px;line-height:1.8">
            <li>Comparativo de volumetría y SLA 2025 vs 2026</li>
            <li>Vista operativa por formulario con cuellos de botella</li>
            <li>Detalle de los 20 tickets con mayor SLA por año</li>
            <li>Análisis de tiempo de aprobación vs tiempo de tarea</li>
          </ul>
        </div>

        <p style="color:#374151;font-size:13px">
          Abre el archivo adjunto <strong>{nombre_archivo}</strong> en cualquier navegador para ver el dashboard interactivo.
        </p>

        <div style="margin-top:20px;padding-top:16px;border-top:1px solid #e5e7eb">
          <p style="font-size:11px;color:#9ca3af;margin:0">
            Este reporte se genera automáticamente cada lunes. Datos extraídos de ServiceNow.
          </p>
        </div>
      </div>
    </div>
    </body></html>
    """

    # Armar el mensaje
    msg = MIMEMultipart("mixed")
    msg["From"]    = remitente
    msg["To"]      = ", ".join(destinatarios)
    msg["Subject"] = f"{asunto} — {fecha}"

    # Adjuntar cuerpo
    msg.attach(MIMEText(cuerpo_html, "html"))

    # Adjuntar HTML del reporte
    adjunto = MIMEBase("text", "html")
    adjunto.set_payload(html.encode("utf-8"))
    encoders.encode_base64(adjunto)
    adjunto.add_header(
        "Content-Disposition",
        "attachment",
        filename=nombre_archivo
    )
    msg.attach(adjunto)

    # Enviar por Gmail SMTP
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(remitente, password)
        server.sendmail(remitente, destinatarios, msg.as_string())
