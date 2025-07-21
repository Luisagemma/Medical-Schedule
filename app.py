import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import calendar
import io
from ortools.sat.python import cp_model

def genera_turni(mese, anno):
    start_date = datetime(anno, mese, 1)
    if mese == 12:
        num_days = (datetime(anno + 1, 1, 1) - start_date).days
    else:
        num_days = (datetime(anno, mese + 1, 1) - start_date).days
    dates = [start_date + timedelta(days=i) for i in range(num_days)]

    medici = [
        "Rosanna R.", "Antonella P.", "Valentina B.", "Maddalena B.",
        "Gisella G.", "Suzanne V.", "Marco G.", "Benedetta M.",
        "Giulia T.", "Patrizia C.", "Ludovica M."
    ]

    df_exc = pd.read_csv("eccezioni.csv")

    model = cp_model.CpModel()
    penalità = []
    GG, GN, RG, RN = {}, {}, {}, {}

    for m in medici:
        for d in range(num_days):
            GG[m, d] = model.NewBoolVar(f"GG_{m}_{d}")
            GN[m, d] = model.NewBoolVar(f"GN_{m}_{d}")
            RG[m, d] = model.NewBoolVar(f"RG_{m}_{d}")
            RN[m, d] = model.NewBoolVar(f"RN_{m}_{d}")

    for d in range(num_days):
        model.Add(sum(GG[m, d] for m in medici) == 1)
        model.Add(sum(GN[m, d] for m in medici) == 1)
        model.Add(sum(RN[m, d] for m in medici) == 1)
        if dates[d].weekday() in [5, 6]:
            model.Add(sum(RG[m, d] for m in medici) == 1)
        else:
            for m in medici:
                model.Add(RG[m, d] == 0)

    for m in medici:
        for d in range(num_days):
            model.Add(GG[m, d] + GN[m, d] <= 1)
            model.Add(GG[m, d] + RG[m, d] <= 1)
            model.Add(GN[m, d] + RN[m, d] <= 1)
            if d < num_days - 1:
                model.Add(GG[m, d + 1] == 0).OnlyEnforceIf(GN[m, d])

    for _, row in df_exc.iterrows():
        nome = row["Medico"]
        giorno = int(row["Giorno"]) - 1
        if nome in medici and 0 <= giorno < num_days:
            model.Add(GG[nome, giorno] == 0)
            model.Add(GN[nome, giorno] == 0)
            model.Add(RG[nome, giorno] == 0)
            model.Add(RN[nome, giorno] == 0)

    for d in range(num_days):
        if dates[d] < datetime(2025, 9, 2):
            model.Add(GN["Valentina B.", d] == 0)
            model.Add(RN["Valentina B.", d] == 0)

    for d in range(num_days - 1):
        if dates[d].weekday() == 5:
            for m in medici:
                model.Add(GG[m, d] == GG[m, d + 1])
                model.Add(GN[m, d] == GN[m, d + 1])

    for m in medici:
        for d in range(num_days - 1):
            gg_consec = model.NewBoolVar(f"gg_consec_{m}_{d}")
            model.AddBoolAnd([GG[m, d], GG[m, d + 1]]).OnlyEnforceIf(gg_consec)
            model.AddBoolOr([GG[m, d].Not(), GG[m, d + 1].Not()]).OnlyEnforceIf(gg_consec.Not())
            penalità.append(gg_consec * 5)

            gn_consec = model.NewBoolVar(f"gn_consec_{m}_{d}")
            model.AddBoolAnd([GN[m, d], GN[m, d + 1]]).OnlyEnforceIf(gn_consec)
            model.AddBoolOr([GN[m, d].Not(), GN[m, d + 1].Not()]).OnlyEnforceIf(gn_consec.Not())
            penalità.append(gn_consec * 5)

    for m in medici:
        tot_guardie = [GG[m, d] + GN[m, d] for d in range(num_days)]
        count = model.NewIntVar(0, num_days, f"count_{m}")
        model.Add(count == sum(tot_guardie))

        if m in ["Valentina B.", "Maddalena B.", "Gisella G.", "Suzanne V.", "Marco G.", "Benedetta M.", "Giulia T."]:
            model.Add(count >= 6)
            model.Add(count <= 8)

        if m == "Maddalena B.":
            gn_count = model.NewIntVar(0, num_days, "gn_count_maddalena")
            model.Add(gn_count == sum(GN[m, d] for d in range(num_days)))
            gn_excess = model.NewIntVar(0, num_days, "gn_excess_maddalena")
            model.AddMaxEquality(gn_excess, [gn_count - 4, 0])
            penalità.append(gn_excess * 10)

        if m == "Suzanne V.":
            for d in range(num_days - 1):
                model.AddBoolOr([GN[m, d].Not(), GN[m, d + 1].Not()])
            for d in range(num_days):
                if dates[d].weekday() >= 5:
                    model.Add(GN[m, d] == 0)

        if m == "Patrizia C.":
            weekend_blocks = []
            for d in range(num_days - 1):
                if dates[d].weekday() == 5:
                    weekend_blocks.append(GG[m, d] + GG[m, d + 1] + GN[m, d] + GN[m, d + 1])
            model.Add(sum(weekend_blocks) <= 2)

    for m in ["Rosanna R.", "Antonella P."]:
        for d in range(num_days):
            penalità.append(GG[m, d] * 20)
            penalità.append(GN[m, d] * 20)

    junior = ["Marco G.", "Benedetta M.", "Giulia T."]
    for d in range(num_days):
        for j in junior:
            for j2 in junior:
                if j != j2:
                    model.Add(GN[j, d] + RN[j2, d] <= 1)

    # === BLOCCO WEEKEND ===
    # candidati = [...]  ← NON DEFINITO
    # fallback = [...]   ← NON DEFINITO
    # preferiti = [...]  ← NON DEFINITO
    # Tutto ciò che usa queste liste è COMMENTATO

    # === Funzione obiettivo base ===
    model.Minimize(sum(penalità))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 10.0
    status = solver.Solve(model)

    rows = []
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        for d in range(num_days):
            data = dates[d].strftime("%d-%b-%y")
            giorno = dates[d].strftime("%a").upper()
            gg = next((m for m in medici if solver.Value(GG[m, d])), "")
            gn = next((m for m in medici if solver.Value(GN[m, d])), "")
            smonto = next((m for m in medici if d > 0 and solver.Value(GN[m, d - 1])), "")
            rg = next((m for m in medici if solver.Value(RG[m, d])), "")
            rn = next((m for m in medici if solver.Value(RN[m, d])), "")
            rows.append([data, giorno, gg, gn, smonto, rg, rn])
    else:
        rows.append(["NESSUNA SOLUZIONE", "", "", "", "", "", ""])

    df_out = pd.DataFrame(rows, columns=["Data", "Giorno", "G. Giorno", "G. Notte", "Smonto", "R. Giorno", "R. Notte"])
    return df_out


def scarica_excel(df, mese, anno):
    import openpyxl
    from openpyxl.styles import Font
    import io

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Turni')

        wb = writer.book
        ws = writer.sheets['Turni']

        bold_font = Font(bold=True)

        # Assumiamo che la colonna 'Giorno' sia la seconda (col B)
        # Righe iniziano da 2 perché la 1 è l’header
        for row_idx, day in enumerate(df['Giorno'], start=2):
            if day.strip().upper() in ["SAT", "SUNDAY", "SATURDAY", "SUN", "DOMENICA", "SABATO"]:
                for col_idx in range(1, len(df.columns) + 1):
                    ws.cell(row=row_idx, column=col_idx).font = bold_font

    buffer.seek(0)
    return buffer


st.set_page_config(page_title="Generatore Turni Medici")
st.title("Generatore Turni Medici")

col1, col2 = st.columns(2)
with col1:
    mese = st.selectbox("Scegli il mese", list(range(1, 13)), format_func=lambda x: calendar.month_name[x])
with col2:
    anno = st.number_input("Scegli l'anno", value=datetime.now().year, step=1, min_value=2020)

if st.button("Genera turno"):
    df_turni = genera_turni(mese, anno)
    st.success("Tabella generata.")
    st.dataframe(df_turni, use_container_width=True)

    excel_file = scarica_excel(df_turni, mese, anno)
    st.download_button(
        label="Scarica Excel",
        data=excel_file,
        file_name=f"Turni_{anno}_{mese:02d}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
