import os
import requests
from datetime import datetime, timedelta
from collections import defaultdict

SN_BASE = os.environ.get("SN_BASE_URL", "")
SN_USER = os.environ.get("SN_USERNAME", "")
SN_PASS = os.environ.get("SN_PASSWORD", "")

# 14 formularios exactos del Excel
CAT_ITEMS = ",".join([
    "098c1d8333631610f9f4984a7e5c7b59",  # Gestión de Tablas
    "3ed9b2ce3bd26a10ee77c237f4e45ab0",  # Agendamiento de Componentes Nube
    "59b6c33b3b4eaa10ee77c237f4e45a23",  # Gestión de Consultas Programadas
    "6ba0d286338b1e10f9f4984a7e5c7b47",  # Cloud SQL
    "a43100c797cf92505529fa77f053afe2",  # Gestión de Buckets
    "a50483a73377ae10f9f4984a7e5c7b0b",  # Gestión de Maquinas Virtuales
    "b261e0e13b275250d034caea26e45a8d",  # Proyecto GCP
    "c919ef5b3bc4f610ee77c237f4e45a59",  # Creación de Proyecto PoC o Sandbox
    "109ce6453beb5e10d034caea26e45a2a",  # Gestión de Cuentas de Servicio Cloud
    "ec519fef339fa610f9f4984a7e5c7b54",  # Gestión de Usuarios Cloud
    "3Df9c0948b3b98ae50d034caea26e45a3e", # Gestión de datasets
    "b2c9d23533233e10f9f4984a7e5c7b23",  # Gestión de proxy transversal
    "52bfcad333a40b90f9f4984a7e5c7b9a", # Managed Airflow
    "05d2b30e3b780b10ee77c237f4e45a90", # Respaldo Cloud
    "29a5a5a63b34cb10ee77c237f4e45a6e", # Gestión de rol aplicativo empresarial
])

AUTH    = (SN_USER, SN_PASS)
HEADERS = {"Accept": "application/json"}

# Horario hábil: lunes a viernes 8:00–18:00 (10 hrs/día)
HORA_INI = 8
HORA_FIN = 18
HRS_DIA  = 10

# SLA targets por grupo para cumplimiento de tareas
SLA_TARGETS = {
    "Gestion Kyndryl":       12,
    "Ingenieria SURA":        8,
    "INGENIERIA SURA":        8,
    "Kyndryl_Accesos":       12,
    "Kyndryl_Accesos Cloud": 12,
    "Kyndryl_Ingeniería":     8,
    "Seguridad SURA":         8,
    "Servicenow":             2,
    "SURA REQ Task":          8,
}

FORMATOS_FECHA = [
    "%Y-%m-%d %H:%M:%S",
    "%d-%m-%Y %H:%M:%S",
    "%d/%m/%Y %H:%M:%S",
    "%m/%d/%Y %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
    "%d-%m-%Y",
    "%Y-%m-%d",
]


def _parsear_fecha(fecha_str):
    if not fecha_str:
        return None
    for fmt in FORMATOS_FECHA:
        try:
            return datetime.strptime(fecha_str.strip(), fmt)
        except ValueError:
            continue
    return None


def _parsear_mes(s):
    dt = _parsear_fecha(s)
    return dt.strftime("%Y-%m") if dt else ""


def _parsear_anio(s):
    dt = _parsear_fecha(s)
    return str(dt.year) if dt else ""


def _paginar(tabla, campos, query):
    resultados = []
    offset = 0
    while True:
        url = (
            f"{SN_BASE}/api/now/table/{tabla}"
            f"?sysparm_display_value=true"
            f"&sysparm_limit=1000"
            f"&sysparm_offset={offset}"
            f"&sysparm_fields={campos}"
            f"&sysparm_query={query}"
        )
        resp = requests.get(url, auth=AUTH, headers=HEADERS, timeout=60)
        resp.raise_for_status()
        data = resp.json().get("result", [])
        print(f"  Página {offset//1000+1}: {len(data)} registros")
        if not data:
            break
        resultados.extend(data)
        if len(data) < 1000:
            break
        offset += 1000
    print(f"  Total {tabla}: {len(resultados)}")
    return resultados


def _val(campo):
    if isinstance(campo, dict):
        return campo.get("display_value", "")
    return campo or ""


def _horas_habiles(inicio_str, fin_str):
    """
    Calcula horas hábiles exactas entre dos fechas.
    Horario: lunes-viernes 8:00-18:00 (10 hrs/día).
    Igual a la fórmula del Excel.
    """
    if not inicio_str or not fin_str:
        return None
    try:
        inicio = _parsear_fecha(inicio_str)
        fin    = _parsear_fecha(fin_str)
        if not inicio or not fin:
            return None
        if inicio >= fin:
            return 0.0

        def h(dt):
            return dt.hour + dt.minute / 60

        def clip_ini(dt):
            hh = h(dt)
            if hh < HORA_INI:
                return dt.replace(hour=HORA_INI, minute=0, second=0, microsecond=0)
            if hh >= HORA_FIN:
                sig = dt.date() + timedelta(days=1)
                return datetime(sig.year, sig.month, sig.day, HORA_INI, 0, 0)
            return dt

        def clip_fin(dt):
            hh = h(dt)
            if hh <= HORA_INI:
                prev = dt.date() - timedelta(days=1)
                return datetime(prev.year, prev.month, prev.day, HORA_FIN, 0, 0)
            if hh > HORA_FIN:
                return dt.replace(hour=HORA_FIN, minute=0, second=0, microsecond=0)
            return dt

        inicio = clip_ini(inicio)
        fin    = clip_fin(fin)
        total  = 0.0
        cur    = inicio

        while cur.date() <= fin.date():
            if cur.weekday() < 5:
                if cur.date() == inicio.date() == fin.date():
                    total += max(0, h(fin) - h(cur))
                    break
                elif cur.date() == inicio.date():
                    total += max(0, HORA_FIN - h(cur))
                elif cur.date() == fin.date():
                    total += max(0, h(fin) - HORA_INI)
                else:
                    total += HRS_DIA
            cur = datetime(cur.year, cur.month, cur.day) + timedelta(days=1)

        return round(total, 2)
    except Exception as e:
        return None


def fetch_all_data():
    now       = datetime.now()
    now_str   = now.strftime("%Y-%m-%d %H:%M:%S")
    anio_aa   = now.year
    anio_ap   = now.year - 1
    aa        = str(anio_aa)
    ap        = str(anio_ap)
    fecha_desde = f"{anio_ap}-01-01"

    # ── 1. RITM ───────────────────────────────────────────────────────────────
    print("Descargando RITM...")
    raw_ritm = _paginar(
        "sc_req_item",
        "number,cat_item,stage,opened_by,sys_created_on,closed_at,sys_updated_on",
        f"opened_at>={fecha_desde}^cat_itemIN{CAT_ITEMS}"
    )

    if raw_ritm:
        ej = _val(raw_ritm[0].get("sys_created_on", ""))
        print(f"Ejemplo fecha: {repr(ej)} → {_parsear_fecha(ej)}")

    ritm_list = []
    for r in raw_ritm:
        creado  = _val(r.get("sys_created_on", ""))
        cerrado = _val(r.get("closed_at", ""))
        # SLA hasta cierre si está cerrado, hasta ahora si está abierto
        fin_sla = cerrado if cerrado else now_str
        ritm_list.append({
            "numero":      _val(r.get("number", "")),
            "elemento":    _val(r.get("cat_item", "")),
            "etapa":       _val(r.get("stage", "")),
            "solicitante": _val(r.get("opened_by", "")),
            "creado":      creado,
            "cerrado":     cerrado,
            "mes":         _parsear_mes(creado),
            "anio":        _parsear_anio(creado),
            "sla":         _horas_habiles(creado, fin_sla),
            "sla_cerrado": _horas_habiles(creado, cerrado) if cerrado else None,
            "cerrado_real": bool(cerrado),
        })

    # ── 2. Tareas ─────────────────────────────────────────────────────────────
    print("Descargando tareas...")
    raw_tasks = _paginar(
        "sc_task",
        "number,request_item,state,assignment_group,opened_at,closed_at,due_date",
        f"opened_at>={fecha_desde}^cat_itemIN{CAT_ITEMS}"
    )

    # Por RITM: grupo resolutor, estado, SLA tarea
    task_grupo  = defaultdict(list)
    task_estado = defaultdict(list)
    task_sla    = defaultdict(list)

    # Por grupo: stats de tareas (para tabla 2A del Excel)
    tarea_grupo_stats = defaultdict(lambda: {
        "total": 0, "dentro": 0, "fuera": 0, "sla_hrs": []
    })

    for t in raw_tasks:
        ritm   = _val(t.get("request_item", ""))
        ini    = _val(t.get("opened_at", ""))
        fin    = _val(t.get("closed_at", ""))
        grupo  = _val(t.get("assignment_group", ""))
        estado = _val(t.get("state", ""))
        fin_t  = fin if fin else now_str
        sla    = _horas_habiles(ini, fin_t)

        if grupo:
            task_grupo[ritm].append(grupo)
        if estado:
            task_estado[ritm].append(estado)
        if sla is not None:
            task_sla[ritm].append(sla)

        # Stats por grupo (tabla 2A)
        if grupo:
            tarea_grupo_stats[grupo]["total"] += 1
            tarea_grupo_stats[grupo]["sla_hrs"].append(sla or 0)
            target = next((v for k, v in SLA_TARGETS.items() if k.lower() in grupo.lower()), 12)
            if sla is not None and sla <= target:
                tarea_grupo_stats[grupo]["dentro"] += 1
            else:
                tarea_grupo_stats[grupo]["fuera"] += 1

    # ── 3. Aprobaciones ───────────────────────────────────────────────────────
    print("Descargando aprobaciones...")
    numeros   = {r["numero"] for r in ritm_list}
    raw_aprob = _paginar(
        "sysapproval_approver",
        "state,sysapproval,approver,sys_created_on,sys_updated_on",
        f"sys_created_on>={fecha_desde}"
    )

    # Por RITM: suma acumulada de tiempos de aprobación (como el Excel)
    aprob_suma   = defaultdict(float)   # suma total de horas de aprobación por RITM
    aprob_estado = defaultdict(list)
    aprob_aprobador = defaultdict(list)

    # Por aprobador: stats (tabla 3C del Excel)
    aprobador_stats = defaultdict(lambda: {
        "total": 0, "completadas": 0, "sla_hrs": []
    })

    for a in raw_aprob:
        ritm   = _val(a.get("sysapproval", ""))
        if ritm not in numeros:
            continue
        cre    = _val(a.get("sys_created_on", ""))
        act    = _val(a.get("sys_updated_on", ""))
        estado = _val(a.get("state", ""))
        apro   = _val(a.get("approver", ""))
        # Tiempo de esta aprobación específica
        fin_a  = act if act else now_str
        sla    = _horas_habiles(cre, fin_a)

        if sla is not None:
            aprob_suma[ritm] += sla  # SUMA ACUMULADA como el Excel

        if estado:
            aprob_estado[ritm].append(estado)
        if apro:
            aprob_aprobador[ritm].append(apro)

        # Stats por aprobador
        if apro:
            aprobador_stats[apro]["total"] += 1
            if estado.lower() in ["approved", "aprobado"]:
                aprobador_stats[apro]["completadas"] += 1
            if sla is not None:
                aprobador_stats[apro]["sla_hrs"].append(sla)

    # ── 4. Enriquecer RITM ────────────────────────────────────────────────────
    def prom(lst):
        v = [x for x in lst if x is not None and x >= 0]
        return round(sum(v) / len(v), 2) if v else None

    for r in ritm_list:
        n = r["numero"]
        # Grupo resolutor (puede ser múltiple)
        grupos_list = list(set(task_grupo.get(n, [])))
        r["grupo"]        = ", ".join(grupos_list)
        r["estado_tarea"] = ", ".join(set(task_estado.get(n, [])))
        r["estado_aprob"] = ", ".join(set(aprob_estado.get(n, [])))
        r["aprobadores"]  = ", ".join(set(aprob_aprobador.get(n, [])))

        # SLA tarea promedio
        st = task_sla.get(n)
        r["sla_tarea"] = round(sum(st)/len(st), 2) if st else None

        # SLA aprobación = SUMA ACUMULADA de todas las aprobaciones del RITM
        r["sla_aprob"] = round(aprob_suma[n], 2) if aprob_suma.get(n) else None

        # Tiempo post-aprobación = SLA total - SLA aprobación
        # (nunca puede ser negativo — si lo es, hay datos inconsistentes)
        if r["sla"] is not None and r["sla_aprob"] is not None:
            post = r["sla"] - r["sla_aprob"]
            r["sla_post_aprob"] = round(max(post, 0), 2)
        else:
            r["sla_post_aprob"] = r["sla_cerrado"] if r["sla_aprob"] is None else None

        # Cuello de botella
        if r["sla_aprob"] and r["sla_tarea"]:
            r["cuello"] = "Aprobacion" if r["sla_aprob"] > r["sla_tarea"] else "Tarea"
        elif r["sla_tarea"]:
            r["cuello"] = "Tarea"
        elif r["sla_aprob"]:
            r["cuello"] = "Aprobacion"
        else:
            r["cuello"] = "Sin datos"

    # ── 5. Agrupaciones ───────────────────────────────────────────────────────
    por_anio = defaultdict(list)
    for r in ritm_list:
        if r["anio"]:
            por_anio[r["anio"]].append(r)

    vol_mes = defaultdict(int)
    sla_mes = defaultdict(list)   # solo cerrados para el promedio mensual
    for r in ritm_list:
        if r["mes"]:
            vol_mes[r["mes"]] += 1
            if r["sla_cerrado"] is not None:
                sla_mes[r["mes"]].append(r["sla_cerrado"])

    resumen_mes = {}
    for mes in sorted(set(list(vol_mes.keys()) + list(sla_mes.keys()))):
        resumen_mes[mes] = {
            "vol": vol_mes.get(mes, 0),
            "sla": prom(sla_mes.get(mes, [])),
        }

    por_form = defaultdict(lambda: defaultdict(list))
    for r in ritm_list:
        por_form[r["elemento"]][r["anio"]].append(r)

    def top_n(lista, n=20):
        return sorted(
            [r for r in lista if r["sla"] is not None],
            key=lambda x: x["sla"], reverse=True
        )[:n]

    # ── 6. ANÁLISIS TABLA 1: Gestión por grupo resolutor (año actual) ─────────
    # Contar RITM por grupo resolutor (del año actual)
    grupo_ritm_stats = defaultdict(lambda: {
        "total": 0, "cerrados": 0, "en_curso": 0, "sla_hrs": []
    })
    for r in por_anio.get(aa, []):
        grupos_list = [g.strip() for g in r["grupo"].split(",") if g.strip()] or ["Sin grupo"]
        for g in grupos_list:
            grupo_ritm_stats[g]["total"] += 1
            if r["cerrado_real"]:
                grupo_ritm_stats[g]["cerrados"] += 1
                if r["sla_cerrado"] is not None:
                    grupo_ritm_stats[g]["sla_hrs"].append(r["sla_cerrado"])
            else:
                grupo_ritm_stats[g]["en_curso"] += 1
                if r["sla"] is not None:
                    grupo_ritm_stats[g]["sla_hrs"].append(r["sla"])

    analisis_grupo = []
    for g, s in sorted(grupo_ritm_stats.items()):
        if g == "Sin grupo":
            continue
        analisis_grupo.append({
            "grupo":    g,
            "total":    s["total"],
            "cerrados": s["cerrados"],
            "en_curso": s["en_curso"],
            "sla_prom": prom(s["sla_hrs"]),
            "sla_total": round(sum(s["sla_hrs"]), 2) if s["sla_hrs"] else 0,
        })

    # ── 7. ANÁLISIS TABLA 1B: Gestión por elemento (año actual) ──────────────
    analisis_elemento = []
    for elem, anios in por_form.items():
        rs_aa = anios.get(aa, [])
        if not rs_aa:
            continue
        cerrados = [r for r in rs_aa if r["cerrado_real"]]
        en_curso = [r for r in rs_aa if not r["cerrado_real"]]
        sla_hrs  = [r["sla_cerrado"] for r in cerrados if r["sla_cerrado"] is not None]
        # Tiempo aprobación: suma acumulada por RITM, promedio entre los que tienen
        aprob_hrs = [r["sla_aprob"] for r in rs_aa if r["sla_aprob"] is not None]
        # Tiempo gestión = SLA total - aprobación (solo positivos)
        post_hrs  = [r["sla_post_aprob"] for r in rs_aa if r["sla_post_aprob"] is not None]

        sla_p   = prom(sla_hrs)
        aprob_p = prom(aprob_hrs)
        post_p  = prom(post_hrs)

        # % aprobación y % gestión respecto al SLA total
        pct_a = round(aprob_p / sla_p, 4) if sla_p and aprob_p else None
        pct_p = round(post_p / sla_p, 4) if sla_p and post_p else None

        analisis_elemento.append({
            "elemento":   elem,
            "total":      len(rs_aa),
            "cerrados":   len(cerrados),
            "en_curso":   len(en_curso),
            "sla_prom":   sla_p,
            "sla_total":  round(sum(sla_hrs), 2) if sla_hrs else 0,
            "aprob_prom": aprob_p,
            "post_prom":  post_p,
            "pct_aprob":  pct_a,
            "pct_post":   pct_p,
        })

    # ── 8. ANÁLISIS TABLA 2A: Cumplimiento SLA tareas ────────────────────────
    cumplimiento_grupo = []
    for g, s in sorted(tarea_grupo_stats.items()):
        total = s["total"]
        cumplimiento_grupo.append({
            "grupo":    g,
            "total":    total,
            "dentro":   s["dentro"],
            "fuera":    s["fuera"],
            "pct":      round(s["dentro"] / total, 4) if total else 0,
            "sla_prom": prom(s["sla_hrs"]),
            "sla_total": round(sum(s["sla_hrs"]), 2),
        })

    # ── 9. ANÁLISIS TABLA 3C: Aprobadores ────────────────────────────────────
    analisis_aprobadores = []
    for apro, s in sorted(aprobador_stats.items()):
        analisis_aprobadores.append({
            "aprobador":   apro,
            "total":       s["total"],
            "completadas": s["completadas"],
            "sla_prom":    prom(s["sla_hrs"]),
            "sla_total":   round(sum(s["sla_hrs"]), 2) if s["sla_hrs"] else 0,
        })

    # ── 10. RESUMEN TIEMPOS (Tabla 3A del Excel) ──────────────────────────────
    # Solo año actual, solo cerrados
    rs_aa_cerrados = [r for r in por_anio.get(aa, []) if r["cerrado_real"]]
    todos_sla      = [r["sla_cerrado"] for r in rs_aa_cerrados if r["sla_cerrado"] is not None]
    todos_aprob    = [r["sla_aprob"] for r in por_anio.get(aa, []) if r["sla_aprob"] is not None]
    todos_post     = [r["sla_post_aprob"] for r in por_anio.get(aa, []) if r["sla_post_aprob"] is not None]

    total_sla_sum   = round(sum(todos_sla), 2)
    total_aprob_sum = round(sum(todos_aprob), 2)
    total_post_sum  = round(sum(todos_post), 2)

    resumen_tiempos = {
        "sla_prom":    prom(todos_sla),
        "sla_total":   total_sla_sum,
        "aprob_prom":  prom(todos_aprob),
        "aprob_total": total_aprob_sum,
        "post_prom":   prom(todos_post),
        "post_total":  total_post_sum,
        "pct_aprob":   round(total_aprob_sum / total_sla_sum, 4) if total_sla_sum else None,
        "pct_post":    round(total_post_sum / total_sla_sum, 4) if total_sla_sum else None,
    }

    # ── 11. PRE/POST AUTOMATIZACIÓN (Tabla 5 del Excel) ──────────────────────
    ELEM_AUTO = "Gestión de Cuentas de Servicio Cloud"
    cuentas_aa = por_form.get(ELEM_AUTO, {}).get(aa, [])
    meses_pre  = [aa+"-01", aa+"-02", aa+"-03"]
    meses_post = [aa+"-04", aa+"-05"]

    def stats_periodo(tickets, meses):
        sub = [r for r in tickets if r["mes"] in meses]
        cerrados = [r for r in sub if r["cerrado_real"]]
        sla_vals = [r["sla_cerrado"] for r in cerrados if r["sla_cerrado"] is not None]
        # Para abiertos usar sla hasta now
        sla_all  = [r["sla"] for r in sub if r["sla"] is not None]
        return {
            "total":    len(sub),
            "cerrados": len(cerrados),
            "sla_prom": prom(sla_vals) if sla_vals else prom(sla_all),
            "sla_total": round(sum(sla_vals), 2) if sla_vals else round(sum(sla_all), 2),
        }

    pre_stats  = stats_periodo(cuentas_aa, meses_pre)
    post_stats = stats_periodo(cuentas_aa, meses_post)

    sla_pre_v  = pre_stats["sla_prom"] or 0
    sla_post_v = post_stats["sla_prom"] or 0
    reduccion  = round(sla_pre_v - sla_post_v, 2)
    pct_mejora = round(reduccion / sla_pre_v, 4) if sla_pre_v else 0
    # HH ahorradas = (RITs post × tiempo pre) - tiempo real post
    hh_proyectadas = round(post_stats["total"] * sla_pre_v, 2)
    hh_ahorradas   = round(hh_proyectadas - post_stats["sla_total"], 2)

    automatizacion = {
        "pre":          pre_stats,
        "post":         post_stats,
        "reduccion_hrs": reduccion,
        "pct_mejora":   pct_mejora,
        "hh_proyectadas": hh_proyectadas,
        "hh_ahorradas": hh_ahorradas,
        "dias_persona": round(hh_ahorradas / HRS_DIA, 2),
        "meses_persona": round(hh_ahorradas / HRS_DIA / 22, 2),
        # Por mes para el gráfico
        "por_mes": {
            m: stats_periodo(cuentas_aa, [m])
            for m in meses_pre + meses_post
        }
    }

    # ── 12. MEJORA 2025 vs 2026 (Tabla 4 del Excel) ──────────────────────────
    BASELINE_HRS = 30.0  # 3 días × 10 hrs/día
    # Solo RITM cerrados del año actual para el SLA actual
    sla_aa_cerrados = prom([r["sla_cerrado"] for r in rs_aa_cerrados if r["sla_cerrado"]])
    total_ritm_aa   = len(por_anio.get(aa, []))
    reduccion_rr    = round(BASELINE_HRS - (sla_aa_cerrados or 0), 2)
    pct_mejora_rr   = round(reduccion_rr / BASELINE_HRS, 4) if sla_aa_cerrados else None
    hh_ahorradas_rr = round(total_ritm_aa * reduccion_rr, 2)

    mejora_2025_2026 = {
        "baseline_2025_hrs": BASELINE_HRS,
        "actual_2026_hrs":   sla_aa_cerrados,
        "reduccion_hrs":     reduccion_rr,
        "pct_mejora":        pct_mejora_rr,
        "total_ritm_2026":   total_ritm_aa,
        "hh_ahorradas_total": hh_ahorradas_rr,
        "hh_habrian_sido":   round(total_ritm_aa * BASELINE_HRS, 2),
        "dias_persona":      round(hh_ahorradas_rr / HRS_DIA, 2),
        "meses_persona":     round(hh_ahorradas_rr / HRS_DIA / 22, 2),
        "fte_anual":         round(hh_ahorradas_rr / HRS_DIA / 22 / 12, 2),
    }

    # ── 13. SLA promedio por año para KPIs (solo cerrados) ───────────────────
    sla_prom_por_anio = {}
    for a, rs in por_anio.items():
        vals = [r["sla_cerrado"] for r in rs if r["sla_cerrado"] is not None]
        sla_prom_por_anio[a] = prom(vals)

    sla_tarea_prom_por_anio = {}
    for a, rs in por_anio.items():
        vals = [r["sla_tarea"] for r in rs if r["sla_tarea"] is not None]
        sla_tarea_prom_por_anio[a] = prom(vals)

    sla_aprob_prom_por_anio = {}
    for a, rs in por_anio.items():
        vals = [r["sla_aprob"] for r in rs if r["sla_aprob"] is not None]
        sla_aprob_prom_por_anio[a] = prom(vals)

    # ── Debug ─────────────────────────────────────────────────────────────────
    print(f"\nDEBUG años: {sorted(por_anio.keys())}")
    print(f"DEBUG RITM: { {a: len(v) for a, v in por_anio.items()} }")
    cerr = {a: sum(1 for r in v if r['cerrado_real']) for a, v in por_anio.items()}
    print(f"DEBUG cerrados: {cerr}")
    print(f"DEBUG SLA prom (cerrados): {sla_prom_por_anio}")
    print(f"DEBUG SLA aprob prom: {sla_aprob_prom_por_anio}")
    print(f"DEBUG resumen tiempos: {resumen_tiempos}")
    print(f"DEBUG formularios: {list(por_form.keys())}")
    print(f"DEBUG mejora: {mejora_2025_2026}\n")

    return {
        "fecha_generacion":          now.strftime("%d %b %Y %H:%M"),
        "total_ritm":                len(ritm_list),
        "total_tasks":               len(raw_tasks),
        "total_approvals":           len(raw_aprob),
        "anio_actual":               aa,
        "anio_anterior":             ap,
        "ritm_por_anio":             {a: len(v) for a, v in por_anio.items()},
        "sla_prom_por_anio":         sla_prom_por_anio,
        "sla_tarea_prom_por_anio":   sla_tarea_prom_por_anio,
        "sla_aprob_prom_por_anio":   sla_aprob_prom_por_anio,
        "resumen_mes":               resumen_mes,
        "por_form_anio": {
            form: {
                anio: {
                    "vol":  len(rs),
                    "sla":  prom([r["sla_cerrado"] for r in rs if r["sla_cerrado"] is not None]),
                    "top3": top_n(rs, 3),
                }
                for anio, rs in anios.items()
            }
            for form, anios in por_form.items()
        },
        "top_cuellos_anio_actual":   top_n(por_anio.get(aa, []), 20),
        "top_cuellos_anio_anterior": top_n(por_anio.get(ap, []), 20),
        "analisis_grupo":            analisis_grupo,
        "analisis_elemento":         analisis_elemento,
        "cumplimiento_grupo":        cumplimiento_grupo,
        "analisis_aprobadores":      analisis_aprobadores,
        "resumen_tiempos":           resumen_tiempos,
        "automatizacion":            automatizacion,
        "mejora_2025_2026":          mejora_2025_2026,
    }
