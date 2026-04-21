"""
Quattro Tax Consulting — Auto-fill System
Toma datos del cuestionario JotForm y llena los PDFs del IRS automáticamente.
Uso: python quattro_autofill.py <cliente.json> <tipo: individual|empresa>
"""

import json, sys, os, subprocess
from pathlib import Path

# ─────────────────────────────────────────────
# MAPEO: JotForm → Campos IRS
# ─────────────────────────────────────────────

def map_individual_1040(data):
    """
    Mapea respuestas del JotForm Individual → Form 1040 (2025)
    data: dict con las respuestas del cliente
    """
    dep = data.get("dependientes", [])

    def dep_first(i): return dep[i]["nombre"].split()[0] if i < len(dep) else ""
    def dep_last(i):  return " ".join(dep[i]["nombre"].split()[1:]) if i < len(dep) else ""
    def dep_ssn(i):   return dep[i].get("ssn","") if i < len(dep) else ""
    def dep_rel(i):   return dep[i].get("relacion","") if i < len(dep) else ""

    nombre = data.get("nombre","")
    partes = nombre.strip().split()
    first  = partes[0] if partes else ""
    last   = " ".join(partes[1:]) if len(partes) > 1 else ""

    conyuge = data.get("conyuge", {})
    c_nombre = conyuge.get("nombre","")
    c_partes = c_nombre.strip().split()
    c_first  = c_partes[0] if c_partes else ""
    c_last   = " ".join(c_partes[1:]) if len(c_partes) > 1 else ""

    fs = data.get("filing_status", "single")
    # All filing status checkboxes use checked_value "/1"
    filing_checkboxes = {
        "single": "topmostSubform[0].Page1[0].c1_1[0]",
        "mfj":    "topmostSubform[0].Page1[0].c1_2[0]",
        "mfs":    "topmostSubform[0].Page1[0].c1_3[0]",
        "hoh":    "topmostSubform[0].Page1[0].c1_4[0]",
        "qss":    "topmostSubform[0].Page1[0].c1_5[0]",
    }

    fields = [
        # ── DATOS PERSONALES ──────────────────────────────────
        {"field_id": "topmostSubform[0].Page1[0].f1_01[0]",
         "description": "Nombre (first name)", "page": 1, "value": first},
        {"field_id": "topmostSubform[0].Page1[0].f1_02[0]",
         "description": "Apellido (last name)", "page": 1, "value": last},
        {"field_id": "topmostSubform[0].Page1[0].f1_03[0]",
         "description": "SSN del contribuyente", "page": 1, "value": data.get("ssn","")},
        {"field_id": "topmostSubform[0].Page1[0].f1_04[0]",
         "description": "Nombre cónyuge (first)", "page": 1, "value": c_first},
        {"field_id": "topmostSubform[0].Page1[0].f1_05[0]",
         "description": "Apellido cónyuge (last)", "page": 1, "value": c_last},
        {"field_id": "topmostSubform[0].Page1[0].f1_06[0]",
         "description": "SSN del cónyuge", "page": 1, "value": conyuge.get("ssn","")},
        # ── DIRECCIÓN ─────────────────────────────────────────
        {"field_id": "topmostSubform[0].Page1[0].Address_ReadOrder[0].f1_20[0]",
         "description": "Calle y número", "page": 1, "value": data.get("address","")},
        {"field_id": "topmostSubform[0].Page1[0].Address_ReadOrder[0].f1_22[0]",
         "description": "Ciudad", "page": 1, "value": data.get("city","")},
        {"field_id": "topmostSubform[0].Page1[0].Address_ReadOrder[0].f1_23[0]",
         "description": "Estado", "page": 1, "value": data.get("state","")},
        {"field_id": "topmostSubform[0].Page1[0].Address_ReadOrder[0].f1_24[0]",
         "description": "ZIP code", "page": 1, "value": data.get("zip","")},
        # ── FILING STATUS ─────────────────────────────────────
        {"field_id": filing_checkboxes.get(fs, filing_checkboxes["single"]),
         "description": f"Filing status: {fs}", "page": 1, "value": "/1"},
        # ── DEPENDIENTES ─────────────────────────────────────
        {"field_id": "topmostSubform[0].Page1[0].Table_Dependents[0].Row1[0].f1_31[0]",
         "description": "Dep 1 first name", "page": 1, "value": dep_first(0)},
        {"field_id": "topmostSubform[0].Page1[0].Table_Dependents[0].Row1[0].f1_32[0]",
         "description": "Dep 1 last name", "page": 1, "value": dep_last(0)},
        {"field_id": "topmostSubform[0].Page1[0].Table_Dependents[0].Row1[0].f1_33[0]",
         "description": "Dep 1 SSN", "page": 1, "value": dep_ssn(0)},
        {"field_id": "topmostSubform[0].Page1[0].Table_Dependents[0].Row1[0].f1_34[0]",
         "description": "Dep 1 relación", "page": 1, "value": dep_rel(0)},
        {"field_id": "topmostSubform[0].Page1[0].Table_Dependents[0].Row2[0].f1_35[0]",
         "description": "Dep 2 first name", "page": 1, "value": dep_first(1)},
        {"field_id": "topmostSubform[0].Page1[0].Table_Dependents[0].Row2[0].f1_36[0]",
         "description": "Dep 2 last name", "page": 1, "value": dep_last(1)},
        {"field_id": "topmostSubform[0].Page1[0].Table_Dependents[0].Row2[0].f1_37[0]",
         "description": "Dep 2 SSN", "page": 1, "value": dep_ssn(1)},
        {"field_id": "topmostSubform[0].Page1[0].Table_Dependents[0].Row2[0].f1_38[0]",
         "description": "Dep 2 relación", "page": 1, "value": dep_rel(1)},
        {"field_id": "topmostSubform[0].Page1[0].Table_Dependents[0].Row3[0].f1_39[0]",
         "description": "Dep 3 first name", "page": 1, "value": dep_first(2)},
        {"field_id": "topmostSubform[0].Page1[0].Table_Dependents[0].Row3[0].f1_40[0]",
         "description": "Dep 3 last name", "page": 1, "value": dep_last(2)},
        {"field_id": "topmostSubform[0].Page1[0].Table_Dependents[0].Row3[0].f1_41[0]",
         "description": "Dep 3 SSN", "page": 1, "value": dep_ssn(2)},
        {"field_id": "topmostSubform[0].Page1[0].Table_Dependents[0].Row3[0].f1_42[0]",
         "description": "Dep 3 relación", "page": 1, "value": dep_rel(2)},
        {"field_id": "topmostSubform[0].Page1[0].Table_Dependents[0].Row4[0].f1_43[0]",
         "description": "Dep 4 first name", "page": 1, "value": dep_first(3)},
        {"field_id": "topmostSubform[0].Page1[0].Table_Dependents[0].Row4[0].f1_44[0]",
         "description": "Dep 4 last name", "page": 1, "value": dep_last(3)},
        {"field_id": "topmostSubform[0].Page1[0].Table_Dependents[0].Row4[0].f1_45[0]",
         "description": "Dep 4 SSN", "page": 1, "value": dep_ssn(3)},
        {"field_id": "topmostSubform[0].Page1[0].Table_Dependents[0].Row4[0].f1_46[0]",
         "description": "Dep 4 relación", "page": 1, "value": dep_rel(3)},
        # ── INGRESOS (página 1) ───────────────────────────────
        {"field_id": "topmostSubform[0].Page1[0].f1_49[0]",
         "description": "Línea 1a W-2 wages", "page": 1, "value": data.get("w2_wages","")},
        {"field_id": "topmostSubform[0].Page1[0].f1_51[0]",
         "description": "Línea 1z total wages", "page": 1, "value": data.get("w2_wages","")},
        {"field_id": "topmostSubform[0].Page1[0].f1_54[0]",
         "description": "Línea 2b taxable interest", "page": 1, "value": data.get("taxable_interest","")},
        {"field_id": "topmostSubform[0].Page1[0].f1_56[0]",
         "description": "Línea 3b ordinary dividends", "page": 1, "value": data.get("ordinary_dividends","")},
        # ── DEPÓSITO DIRECTO (página 2) ───────────────────────
        {"field_id": "topmostSubform[0].Page2[0].f2_17[0]",
         "description": "Routing number", "page": 2, "value": data.get("routing_number","")},
        {"field_id": "topmostSubform[0].Page2[0].f2_18[0]",
         "description": "Account number", "page": 2, "value": data.get("account_number","")},
        # ── PREPARADOR ────────────────────────────────────────
        {"field_id": "topmostSubform[0].Page2[0].f2_28[0]",
         "description": "Preparer name", "page": 2, "value": data.get("preparer_name","Quattro Tax Consulting")},
        {"field_id": "topmostSubform[0].Page2[0].f2_30[0]",
         "description": "Firm name", "page": 2, "value": "Quattro Tax Consulting"},
        {"field_id": "topmostSubform[0].Page2[0].f2_31[0]",
         "description": "Firm phone", "page": 2, "value": data.get("firm_phone","")},
        {"field_id": "topmostSubform[0].Page2[0].f2_32[0]",
         "description": "Firm address", "page": 2, "value": data.get("firm_address","")},
    ]
    return [f for f in fields if f["value"]]


def map_schedule_c(data):
    """
    Mapea datos del negocio → Schedule C (2025)
    Usado para Sole Proprietors y LLC single-member
    """
    negocio = data.get("negocio", {})
    fields = [
        {"field_id": "topmostSubform[0].Page1[0].f1_2[0]",
         "description": "Nombre del propietario", "page": 1,
         "value": data.get("nombre","")},
        {"field_id": "topmostSubform[0].Page1[0].f1_1[0]",
         "description": "SSN del propietario", "page": 1,
         "value": data.get("ssn","")},
        {"field_id": "topmostSubform[0].Page1[0].BComb[0].f1_4[0]",
         "description": "Línea A - Tipo de negocio", "page": 1,
         "value": negocio.get("tipo","")},
        {"field_id": "topmostSubform[0].Page1[0].f1_3[0]",
         "description": "Línea C - Nombre del negocio", "page": 1,
         "value": negocio.get("nombre","")},
        {"field_id": "topmostSubform[0].Page1[0].DComb[0].f1_6[0]",
         "description": "Línea D - EIN", "page": 1,
         "value": negocio.get("ein","")},
        {"field_id": "topmostSubform[0].Page1[0].f1_7[0]",
         "description": "Línea E - Dirección del negocio", "page": 1,
         "value": negocio.get("address","")},
        # ── INGRESOS ──────────────────────────────────────────
        {"field_id": "topmostSubform[0].Page1[0].f1_10[0]",
         "description": "Línea 1 - Gross receipts", "page": 1,
         "value": negocio.get("gross_receipts","")},
        {"field_id": "topmostSubform[0].Page1[0].f1_11[0]",
         "description": "Línea 2 - Returns & allowances", "page": 1,
         "value": negocio.get("returns","")},
        {"field_id": "topmostSubform[0].Page1[0].f1_13[0]",
         "description": "Línea 4 - COGS", "page": 1,
         "value": negocio.get("cogs","")},
        # ── GASTOS ────────────────────────────────────────────
        {"field_id": "topmostSubform[0].Page1[0].Lines8-17[0].f1_17[0]",
         "description": "Línea 8 - Advertising", "page": 1,
         "value": negocio.get("advertising","")},
        {"field_id": "topmostSubform[0].Page1[0].Lines8-17[0].f1_18[0]",
         "description": "Línea 9 - Car/truck expenses", "page": 1,
         "value": negocio.get("car_expenses","")},
        {"field_id": "topmostSubform[0].Page1[0].Lines8-17[0].f1_19[0]",
         "description": "Línea 10 - Commissions", "page": 1,
         "value": negocio.get("commissions","")},
        {"field_id": "topmostSubform[0].Page1[0].Lines8-17[0].f1_20[0]",
         "description": "Línea 11 - Contract labor", "page": 1,
         "value": negocio.get("contract_labor","")},
        {"field_id": "topmostSubform[0].Page1[0].Lines8-17[0].f1_22[0]",
         "description": "Línea 13 - Depreciation §179", "page": 1,
         "value": negocio.get("depreciation","")},
        {"field_id": "topmostSubform[0].Page1[0].Lines8-17[0].f1_24[0]",
         "description": "Línea 15 - Insurance", "page": 1,
         "value": negocio.get("insurance","")},
        {"field_id": "topmostSubform[0].Page1[0].Lines8-17[0].f1_26[0]",
         "description": "Línea 16b - Other interest", "page": 1,
         "value": negocio.get("interest","")},
        {"field_id": "topmostSubform[0].Page1[0].Lines8-17[0].f1_27[0]",
         "description": "Línea 17 - Legal & professional", "page": 1,
         "value": negocio.get("legal_prof","")},
        {"field_id": "topmostSubform[0].Page1[0].Lines18-27[0].f1_28[0]",
         "description": "Línea 18 - Office expense", "page": 1,
         "value": negocio.get("office_exp","")},
        {"field_id": "topmostSubform[0].Page1[0].Lines18-27[0].f1_30[0]",
         "description": "Línea 20b - Rent/lease property", "page": 1,
         "value": negocio.get("rent","")},
        {"field_id": "topmostSubform[0].Page1[0].Lines18-27[0].f1_31[0]",
         "description": "Línea 21 - Repairs & maintenance", "page": 1,
         "value": negocio.get("repairs","")},
        {"field_id": "topmostSubform[0].Page1[0].Lines18-27[0].f1_32[0]",
         "description": "Línea 22 - Supplies", "page": 1,
         "value": negocio.get("supplies","")},
        {"field_id": "topmostSubform[0].Page1[0].Lines18-27[0].f1_33[0]",
         "description": "Línea 23 - Taxes & licenses", "page": 1,
         "value": negocio.get("taxes_licenses","")},
        {"field_id": "topmostSubform[0].Page1[0].Lines18-27[0].f1_34[0]",
         "description": "Línea 24a - Travel", "page": 1,
         "value": negocio.get("travel","")},
        {"field_id": "topmostSubform[0].Page1[0].Lines18-27[0].f1_35[0]",
         "description": "Línea 24b - Meals (50%)", "page": 1,
         "value": negocio.get("meals","")},
        {"field_id": "topmostSubform[0].Page1[0].Lines18-27[0].f1_36[0]",
         "description": "Línea 25 - Utilities", "page": 1,
         "value": negocio.get("utilities","")},
        {"field_id": "topmostSubform[0].Page1[0].Lines18-27[0].f1_37[0]",
         "description": "Línea 26 - Wages", "page": 1,
         "value": negocio.get("wages","")},
        {"field_id": "topmostSubform[0].Page1[0].Lines18-27[0].f1_40[0]",
         "description": "Línea 27b - Other expenses", "page": 1,
         "value": negocio.get("other_expenses","")},
    ]
    return [f for f in fields if f["value"]]


def map_1120s(data):
    """Mapea datos de S-Corporation → Form 1120-S"""
    empresa = data.get("empresa", {})
    fields = [
        {"field_id": "topmostSubform[0].Page1[0].f1_1[0]",
         "description": "Nombre de la corporación", "page": 1,
         "value": empresa.get("nombre","")},
        {"field_id": "topmostSubform[0].Page1[0].f1_2[0]",
         "description": "Número y calle", "page": 1,
         "value": empresa.get("address","")},
        {"field_id": "topmostSubform[0].Page1[0].f1_6[0]",
         "description": "EIN", "page": 1,
         "value": empresa.get("ein","")},
        # Ingresos
        {"field_id": "topmostSubform[0].Page1[0].f1_10[0]",
         "description": "Línea 1a - Gross receipts", "page": 1,
         "value": empresa.get("gross_receipts","")},
        {"field_id": "topmostSubform[0].Page1[0].f1_12[0]",
         "description": "Línea 2 - COGS", "page": 1,
         "value": empresa.get("cogs","")},
        # Deducciones
        {"field_id": "topmostSubform[0].Page1[0].f1_16[0]",
         "description": "Línea 7 - Compensation of officers", "page": 1,
         "value": empresa.get("officer_comp","")},
        {"field_id": "topmostSubform[0].Page1[0].f1_17[0]",
         "description": "Línea 8 - Salaries & wages", "page": 1,
         "value": empresa.get("wages","")},
        {"field_id": "topmostSubform[0].Page1[0].f1_18[0]",
         "description": "Línea 9 - Repairs", "page": 1,
         "value": empresa.get("repairs","")},
        {"field_id": "topmostSubform[0].Page1[0].f1_20[0]",
         "description": "Línea 11 - Rents", "page": 1,
         "value": empresa.get("rent","")},
        {"field_id": "topmostSubform[0].Page1[0].f1_21[0]",
         "description": "Línea 12 - Taxes & licenses", "page": 1,
         "value": empresa.get("taxes_licenses","")},
        {"field_id": "topmostSubform[0].Page1[0].f1_22[0]",
         "description": "Línea 13 - Interest", "page": 1,
         "value": empresa.get("interest","")},
        {"field_id": "topmostSubform[0].Page1[0].f1_23[0]",
         "description": "Línea 14 - Depreciation", "page": 1,
         "value": empresa.get("depreciation","")},
        {"field_id": "topmostSubform[0].Page1[0].f1_25[0]",
         "description": "Línea 16 - Advertising", "page": 1,
         "value": empresa.get("advertising","")},
        {"field_id": "topmostSubform[0].Page1[0].f1_29[0]",
         "description": "Línea 20 - Other deductions", "page": 1,
         "value": empresa.get("other_deductions","")},
    ]
    return [f for f in fields if f["value"]]


def map_1065(data):
    """Mapea datos de Partnership/LLC multi-member → Form 1065"""
    empresa = data.get("empresa", {})
    fields = [
        {"field_id": "topmostSubform[0].Page1[0].f1_1[0]",
         "description": "Nombre del partnership", "page": 1,
         "value": empresa.get("nombre","")},
        {"field_id": "topmostSubform[0].Page1[0].f1_5[0]",
         "description": "EIN", "page": 1,
         "value": empresa.get("ein","")},
        {"field_id": "topmostSubform[0].Page1[0].f1_9[0]",
         "description": "Línea 1a - Gross receipts", "page": 1,
         "value": empresa.get("gross_receipts","")},
        {"field_id": "topmostSubform[0].Page1[0].f1_11[0]",
         "description": "Línea 2 - COGS", "page": 1,
         "value": empresa.get("cogs","")},
        {"field_id": "topmostSubform[0].Page1[0].f1_14[0]",
         "description": "Línea 9 - Salaries & wages", "page": 1,
         "value": empresa.get("wages","")},
        {"field_id": "topmostSubform[0].Page1[0].f1_16[0]",
         "description": "Línea 11 - Repairs", "page": 1,
         "value": empresa.get("repairs","")},
        {"field_id": "topmostSubform[0].Page1[0].f1_17[0]",
         "description": "Línea 12 - Bad debts", "page": 1,
         "value": empresa.get("bad_debts","")},
        {"field_id": "topmostSubform[0].Page1[0].f1_18[0]",
         "description": "Línea 13 - Rent", "page": 1,
         "value": empresa.get("rent","")},
        {"field_id": "topmostSubform[0].Page1[0].f1_19[0]",
         "description": "Línea 14 - Taxes & licenses", "page": 1,
         "value": empresa.get("taxes_licenses","")},
        {"field_id": "topmostSubform[0].Page1[0].f1_20[0]",
         "description": "Línea 15 - Interest", "page": 1,
         "value": empresa.get("interest","")},
        {"field_id": "topmostSubform[0].Page1[0].f1_23[0]",
         "description": "Línea 18 - Retirement plans", "page": 1,
         "value": empresa.get("retirement","")},
        {"field_id": "topmostSubform[0].Page1[0].f1_26[0]",
         "description": "Línea 21 - Other deductions", "page": 1,
         "value": empresa.get("other_deductions","")},
    ]
    return [f for f in fields if f["value"]]


def map_8962(data):
    """Mapea datos de Obama Care 1095-A → Form 8962"""
    obamacare = data.get("obamacare", {})
    fields = [
        {"field_id": "topmostSubform[0].Page1[0].f1_1[0]",
         "description": "SSN", "page": 1, "value": data.get("ssn","")},
        {"field_id": "topmostSubform[0].Page1[0].f1_2[0]",
         "description": "Tax family size", "page": 1,
         "value": str(obamacare.get("family_size",""))},
        {"field_id": "topmostSubform[0].Page1[0].f1_3[0]",
         "description": "Línea 2a - Modified AGI", "page": 1,
         "value": str(obamacare.get("magi",""))},
        {"field_id": "topmostSubform[0].Page1[0].f1_6[0]",
         "description": "Línea 4 - Federal poverty line", "page": 1,
         "value": str(obamacare.get("poverty_line",""))},
        # Annual totals de la 1095-A
        {"field_id": "topmostSubform[0].Page1[0].Table_Annual[0].f1_15[0]",
         "description": "Línea 11a - Annual enrollment premiums", "page": 1,
         "value": str(obamacare.get("annual_premiums",""))},
        {"field_id": "topmostSubform[0].Page1[0].Table_Annual[0].f1_16[0]",
         "description": "Línea 11b - Annual SLCSP premium", "page": 1,
         "value": str(obamacare.get("annual_slcsp",""))},
        {"field_id": "topmostSubform[0].Page1[0].Table_Annual[0].f1_18[0]",
         "description": "Línea 11f - Advance payment of PTC", "page": 1,
         "value": str(obamacare.get("advance_ptc",""))},
    ]
    return [f for f in fields if f["value"]]


# ─────────────────────────────────────────────
# MOTOR DE LLENADO
# ─────────────────────────────────────────────

def fill_form(input_pdf, field_values, output_pdf, scripts_dir="."):
    """Llena un PDF usando el script del skill"""
    values_file = output_pdf.replace(".pdf", "_values.json")
    with open(values_file, "w") as f:
        json.dump(field_values, f, indent=2)

    result = subprocess.run(
        ["python", f"{scripts_dir}/fill_fillable_fields.py",
         input_pdf, values_file, output_pdf],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"  ⚠️  Advertencia en {output_pdf}: {result.stderr[:200]}")
    else:
        print(f"  ✅ Generado: {output_pdf}")
    os.remove(values_file)
    return result.returncode == 0


def determinar_forms(data, tipo):
    """Determina qué forms llenar según el tipo y situaciones del cliente"""
    forms = []
    ingresos = data.get("ingresos_marcados", [])
    situaciones = data.get("situaciones_marcadas", [])

    if tipo == "individual":
        forms.append("1040")
        if any(x in ingresos for x in ["1099-NEC", "negocio propio", "self-employed"]):
            forms.append("schedule_c")
        if any(x in ingresos for x in ["renta", "rental", "S corporation", "partnership", "K-1"]):
            forms.append("schedule_e")
        if any(x in situaciones for x in ["1095A", "Obama Care", "1095-A"]):
            forms.append("8962")
        if any(x in ingresos for x in ["cripto", "criptomoneda", "venta acciones", "dividendos"]):
            forms.append("schedule_d")

    elif tipo == "empresa":
        entidad = data.get("empresa", {}).get("tipo_entidad", "").lower()
        if "s-corp" in entidad or "s corp" in entidad:
            forms.append("1120s")
        elif "c-corp" in entidad or "c corp" in entidad:
            forms.append("1120")
        elif "partnership" in entidad or "multi" in entidad:
            forms.append("1065")
        else:
            forms.append("1120s")
        # Texas siempre requerido para empresas en Texas
        if data.get("declaracion_estatal", True) or data.get("franchise_tax", True):
            revenue = float(data.get("empresa", {}).get("gross_receipts", 0))
            if revenue > 2470000:
                forms.append("tx_05158a")
            forms.append("tx_05102")  # PIR siempre requerido

    return forms


def generar_paquete_cliente(data_file, tipo, output_dir="output"):
    """
    Función principal: genera todos los PDFs para un cliente
    """
    with open(data_file) as f:
        data = json.load(f)

    cliente = data.get("nombre") or data.get("empresa", {}).get("nombre","cliente")
    cliente_clean = cliente.replace(" ","_").replace("/","_")
    os.makedirs(output_dir, exist_ok=True)

    print(f"\n{'='*50}")
    print(f"  Quattro Tax — Generando paquete para: {cliente}")
    print(f"  Tipo: {tipo.upper()}")
    print(f"{'='*50}")

    forms_a_llenar = determinar_forms(data, tipo)
    print(f"\n  Forms identificados: {', '.join(forms_a_llenar)}")
    print()

    pdf_dir = Path(__file__).parent

    form_map = {
        "1040":        (str(pdf_dir/"f1040.pdf"),    map_individual_1040, "Form_1040"),
        "schedule_c":  (str(pdf_dir/"f1040sc.pdf"),  map_schedule_c,      "Schedule_C"),
        "schedule_e":  (str(pdf_dir/"f1040se.pdf"),  lambda d: [],        "Schedule_E"),
        "schedule_d":  (str(pdf_dir/"f1040sd.pdf"),  lambda d: [],        "Schedule_D"),
        "8962":        (str(pdf_dir/"f8962.pdf"),    map_8962,            "Form_8962"),
        "1120s":       (str(pdf_dir/"f1120s.pdf"),   map_1120s,           "Form_1120S"),
        "1120":        (str(pdf_dir/"f1120.pdf"),    lambda d: [],        "Form_1120"),
        "1065":        (str(pdf_dir/"f1065.pdf"),    map_1065,            "Form_1065"),
        # Texas — se llenan como annotations sobre el PDF base
        "tx_05158a":   (str(pdf_dir/"f1120s.pdf"),   map_texas_05158a,   "TX_Franchise_05158A"),
        "tx_05102":    (str(pdf_dir/"f1120s.pdf"),    map_texas_05102,    "TX_PIR_05102"),
    }

    generados = []
    for form_key in forms_a_llenar:
        if form_key not in form_map:
            continue
        input_pdf, mapper, label = form_map[form_key]
        if not os.path.exists(input_pdf):
            print(f"  ❌ PDF no encontrado: {input_pdf}")
            continue
        field_values = mapper(data)
        if not field_values:
            print(f"  ⚠️  {label}: sin datos para llenar, copiando en blanco")
            import shutil
            out = f"{output_dir}/{cliente_clean}_{label}.pdf"
            shutil.copy(input_pdf, out)
            generados.append(out)
            continue
        out = f"{output_dir}/{cliente_clean}_{label}.pdf"
        fill_form(input_pdf, field_values, out, scripts_dir=str(pdf_dir))
        generados.append(out)

    print(f"\n  📁 Paquete completo en: {output_dir}/")
    print(f"  📄 {len(generados)} PDFs generados:")
    for g in generados:
        print(f"     • {os.path.basename(g)}")
    print()
    return generados


# ─────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python quattro_autofill.py <cliente.json> <individual|empresa>")
        print("\nEjemplo:")
        print("  python quattro_autofill.py maria_gonzalez.json individual")
        print("  python quattro_autofill.py restaurante_el_sol.json empresa")
        sys.exit(1)

    data_file = sys.argv[1]
    tipo = sys.argv[2].lower()
    output_dir = sys.argv[3] if len(sys.argv) > 3 else "output"
    generar_paquete_cliente(data_file, tipo, output_dir)


def map_texas_05158a(data):
    """
    Mapea datos de empresa → Texas Franchise Tax Report 05-158-A (2026)
    Para empresas con ingresos > $2.47M en Texas
    """
    empresa = data.get("empresa", {})
    
    # Texas margin tax: revenue - COGS (o compensation, lo que sea mayor)
    total_revenue = float(empresa.get("gross_receipts", 0))
    cogs = float(empresa.get("cogs", 0))
    compensation = float(empresa.get("wages", 0)) + float(empresa.get("officer_comp", 0))
    
    # Margin = revenue - mayor deducción (COGS o compensation), mínimo 70% de revenue
    deduction = max(cogs, compensation)
    margin = max(total_revenue - deduction, total_revenue * 0.70)
    
    # Texas tax rate: 0.75% para mayoría de negocios, 0.375% para retail/wholesale
    tx_rate = 0.0075
    tx_tax = margin * tx_rate
    
    fields = [
        # ── IDENTIFICACIÓN ────────────────────────────────────
        {"field_id": "Taxpayer_Name",
         "description": "Nombre del contribuyente", "page": 1,
         "value": empresa.get("nombre", "")},
        {"field_id": "Taxpayer_Number",
         "description": "Texas Taxpayer Number (11 dígitos)", "page": 1,
         "value": empresa.get("texas_taxpayer_number", "")},
        {"field_id": "Report_Year",
         "description": "Año del reporte", "page": 1,
         "value": "2026"},
        {"field_id": "Accounting_Year_Begin",
         "description": "Inicio del año contable", "page": 1,
         "value": "01/01/2025"},
        {"field_id": "Accounting_Year_End",
         "description": "Fin del año contable", "page": 1,
         "value": "12/31/2025"},
        {"field_id": "Mailing_Address",
         "description": "Dirección postal", "page": 1,
         "value": empresa.get("address", "")},
        {"field_id": "SIC_Code",
         "description": "SIC/NAICS code", "page": 1,
         "value": empresa.get("sic_code", "5812")},  # 5812 = restaurantes

        # ── REVENUE ───────────────────────────────────────────
        {"field_id": "Total_Revenue",
         "description": "Total revenue (suma de todos los ingresos)", "page": 1,
         "value": str(round(total_revenue))},
        {"field_id": "COGS_Deduction",
         "description": "Cost of goods sold deduction", "page": 1,
         "value": str(round(cogs))},
        {"field_id": "Compensation_Deduction",
         "description": "Compensation deduction (wages + officer comp)", "page": 1,
         "value": str(round(compensation))},
        {"field_id": "Margin",
         "description": "Taxable margin (revenue - mayor deducción)", "page": 1,
         "value": str(round(margin))},
        {"field_id": "Texas_Gross_Receipts",
         "description": "Texas gross receipts (ingresos en Texas)", "page": 1,
         "value": str(round(total_revenue))},
        {"field_id": "Apportionment_Factor",
         "description": "Factor de apportionment (Texas/Total)", "page": 1,
         "value": "1.0000"},  # Si todo es en Texas
        {"field_id": "Apportioned_Margin",
         "description": "Margin × Apportionment factor", "page": 1,
         "value": str(round(margin))},

        # ── TAX CALCULATION ───────────────────────────────────
        {"field_id": "Tax_Rate",
         "description": "Tax rate (0.75% general / 0.375% retail)", "page": 1,
         "value": "0.0075"},
        {"field_id": "Tax_Due",
         "description": "Franchise tax due antes de créditos", "page": 1,
         "value": str(round(tx_tax, 2))},
        {"field_id": "Total_Tax_Due",
         "description": "Total franchise tax due", "page": 1,
         "value": str(round(tx_tax, 2))},
    ]
    return [f for f in fields if f["value"]]


def map_texas_05102(data):
    """
    Mapea datos → Texas Franchise Tax Public Information Report 05-102 (2026)
    Requerido para todas las LLCs y Corporations en Texas
    """
    empresa = data.get("empresa", {})
    socios = data.get("socios", [])
    oficiales = data.get("oficiales", [])
    
    fields = [
        # ── DATOS DE LA ENTIDAD ───────────────────────────────
        {"field_id": "Taxpayer_Name",
         "description": "Nombre legal de la entidad", "page": 1,
         "value": empresa.get("nombre", "")},
        {"field_id": "Taxpayer_Number",
         "description": "Texas Taxpayer Number", "page": 1,
         "value": empresa.get("texas_taxpayer_number", "")},
        {"field_id": "Report_Year",
         "description": "Año del reporte", "page": 1,
         "value": "2026"},
        {"field_id": "Registered_Agent_Name",
         "description": "Nombre del registered agent en Texas", "page": 1,
         "value": empresa.get("registered_agent", "")},
        {"field_id": "Registered_Agent_Address",
         "description": "Dirección del registered agent", "page": 1,
         "value": empresa.get("registered_agent_address", "")},
        {"field_id": "Principal_Office_Address",
         "description": "Dirección de la oficina principal", "page": 1,
         "value": empresa.get("address", "")},
        {"field_id": "Principal_Business_Activity",
         "description": "Actividad principal del negocio", "page": 1,
         "value": empresa.get("actividad", "Restaurant")},
        {"field_id": "SIC_Code",
         "description": "SIC/NAICS code", "page": 1,
         "value": empresa.get("sic_code", "5812")},
    ]

    # Oficiales / directores (hasta 3 en la forma estándar)
    officer_labels = [
        ("President_Name", "President_Title", "President_Address"),
        ("Officer2_Name", "Officer2_Title", "Officer2_Address"),
        ("Officer3_Name", "Officer3_Title", "Officer3_Address"),
    ]
    for i, oficial in enumerate(oficiales[:3]):
        name_field, title_field, addr_field = officer_labels[i]
        fields += [
            {"field_id": name_field, "description": f"Oficial {i+1} nombre",
             "page": 1, "value": oficial.get("nombre", "")},
            {"field_id": title_field, "description": f"Oficial {i+1} título",
             "page": 1, "value": oficial.get("titulo", "")},
            {"field_id": addr_field, "description": f"Oficial {i+1} dirección",
             "page": 1, "value": oficial.get("address", "")},
        ]

    # Miembros/socios (para LLCs)
    member_labels = [
        ("Member1_Name", "Member1_Title", "Member1_Address"),
        ("Member2_Name", "Member2_Title", "Member2_Address"),
        ("Member3_Name", "Member3_Title", "Member3_Address"),
    ]
    for i, socio in enumerate(socios[:3]):
        name_field, title_field, addr_field = member_labels[i]
        fields += [
            {"field_id": name_field, "description": f"Miembro {i+1} nombre",
             "page": 1, "value": socio.get("nombre", "")},
            {"field_id": title_field, "description": f"Miembro {i+1} título",
             "page": 1, "value": socio.get("titulo", "Member")},
            {"field_id": addr_field, "description": f"Miembro {i+1} dirección",
             "page": 1, "value": socio.get("address", "")},
        ]

    return [f for f in fields if f["value"]]
