import os
import base64
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition
from datetime import datetime


def enviar_correo(destinatarios: list, asunto: str, html: str):
    remitente = os.environ["EMAIL_SENDER"]
    api_key   = os.environ["SENDGRID_API_KEY"]
    fecha     = datetime.now().strftime("%d/%m/%Y")
    nombre    = f"Reporte_WorkflowIT_{datetime.now().strftime('%Y%m%d')}.html"

    cuerpo = f"""
    <html><body style="font-family:Segoe UI,sans-serif;background:#f5f5f5;padding:20px">
    <div style="max-width:600px;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.1)">
      <div style="background:linear-gradient(135deg,#0c3c6e,#1a5fa8);color:#fff;padding:24px 28px">
        <h2 style="margin:0;font-size:18px">Reporte Semanal — Tickets Proyecto Workflow IT</h2>
        <p style="margin:6px 0 0;opacity:.8;font-size:13px">AFP Capital · Ingeniería TI · {fecha}</p>
      </div>
      <div style="padding:24px 28px">
        <p style="color:#374151;font-size:14px">Hola,</p>
        <p style="color:#374151;font-size:14px">Se adjunta el reporte semanal actualizado con los datos más recientes de ServiceNow.</p>
        <div style="background:#f8fafc;border-radius:8px;padding:16px;margin:16px 0;border:1px solid #e5e7eb">
          <p style="font-size:12px;color:#6b7280;margin:0 0 8px;font-weight:600;text-transform:uppercase">El reporte incluye</p>
          <ul style="color:#374151;font-size:13px;margin:0;padding-left:18px;line-height:1.8">
            <li>Comparativo volumetría y SLA {datetime.now().year-1} vs {datetime.now().year}</li>
            <li>Vista operativa por formulario con cuellos de botella</li>
            <li>Detalle de los 20 tickets con mayor SLA por año</li>
            <li>Análisis tiempo de aprobación vs tiempo de tarea</li>
          </ul>
        </div>
        <p style="color:#374151;font-size:13px">Abre el archivo adjunto <strong>{nombre}</strong> en tu navegador para ver el dashboard interactivo.</p>
        <div style="margin-top:20px;padding-top:16px;border-top:1px solid #e5e7eb">
          <p style="font-size:11px;color:#9ca3af;margin:0">Reporte generado automáticamente cada lunes. Datos extraídos de ServiceNow.</p>
        </div>
      </div>
    </div>
    </body></html>
    """

    adjunto = Attachment(
        FileContent(base64.b64encode(html.encode("utf-8")).decode()),
        FileName(nombre),
        FileType("text/html"),
        Disposition("attachment")
    )

    msg = Mail(from_email=remitente, subject=f"{asunto} — {fecha}", html_content=cuerpo)
    msg.to = destinatarios
    msg.attachment = adjunto

    sg = SendGridAPIClient(api_key)
    resp = sg.send(msg)
    print(f"✅ Correo enviado — Status: {resp.status_code}")
