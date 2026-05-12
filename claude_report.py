import os
import json
import anthropic


def generar_html(datos: dict) -> str:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    aa = datos["anio_actual"]
    ap = datos["anio_anterior"]
    mt = datos["mejora_2025_2026"]
    at = datos["automatizacion"]
    rt = datos["resumen_tiempos"]

    resumen = {
        "fecha_generacion":    datos["fecha_generacion"],
        "anio_actual":         aa,
        "anio_anterior":       ap,
        "total_ritm":          datos["total_ritm"],
        "ritm_por_anio":       datos["ritm_por_anio"],
        "sla_prom_por_anio":   datos["sla_prom_por_anio"],
        "sla_tarea_por_anio":  datos["sla_tarea_prom_por_anio"],
        "sla_aprob_por_anio":  datos["sla_aprob_prom_por_anio"],
        "volumetria_mensual":  datos["resumen_mes"],
        "por_formulario": {
            form: {
                anio: {
                    "vol":  info["vol"],
                    "sla":  info["sla"],
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
                "ritm":   r["numero"], "form": r["elemento"], "etapa": r["etapa"],
                "sol":    r["solicitante"], "mes": r["mes"],
                "sla":    r["sla"], "slaT": r["sla_tarea"], "slaA": r["sla_aprob"],
                "grupo":  r["grupo"], "estT": r["estado_tarea"],
                "estA":   r["estado_aprob"], "cuello": r["cuello"],
            }
            for r in datos["top_cuellos_anio_actual"]
        ],
        "top20_anterior": [
            {
                "ritm":   r["numero"], "form": r["elemento"], "etapa": r["etapa"],
                "sol":    r["solicitante"], "mes": r["mes"],
                "sla":    r["sla"], "slaT": r["sla_tarea"], "slaA": r["sla_aprob"],
                "grupo":  r["grupo"], "estT": r["estado_tarea"],
                "estA":   r["estado_aprob"], "cuello": r["cuello"],
            }
            for r in datos["top_cuellos_anio_anterior"]
        ],
        "analisis_tiempos": {
            "resumen_general": rt,
            "por_grupo_resolutor": datos["analisis_grupo"],
            "por_elemento": datos["analisis_elemento"],
            "cumplimiento_sla_tareas": datos["cumplimiento_grupo"],
            "por_aprobador": datos["analisis_aprobadores"],
            "mejora_2025_2026": mt,
            "automatizacion_cuentas_servicio": at,
        }
    }

    prompt = f"""Eres un asistente de reportería para AFP Capital, área Ingeniería TI.

Con los siguientes datos actualizados de ServiceNow, genera un reporte HTML completo, profesional y visualmente atractivo.

DATOS:
{json.dumps(resumen, ensure_ascii=False, indent=2)}

INSTRUCCIONES GENERALES:
- Título: "Tickets Proyecto Workflow IT — Vista Comparativa"
- Subtítulo: "AFP Capital · Ingeniería TI · Datos al {datos['fecha_generacion']}"
- Header con gradiente azul oscuro (#0c3c6e a #1a5fa8)
- 5 pestañas navegables con iconos
- Chart.js desde cdnjs.cloudflare.com para gráficos
- Todo CSS y JS inline en un solo archivo HTML
- Fondo #f0f2f5, cards border-radius 12px, fuente Segoe UI
- Colores: #0c3c6e azul, #10b981 verde, #f59e0b amarillo, #dc2626 rojo, #8b5cf6 púrpura

═══ PESTAÑA 1: "📊 Resumen Ejecutivo" ═══
- 4 KPIs: Total RITM {ap}, Total RITM {aa}, SLA Prom {ap}, SLA Prom {aa}
- Gráfico líneas: Volumetría mensual {ap} vs {aa} lado a lado
- Gráfico líneas: SLA promedio mensual {ap} vs {aa} lado a lado
- Sección comparativa Aprobación vs Tarea: tarjetas con promedios anuales + gráfico barras agrupadas por mes

═══ PESTAÑA 2: "🗂 Vista Operativa por Formulario" ═══
- Una tarjeta por cada formulario con: total RITM {aa} en grande, SLA promedio {aa}, delta vs {ap}
- Cuellos de botella {aa}: top 3 con RITM, SLA, grupo resolutor, estado tarea, cuello (Tarea/Aprobación)
- Tabla debajo con estado tarea, estado aprobación, SLA tarea, SLA aprobación

═══ PESTAÑA 3: "📋 Detalles SLA" ═══
- Gráfico barras horizontales top 10 tickets {aa}
- Dos tablas separadas con tabs: {ap} y {aa}
- Columnas: #, RITM, Formulario, Etapa, Solicitante, Mes, SLA Total, SLA Tarea, SLA Aprob, Grupo, Estado Tarea, Estado Aprob, Cuello

═══ PESTAÑA 4: "⏱ Análisis de Tiempos" ═══
Esta pestaña tiene 4 sub-secciones con sus propios tabs:

TAB A — "Gestión por Grupo Resolutor":
- Tabla: Grupo | Total RITs | Cerrados | En Curso | Tiempo Prom (hrs) | Tiempo Total (hrs)
- Gráfico barras horizontales: tiempo promedio por grupo

TAB B — "Gestión por Formulario":
- Tabla: Formulario | Total | Cerrados | En Curso | SLA Prom | Aprob Prom | Post-Aprob Prom | % Aprob | % Post
- Gráfico barras apiladas: % tiempo aprobación vs % tiempo post-aprobación por formulario

TAB C — "Cumplimiento SLA Tareas":
- Tabla: Grupo | Total Tareas | Dentro SLA | Fuera SLA | % Cumplimiento | SLA Prom
- Gráfico dona: % cumplimiento general
- Gráfico barras: % cumplimiento por grupo

TAB D — "Aprobadores":
- Tabla: Aprobador | Total | Completadas | Tiempo Prom (hrs) | Tiempo Total (hrs)
- Gráfico barras: tiempo promedio por aprobador

═══ PESTAÑA 5: "🚀 Impacto y Mejoras" ═══
Esta pestaña tiene 2 sub-secciones:

SECCIÓN A — "Mejora 2025 vs 2026":
- KPIs destacados: Baseline 2025 (30 hrs), Actual 2026, Reducción (hrs), % Mejora
- KPIs de impacto: Total RITM procesados, HH Ahorradas, Días-Persona, Meses-Persona, FTE Equivalente
- Gráfico comparativo de barras: 2025 vs 2026
- Texto interpretativo con los hallazgos principales

SECCIÓN B — "Impacto Automatización Cuentas de Servicio Cloud":
- KPIs: Pre-Auto (Ene-Mar) vs Post-Auto (Abr-May): Total RITs, SLA Prom, HH Ahorradas
- Gráfico líneas: evolución mensual SLA de Gestión Cuentas Servicio Cloud
- Gráfico barras comparativo Pre vs Post automatización
- % de mejora en tiempo de gestión
- Texto interpretativo

ESTILO PARA TODOS:
- Pills coloreados: Completado=verde, Cumplimiento=amarillo, Open=naranja, Closed Complete=verde
- Cuello: 🔧 Tarea (rojo claro) o ⚠ Aprobación (amarillo)
- Tablas: hover effect, headers gris claro, alternating rows
- Números grandes en KPIs, texto descriptivo pequeño abajo
- % de mejora en verde si positivo, rojo si negativo

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
