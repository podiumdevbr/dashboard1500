import io
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Dashboard de Ligações", page_icon="☎️", layout="wide")

st.title("☎️ Dashboard de Ligações — Ramal 3512-1500")
st.caption("Consulta e análise dos registros de chamadas da central telefônica.")

@st.cache_data
def load_data(uploaded_file):
    if uploaded_file is not None:
        df = pd.read_excel(uploaded_file, sheet_name="Ligações")
    else:
        path = Path("ligacoes_ramal_1500.xlsx")
        if not path.exists():
            return None
        df = pd.read_excel(path, sheet_name="Ligações")

    df.columns = [str(c).strip() for c in df.columns]
    df["Data"] = pd.to_datetime(df["Data"], errors="coerce")
    # A coluna Hora pode vir como texto ou como valor de hora do Excel.
    df["Hora"] = df["Hora"].astype(str).str.replace(r"^0 days ", "", regex=True)
    df["Hora_dt"] = pd.to_datetime(df["Hora"], format="%H:%M:%S", errors="coerce")
    df["Hora_num"] = df["Hora_dt"].dt.hour
    df["Tempo_segundos"] = pd.to_timedelta(df["Tempo da ligação"], errors="coerce").dt.total_seconds()
    df["Tempo_segundos"] = df["Tempo_segundos"].where(df["Tempo_segundos"] >= 0)
    for col in ["Número de origem", "Número de destino", "Ramal direcionado", "Status da ligação", "Observação"]:
        if col in df:
            df[col] = df[col].fillna("").astype(str).str.strip()
    return df

st.sidebar.header("Dados")
uploaded = st.sidebar.file_uploader("Carregar planilha Excel (.xlsx)", type=["xlsx"])
df = load_data(uploaded)

if df is None:
    st.info("Coloque o arquivo **ligacoes_ramal_1500.xlsx** na mesma pasta deste aplicativo ou carregue-o pelo campo acima.")
    st.stop()

if df["Data"].notna().sum() == 0:
    st.error("Não foi possível reconhecer a coluna Data da planilha.")
    st.stop()

min_data = df["Data"].min().date()
max_data = df["Data"].max().date()
# O período solicitado pelo usuário é usado como padrão quando está contido na base.
default_start = max(min_data, pd.Timestamp("2026-09-24").date())
default_end = min(max_data, pd.Timestamp("2026-10-06").date())
if default_start > default_end:
    default_start, default_end = min_data, max_data

st.sidebar.subheader("Filtros")
periodo = st.sidebar.date_input(
    "Período",
    value=(default_start, default_end),
    min_value=min_data,
    max_value=max_data,
    format="DD/MM/YYYY",
)
if isinstance(periodo, (tuple, list)) and len(periodo) == 2:
    inicio, fim = periodo
else:
    inicio = fim = periodo

statuses = sorted([s for s in df["Status da ligação"].dropna().unique() if s])
selected_status = st.sidebar.multiselect("Status da ligação", statuses, default=statuses)
ramais = sorted([r for r in df["Ramal direcionado"].dropna().unique() if r and r != "—"])
selected_ramais = st.sidebar.multiselect("Ramal direcionado", ramais, default=ramais)
busca = st.sidebar.text_input("Buscar telefone (origem ou destino)").strip()

mask = df["Data"].dt.date.between(inicio, fim)
mask &= df["Status da ligação"].isin(selected_status)
if selected_ramais:
    mask &= df["Ramal direcionado"].isin(selected_ramais) | df["Ramal direcionado"].eq("—")
else:
    mask &= df["Ramal direcionado"].eq("—")
if busca:
    mask &= (
        df["Número de origem"].str.contains(busca, case=False, na=False, regex=False)
        | df["Número de destino"].str.contains(busca, case=False, na=False, regex=False)
    )
f = df.loc[mask].copy()

# Nota sobre os dados de origem, útil para evitar confusão com o intervalo solicitado.
extra = df.loc[~df["Data"].dt.date.between(pd.Timestamp("2026-09-24").date(), pd.Timestamp("2026-10-06").date())]
if not extra.empty:
    st.info(f"A planilha contém {len(extra)} registro(s) fora do período informado (24/09 a 06/10/2026). Ajuste o filtro de período para consultá-los.")

total = len(f)
atendidas = int((f["Status da ligação"] == "atendida").sum())
nao_atendidas = int((f["Status da ligação"] == "não atendida").sum())
ocupado = int((f["Status da ligação"] == "ocupado").sum())
taxa = atendidas / total * 100 if total else 0
duracao = f.loc[f["Status da ligação"] == "atendida", "Tempo_segundos"].dropna()
duracao_media = duracao.mean() if len(duracao) else 0

def fmt_duracao(seg):
    seg = int(round(seg or 0))
    return f"{seg // 60:02d}:{seg % 60:02d}"

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total de ligações", f"{total:,}".replace(",", "."))
c2.metric("Atendidas", f"{atendidas:,}".replace(",", "."))
c3.metric("Não atendidas", f"{nao_atendidas:,}".replace(",", "."))
c4.metric("Taxa de atendimento", f"{taxa:.1f}%".replace(".", ","))
c5.metric("Duração média atendida", fmt_duracao(duracao_media), help="Formato mm:ss")

st.divider()
if f.empty:
    st.warning("Nenhum registro encontrado com os filtros selecionados.")
    st.stop()

left, right = st.columns(2)
with left:
    daily = f.groupby([f["Data"].dt.date, "Status da ligação"]).size().reset_index(name="Ligações")
    daily = daily.rename(columns={"Data": "Data"})
    fig = px.bar(daily, x="Data", y="Ligações", color="Status da ligação", barmode="stack",
                 title="Ligações por dia e status", category_orders={"Status da ligação": ["atendida", "não atendida", "ocupado"]})
    fig.update_layout(xaxis_title="", yaxis_title="Quantidade", legend_title="Status")
    st.plotly_chart(fig, use_container_width=True)

with right:
    by_status = f["Status da ligação"].value_counts().rename_axis("Status").reset_index(name="Ligações")
    fig = px.pie(by_status, names="Status", values="Ligações", hole=0.58, title="Distribuição por status")
    fig.update_traces(textposition="inside", textinfo="percent+label")
    st.plotly_chart(fig, use_container_width=True)

left, right = st.columns(2)
with left:
    hourly = f.dropna(subset=["Hora_num"]).groupby("Hora_num").size().reindex(range(24), fill_value=0).rename_axis("Hora").reset_index(name="Ligações")
    hourly["Hora"] = hourly["Hora"].map(lambda h: f"{int(h):02d}:00")
    fig = px.bar(hourly, x="Hora", y="Ligações", title="Distribuição por hora do dia")
    fig.update_layout(xaxis_title="Hora", yaxis_title="Quantidade")
    st.plotly_chart(fig, use_container_width=True)

with right:
    by_ramal = f[f["Ramal direcionado"].ne("—") & f["Ramal direcionado"].ne("")]["Ramal direcionado"].value_counts().head(12).rename_axis("Ramal").reset_index(name="Ligações")
    if not by_ramal.empty:
        fig = px.bar(by_ramal.sort_values("Ligações"), x="Ligações", y="Ramal", orientation="h", title="Ramais direcionados mais frequentes (top 12)")
        fig.update_layout(xaxis_title="Quantidade", yaxis_title="Ramal")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Não há ramais direcionados nos registros filtrados.")

st.subheader("Registros detalhados")
display_cols = ["Data", "Hora", "Número de origem", "Número de destino", "Ramal direcionado", "Status da ligação", "Tempo da ligação", "Observação"]
table = f[display_cols].sort_values(["Data", "Hora"], ascending=[False, False]).copy()
table["Data"] = table["Data"].dt.strftime("%d/%m/%Y")
table["Tempo da ligação"] = table["Tempo da ligação"].apply(lambda x: str(x).split(" days ")[-1] if pd.notna(x) else "—")
st.dataframe(table, use_container_width=True, hide_index=True)

csv = table.to_csv(index=False, sep=";", encoding="utf-8-sig").encode("utf-8-sig")
st.download_button("⬇️ Exportar registros filtrados (CSV)", data=csv, file_name="ligacoes_filtradas.csv", mime="text/csv")
st.caption("Observação: duração média considera apenas chamadas atendidas com tempo registrado. O filtro de ramal mantém também chamadas sem ramal direcionado (—), que normalmente representam chamadas não encaminhadas/sem atendimento.")
