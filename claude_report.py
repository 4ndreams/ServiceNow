import os
import json
import anthropic

def generar_html(datos: dict) -> str:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    aa = datos["anio_actual"]
    ap = datos["anio_anterior"]

    resumen = {
        "fecha_generacion":        datos["fecha_generacion"],
        "anio_actual":             aa,
        "anio_anterior":           ap,
        "total_ritm_por_anio":     datos["ritm_por_anio"],
        "sla_promedio_por_anio":   datos["sla_prom_por_anio"],
        "sla_tarea_por_anio":      datos["sla_tarea_prom_por_anio"],
        "sla_aprobacion_por_anio": datos["sla_aprob_prom_por_anio"],
        "volumetria_mensual":      datos["resumen_mes"],
        "por_formulario": {
            form: {
                anio: {
                    "volumen": info["vol"],
                    "sla":     info["sla"],
                    "top3": [
                        {
                            "ritm":   r["numero"],
                            "sla":    r["sla"],
                            "slaT":   r["sla_tarea"],
                            "slaA":   r["sla_aprob"],
                            "grupo":  r["grupo"],
                            "estT":   r["estado_tarea"],
                            "estA":   r["estado_aprob"],
                            "cuello": r["cuello"],
                            "mes":    r["mes"],
                        }
                        for r in info["top3"]
                    ]
                }
                for anio, info in anios.items()
            }
            for form, anios in datos["por_form_anio"].items()
        },
        "top20_actual": [
            {
                "ritm":   r["numero"],
                "form":   r["elemento"],
                "etapa":  r["etapa"],
                "sol":    r["solicitante"],
                "mes":    r["mes"],
                "sla":    r["sla"],
                "slaT":   r["sla_tarea"],
                "slaA":   r["sla_aprob"],
                "grupo":  r["grupo"],
                "estT":   r["estado_tarea"],
                "estA":   r["estado_aprob"],
                "cuello": r["cuello"],
            }
            for r in datos["top_cuellos_anio_actual"]
        ],
        "top20_anterior": [
            {
                "ritm":   r["numero"],
                "form":   r["elemento"],
                "etapa":  r["etapa"],
                "sol":    r["solicitante"],
                "mes":    r["mes"],
                "sla":    r["sla"],
                "slaT":   r["sla_tarea"],
                "slaA":   r["sla_aprob"],
                "grupo":  r["grupo"],
                "estT":   r["estado_tarea"],
                "estA":   r["estado_aprob"],
                "cuello": r["cuello"],
            }
            for r in datos["top_cuellos_anio_anterior"]
        ],
    }

    prompt = f"""Eres un asistente de reportería para AFP Capital, área Ingeniería TI.

Con los siguientes datos actualizados de ServiceNow, genera un reporte HTML completo, profesional y visualmente atractivo.

DATOS:
{json.dumps(resumen, ensure_ascii=False, indent=2)}

INSTRUCCIONES:
- Título: "Tickets Proyecto Workflow IT — Vista Comparativa"
- Subtítulo: "AFP Capital · Ingeniería TI · Datos al {datos['fecha_generacion']}"
- Header con gradiente azul oscuro (#0c3c6e a #1a5fa8)
- 3 pestañas navegables: "Resumen Ejecutivo", "Vista Operativa por Formulario", "Detalles SLA"
- Usa Chart.js desde cdnjs.cloudflare.com para los gráficos
- Todo el CSS y JS inline en un solo archivo HTML

PESTAÑA 1 — RESUMEN EJECUTIVO:
- 4 KPIs: Total RITM {ap}, Total RITM {aa}, SLA Promedio {ap}, SLA Promedio {aa}
- Gráfico de líneas: Volumetría mensual {ap} vs {aa} (lado a lado)
- Gráfico de líneas: SLA promedio mensual {ap} vs {aa} (lado a lado)
- Sección: Tiempo Aprobación vs Tiempo Tarea con tarjetas de promedios anuales y gráfico de barras agrupadas por mes

PESTAÑA 2 — VISTA OPERATIVA:
- Una tarjeta por cada formulario con: total RITM {aa} en grande, SLA promedio {aa}, delta vs {ap}
- Cuellos de botella {aa}: top 3 con RITM, SLA, grupo resolutor, estado tarea, cuello (Tarea/Aprobación)
- Tabla debajo con estado tarea, estado aprobación, SLA tarea, SLA aprobación por ticket

PESTAÑA 3 — DETALLES SLA:
- Gráfico barras horizontales top 10 tickets {aa}
- Dos tablas con tabs separados: {ap} y {aa}
- Columnas: #, RITM, Formulario, Etapa, Solicitante, Mes, SLA Total, SLA Tarea, SLA Aprob, Grupo, Estado Tarea, Estado Aprob, Cuello

ESTILO:
- Colores: #0c3c6e azul, #10b981 verde, #f59e0b amarillo, #dc2626 rojo
- Pills coloreados para estados
- Cuello: 🔧 Tarea (rojo claro) o ⚠ Aprobación (amarillo)
- Fondo: #f0f2f5, cards con border-radius 12px, fuente Segoe UI

Devuelve SOLO el HTML completo sin explicaciones. Empieza con <!DOCTYPE html>"""

    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8000,
        messages=[{"role": "user", "content": prompt}]
    )

    html = msg.content[0].text
    if html.startswith("```"):
        html = html.split("\n", 1)[1]
        if html.endswith("```"):
            html = html.rsplit("```", 1)[0]
    return html.strip()
