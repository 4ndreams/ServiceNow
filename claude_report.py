"""
claude_report.py — Genera el HTML del reporte usando Claude API
"""

import os
import json
import anthropic

def generar_html(datos: dict) -> str:
    """Le pasa los datos a Claude y le pide que genere el HTML completo del reporte."""

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    # Preparar resumen de datos para Claude (sin enviar todo el detalle raw)
    anio_a = datos["anio_actual"]
    anio_p = datos["anio_anterior"]

    resumen = {
        "fecha_generacion": datos["fecha_generacion"],
        "anio_actual": anio_a,
        "anio_anterior": anio_p,
        "total_ritm_por_anio": datos["ritm_por_anio"],
        "sla_promedio_por_anio": datos["sla_prom_por_anio"],
        "sla_tarea_promedio_por_anio": datos["sla_tarea_prom_por_anio"],
        "sla_aprobacion_promedio_por_anio": datos["sla_aprob_prom_por_anio"],
        "volumetria_y_sla_mensual": datos["resumen_mes"],
        "por_formulario": {
            form: {
                anio: {
                    "volumen": info["vol"],
                    "sla_promedio": info["sla"],
                    "top3_cuellos": [
                        {
                            "ritm": r["numero"],
                            "sla_total": r["sla"],
                            "sla_tarea": r["sla_tarea"],
                            "sla_aprobacion": r["sla_aprob"],
                            "grupo": r["grupo"],
                            "estado_tarea": r["estado_tarea"],
                            "estado_aprobacion": r["estado_aprob"],
                            "cuello": r["cuello"],
                            "mes": r["mes"],
                        }
                        for r in info["top3"]
                    ]
                }
                for anio, info in anios.items()
            }
            for form, anios in datos["por_form_anio"].items()
        },
        "top20_cuellos_anio_actual": [
            {
                "ritm": r["numero"],
                "formulario": r["elemento"],
                "etapa": r["etapa"],
                "solicitante": r["solicitante"],
                "mes": r["mes"],
                "sla_total": r["sla"],
                "sla_tarea": r["sla_tarea"],
                "sla_aprobacion": r["sla_aprob"],
                "grupo": r["grupo"],
                "estado_tarea": r["estado_tarea"],
                "estado_aprobacion": r["estado_aprob"],
                "cuello": r["cuello"],
            }
            for r in datos["top_cuellos_anio_actual"]
        ],
        "top20_cuellos_anio_anterior": [
            {
                "ritm": r["numero"],
                "formulario": r["elemento"],
                "etapa": r["etapa"],
                "solicitante": r["solicitante"],
                "mes": r["mes"],
                "sla_total": r["sla"],
                "sla_tarea": r["sla_tarea"],
                "sla_aprobacion": r["sla_aprob"],
                "grupo": r["grupo"],
                "estado_tarea": r["estado_tarea"],
                "estado_aprobacion": r["estado_aprob"],
                "cuello": r["cuello"],
            }
            for r in datos["top_cuellos_anio_anterior"]
        ],
    }

    prompt = f"""Eres un asistente de reportería para AFP Capital, área Ingeniería TI.

Con los siguientes datos actualizados de ServiceNow, genera un reporte HTML completo, profesional y visualmente atractivo.

DATOS:
{json.dumps(resumen, ensure_ascii=False, indent=2)}

INSTRUCCIONES PARA EL HTML:
- Título: "Tickets Proyecto Workflow IT — Vista Comparativa"
- Subtítulo: "AFP Capital · Ingeniería TI · Datos al {datos['fecha_generacion']}"
- Header con gradiente azul oscuro (#0c3c6e → #1a5fa8)
- 3 pestañas navegables: "Resumen Ejecutivo", "Vista Operativa por Formulario", "Detalles SLA"
- Usa Chart.js desde cdnjs.cloudflare.com para los gráficos
- Incluye TODO el JavaScript y CSS inline en un solo archivo HTML

PESTAÑA 1 — RESUMEN EJECUTIVO:
- 4 KPIs: Total RITM {anio_p}, Total RITM {anio_a}, SLA Promedio {anio_p}, SLA Promedio {anio_a}
- Gráfico de líneas: Volumetría mensual {anio_p} vs {anio_a} (lado a lado)
- Gráfico de líneas: SLA promedio mensual {anio_p} vs {anio_a} (lado a lado)
- Sección comparativa: Tiempo de Aprobación vs Tiempo de Tarea (tarjetas con promedios anuales + gráfico de barras agrupadas por mes)

PESTAÑA 2 — VISTA OPERATIVA:
- Una tarjeta por cada formulario
- Mostrar: total RITM {anio_a} en grande, SLA promedio {anio_a}, delta vs {anio_p}
- Cuellos de botella {anio_a}: top 3 con RITM, SLA total, grupo resolutor, estado tarea, cuello (Tarea/Aprobación)
- Tabla debajo con estado tarea, estado aprobación, SLA tarea, SLA aprobación

PESTAÑA 3 — DETALLES SLA:
- Gráfico barras horizontales: top 10 tickets por SLA {anio_a}
- Dos tablas separadas con tabs: una para {anio_p} y otra para {anio_a}
- Columnas: #, RITM, Formulario, Etapa, Solicitante, Mes, SLA Total, SLA Tarea, SLA Aprob, Grupo Resolutor, Estado Tarea, Estado Aprob, Cuello

ESTILO:
- Colores: azul #0c3c6e, verde #10b981, amarillo #f59e0b, rojo #dc2626
- Pills de colores para estados: Completado=verde, Cumplimiento=amarillo, Open=naranja, Closed Complete=verde
- Tag de cuello: 🔧 Tarea (rojo claro) o ⚠ Aprobación (amarillo)
- Fuente Segoe UI
- Border-radius: 12px en las cards
- Fondo general: #f0f2f5

Devuelve SOLO el HTML completo, sin explicaciones ni bloques de código markdown. Empieza directamente con <!DOCTYPE html>"""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8000,
        messages=[{"role": "user", "content": prompt}]
    )

    html = message.content[0].text

    # Limpiar por si Claude agrega bloques markdown
    if html.startswith("```"):
        html = html.split("\n", 1)[1]
        if html.endswith("```"):
            html = html.rsplit("```", 1)[0]

    return html.strip()
