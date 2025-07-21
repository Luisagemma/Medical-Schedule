import streamlit as st
import pandas as pd
from datetime import datetime
import calendar
import io

def genera_tabella(mese, anno):
    giorni = calendar.monthrange(anno, mese)[1]
    date = pd.date_range(start=datetime(anno, mese, 1), periods=giorni)
    df = pd.DataFrame({
        'Data': date,
        'Giorno': date.strftime('%A'),
        'Guardia Giorno': ['—'] * giorni,
        'Guardia Notte': ['—'] * giorni,
        'Reperibile Giorno': ['—'] * giorni,
        'Reperibile Notte': ['—'] * giorni
    })
    return df

def scarica_excel(df, mese, anno):
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Turni')
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
    df_turni = genera_tabella(mese, anno)
    st.success("Tabella generata.")
    st.dataframe(df_turni, use_container_width=True)

    excel_file = scarica_excel(df_turni, mese, anno)
    st.download_button(
        label="Scarica Excel",
        data=excel_file,
        file_name=f"Turni_{anno}_{mese:02d}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
