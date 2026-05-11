"""
sn_fetch.py — Descarga datos de ServiceNow
Trae RITM, tareas (SCTASK) y aprobaciones con paginación automática.
"""

import os
import requests
from datetime import datetime

# ── Configuración ──────────────────────────────────────────────────────────────
SN_BASE   = os.environ["SN_BASE_URL"]        # ej: https://ibmsurachileprod.service-now.com
SN_USER   = os.environ["SN_USERNAME"]
SN_PASS   = os.environ["SN_PASSWORD"]

# IDs de los formularios (cat_item) — los mismos de tus queries
CAT_ITEMS = ",".join([
    "098c1d8333631610f9f4984a7e5c7b59",
    "3ed9b2ce3bd26a10ee77c237f4e45ab0",
    "59b6c33b3b4eaa10ee77c237f4e45a23",
    "6ba0d286338b1e10f9f4984a7e5c7b47",
    "a43100c797cf92505529fa77f053afe2",
    "a50483a73377ae10f9f4984a7e5c7b0b",
    "b261e0e13b275250d034caea26e45a8d",
    "c919ef5b3bc4f610ee77c237f4e45a59",
])

AUTH = (SN_USER, SN_PASS)
HEADERS = {"Accept": "application/json"}


def _paginar(tabla: str, campos: str, query: str) -> list:
    """Descarga todos los registros de una tabla usando paginación de 1000 en 1000."""
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
        if not data:
            break
        resultados.extend(data)
        offset += 1000
        if len(data) < 1000:
            break
    return resultados


def _val(campo):
    """Extrae display_value si es un dict, si no devuelve el valor directo."""
    if isinstance(campo, dict):
        return campo.get("display_value", "")
    return campo or ""


def _calcular_horas_habiles(inicio_str, fin_str) -> float | None:
    """Calcula horas hábiles entre dos fechas (lun-vie, 08:00-19:00)."""
    if not inicio_str or not fin_str:
        return None
    try:
        fmt = "%Y-%m-%d %H:%M:%S"
        inicio = datetime.strptime(inicio_str, fmt)
        fin    = datetime.strptime(fin_str, fmt)
        if inicio >= fin:
            return 0.0

        HORA_INI, HORA_FIN = 8, 19
        HRS_DIA = HORA_FIN - HORA_INI  # 11 hrs

        def clip(dt):
            h = dt.hour + dt.minute / 60
            if h < HORA_INI:
                return dt.replace(hour=HORA_INI, minute=0, second=0)
            if h >= HORA_FIN:
                from datetime import timedelta
                sig = dt.date() + timedelta(days=1)
                return datetime(sig.year, sig.month, sig.day, HORA_INI, 0, 0)
            return dt

        inicio = clip(inicio)
        fin    = clip(fin)

        total = 0.0
        cur = inicio
        from datetime import timedelta
        while cur.date() <= fin.date():
            if cur.weekday() < 5:  # lunes a viernes
                h_ini = HORA_INI if cur.date() < fin.date() else (fin.hour + fin.minute / 60)
                h_fin = HORA_FIN if cur.date() < fin.date() else (fin.hour + fin.minute / 60)
                if cur.date() == inicio.date():
                    h_ini = cur.hour + cur.minute / 60
                if cur.date() == fin.date() and cur.date() == inicio.date():
                    total += max(0, (fin.hour + fin.minute/60) - (inicio.hour + inicio.minute/60))
                    break
                elif cur.date() == inicio.date():
                    total += max(0, HORA_FIN - (inicio.hour + inicio.minute / 60))
                elif cur.date() == fin.date():
                    total += max(0, (fin.hour + fin.minute / 60) - HORA_INI)
                else:
                    total += HRS_DIA
            cur = datetime(cur.year, cur.month, cur.day) + timedelta(days=1)
        return round(total, 2)
    except Exception:
        return None


def fetch_all_data() -> dict:
    """Descarga y procesa todos los datos necesarios para el reporte."""

    anio_actual = datetime.now().year
    fecha_desde = f"{anio_actual - 1}-01-01"  # desde 1 ene del año anterior

    # ── 1. RITM ───────────────────────────────────────────────────────────────
    raw_ritm = _paginar(
        tabla="sc_req_item",
        campos="number,cat_item,stage,opened_by,sys_created_on,closed_at,sys_updated_on",
        query=f"opened_at>={fecha_desde}^cat_itemIN{CAT_ITEMS}"
    )

    ritm_list = []
    for r in raw_ritm:
        creado   = _val(r.get("sys_created_on", ""))
        cerrado  = _val(r.get("closed_at", ""))
        sla      = _calcular_horas_habiles(creado, cerrado)
        mes      = creado[:7] if creado else ""
        anio     = creado[:4] if creado else ""
        ritm_list.append({
            "numero":   _val(r.get("number", "")),
            "elemento": _val(r.get("cat_item", "")),
            "etapa":    _val(r.get("stage", "")),
            "solicitante": _val(r.get("opened_by", "")),
            "creado":   creado,
            "cerrado":  cerrado,
            "mes":      mes,
            "anio":     anio,
            "sla":      sla,
        })

    # ── 2. Tareas (SCTASK) ────────────────────────────────────────────────────
    raw_tasks = _paginar(
        tabla="sc_task",
        campos="number,request_item,state,assignment_group,assigned_to,opened_at,closed_at",
        query=f"opened_at>={fecha_desde}^stateIN-5,3,1^cat_itemIN{CAT_ITEMS}"
    )

    tasks_list = []
    for t in raw_tasks:
        inicio  = _val(t.get("opened_at", ""))
        fin     = _val(t.get("closed_at", ""))
        sla     = _calcular_horas_habiles(inicio, fin)
        tasks_list.append({
            "sctask":  _val(t.get("number", "")),
            "ritm":    _val(t.get("request_item", "")),
            "estado":  _val(t.get("state", "")),
            "grupo":   _val(t.get("assignment_group", "")),
            "inicio":  inicio,
            "fin":     fin,
            "sla":     sla,
        })

    # ── 3. Aprobaciones ───────────────────────────────────────────────────────
    raw_aprob = _paginar(
        tabla="sysapproval_approver",
        campos="state,sysapproval,approver,sys_created_on,sys_updated_on",
        query=f"sys_created_on>={fecha_desde}"
    )

    numeros_ritm = {r["numero"] for r in ritm_list}
    aprob_list = []
    for a in raw_aprob:
        ritm_num = _val(a.get("sysapproval", ""))
        if ritm_num not in numeros_ritm:
            continue
        creado    = _val(a.get("sys_created_on", ""))
        actualizado = _val(a.get("sys_updated_on", ""))
        sla       = _calcular_horas_habiles(creado, actualizado)
        aprob_list.append({
            "ritm":      ritm_num,
            "aprobador": _val(a.get("approver", "")),
            "estado":    _val(a.get("state", "")),
            "creado":    creado,
            "actualizado": actualizado,
            "sla":       sla,
        })

    # ── 4. Calcular resumen ───────────────────────────────────────────────────
    from collections import defaultdict

    def promedio(lst):
        vals = [x for x in lst if x is not None]
        return round(sum(vals) / len(vals), 1) if vals else None

    # SLA tarea por RITM
    task_sla_por_ritm = defaultdict(list)
    task_grupo_por_ritm = defaultdict(list)
    task_estado_por_ritm = defaultdict(list)
    for t in tasks_list:
        if t["sla"] is not None:
            task_sla_por_ritm[t["ritm"]].append(t["sla"])
        if t["grupo"]:
            task_grupo_por_ritm[t["ritm"]].append(t["grupo"])
        if t["estado"]:
            task_estado_por_ritm[t["ritm"]].append(t["estado"])

    # SLA aprobacion por RITM
    aprob_sla_por_ritm = defaultdict(list)
    aprob_estado_por_ritm = defaultdict(list)
    for a in aprob_list:
        if a["sla"] is not None:
            aprob_sla_por_ritm[a["ritm"]].append(a["sla"])
        if a["estado"]:
            aprob_estado_por_ritm[a["ritm"]].append(a["estado"])

    # Enriquecer RITM
    for r in ritm_list:
        n = r["numero"]
        sla_t = task_sla_por_ritm.get(n)
        sla_a = aprob_sla_por_ritm.get(n)
        r["sla_tarea"]     = round(sum(sla_t)/len(sla_t), 2) if sla_t else None
        r["sla_aprob"]     = round(max(sla_a), 2) if sla_a else None
        r["grupo"]         = ", ".join(set(task_grupo_por_ritm.get(n, [])))
        r["estado_tarea"]  = ", ".join(set(task_estado_por_ritm.get(n, [])))
        r["estado_aprob"]  = ", ".join(set(aprob_estado_por_ritm.get(n, [])))
        # Cuello de botella
        if r["sla_aprob"] and r["sla_tarea"]:
            r["cuello"] = "Aprobación" if r["sla_aprob"] > r["sla_tarea"] else "Tarea"
        elif r["sla_tarea"]:
            r["cuello"] = "Tarea"
        elif r["sla_aprob"]:
            r["cuello"] = "Aprobación"
        else:
            r["cuello"] = "Sin datos"

    # Agrupar por año
    por_anio = defaultdict(list)
    for r in ritm_list:
        if r["anio"]:
            por_anio[r["anio"]].append(r)

    # Agrupar por formulario y año
    por_form_anio = defaultdict(lambda: defaultdict(list))
    for r in ritm_list:
        por_form_anio[r["elemento"]][r["anio"]].append(r)

    # Volumetría y SLA mensual
    vol_mes = defaultdict(int)
    sla_mes = defaultdict(list)
    for r in ritm_list:
        if r["mes"]:
            vol_mes[r["mes"]] += 1
            if r["sla"] is not None:
                sla_mes[r["mes"]].append(r["sla"])

    resumen_mes = {}
    for mes in sorted(set(list(vol_mes.keys()) + list(sla_mes.keys()))):
        resumen_mes[mes] = {
            "vol": vol_mes.get(mes, 0),
            "sla": promedio(sla_mes.get(mes, [])),
        }

    # Top 20 cuellos de botella por año
    def top_cuellos(lista_ritm, n=20):
        con_sla = [r for r in lista_ritm if r["sla"] is not None]
        return sorted(con_sla, key=lambda x: x["sla"], reverse=True)[:n]

    anio_actual_str = str(datetime.now().year)
    anio_anterior_str = str(datetime.now().year - 1)

    return {
        "fecha_generacion": datetime.now().strftime("%d %b %Y %H:%M"),
        "total_ritm": len(ritm_list),
        "total_tasks": len(tasks_list),
        "total_approvals": len(aprob_list),
        "ritm_por_anio": {a: len(v) for a, v in por_anio.items()},
        "sla_prom_por_anio": {a: promedio([r["sla"] for r in v]) for a, v in por_anio.items()},
        "sla_tarea_prom_por_anio": {a: promedio([r["sla_tarea"] for r in v]) for a, v in por_anio.items()},
        "sla_aprob_prom_por_anio": {a: promedio([r["sla_aprob"] for r in v]) for a, v in por_anio.items()},
        "resumen_mes": resumen_mes,
        "por_form_anio": {
            form: {
                anio: {
                    "vol": len(rs),
                    "sla": promedio([r["sla"] for r in rs]),
                    "top3": top_cuellos(rs, 3),
                }
                for anio, rs in anios.items()
            }
            for form, anios in por_form_anio.items()
        },
        "top_cuellos_anio_actual": top_cuellos(por_anio.get(anio_actual_str, []), 20),
        "top_cuellos_anio_anterior": top_cuellos(por_anio.get(anio_anterior_str, []), 20),
        "anio_actual": anio_actual_str,
        "anio_anterior": anio_anterior_str,
    }
