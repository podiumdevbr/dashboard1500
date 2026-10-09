
from io import BytesIO
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


# =========================================================
# CONFIGURAÇÃO
# =========================================================

st.set_page_config(
    page_title="Painel de ligações | Ramal 1500",
    page_icon="☎️",
    layout="wide",
)

st.title("☎️ Painel de ligações — Ramal 3512-1500")
st.caption("Gestão, análise operacional e consulta de chamadas")


# =========================================================
# CARREGAMENTO AUTOMÁTICO DO EXCEL
# O arquivo deve ficar na mesma pasta deste app.py
# =========================================================

PASTA_APP = Path(__file__).resolve().parent
ARQUIVO_EXCEL = PASTA_APP / "ligacoes_ramal_1500.xlsx"


@st.cache_data
def load(caminho_arquivo, data_modificacao):
    df = pd.read_excel(
        caminho_arquivo,
        sheet_name="Ligações",
    )

    df.columns = [str(c).strip() for c in df.columns]

    required = [
        "Data",
        "Hora",
        "Número de origem",
        "Número de destino",
        "Ramal direcionado",
        "Status da ligação",
        "Tempo da ligação",
    ]

    missing = [c for c in required if c not in df.columns]

    if missing:
        raise ValueError(
            "Colunas ausentes na planilha: "
            + ", ".join(missing)
        )

    # Datas
    df["Data"] = pd.to_datetime(
        df["Data"],
        errors="coerce",
    )

    # Horários
    df["Hora"] = (
        df["Hora"]
        .astype(str)
        .str.replace(r"^0 days ", "", regex=True)
        .str.strip()
    )

    df["Hora_dt"] = pd.to_datetime(
        df["Hora"],
        format="%H:%M:%S",
        errors="coerce",
    )

    miss = df["Hora_dt"].isna()

    df.loc[miss, "Hora_dt"] = pd.to_datetime(
        df.loc[miss, "Hora"],
        format="%H:%M",
        errors="coerce",
    )

    df["Hora_num"] = df["Hora_dt"].dt.hour

    # Duração em segundos
    df["Tempo_segundos"] = pd.to_timedelta(
        df["Tempo da ligação"],
        errors="coerce",
    ).dt.total_seconds()

    # Campos textuais
    colunas_texto = [
        "Número de origem",
        "Número de destino",
        "Ramal direcionado",
        "Status da ligação",
        "Observação",
    ]

    for coluna in colunas_texto:
        if coluna in df.columns:
            df[coluna] = (
                df[coluna]
                .fillna("")
                .astype(str)
                .str.strip()
            )

    df["Status da ligação"] = (
        df["Status da ligação"].str.lower()
    )

    # Dia da semana em português
    dias = {
        "Monday": "Segunda-feira",
        "Tuesday": "Terça-feira",
        "Wednesday": "Quarta-feira",
        "Thursday": "Quinta-feira",
        "Friday": "Sexta-feira",
        "Saturday": "Sábado",
        "Sunday": "Domingo",
    }

    df["Dia da semana"] = (
        df["Data"].dt.day_name().map(dias)
    )

    # Faixas horárias
    df["Faixa horária"] = pd.cut(
        df["Hora_num"],
        bins=[-1, 5, 11, 17, 21, 23],
        labels=[
            "Madrugada (00–05)",
            "Manhã (06–11)",
            "Tarde (12–17)",
            "Noite (18–21)",
            "Noite (22–23)",
        ],
        include_lowest=True,
    )

    return df


# Verifica a existência da planilha
if not ARQUIVO_EXCEL.exists():
    st.error("Não foi possível encontrar a planilha Excel.")
    st.write("O aplicativo está procurando este arquivo:")
    st.code(str(ARQUIVO_EXCEL))
    st.info(
        "Coloque 'ligacoes_ramal_1500.xlsx' na mesma pasta "
        "do app.py e reinicie o aplicativo."
    )
    st.stop()


# Carrega os dados e identifica alterações no arquivo
try:
    data_modificacao = ARQUIVO_EXCEL.stat().st_mtime
    raw = load(str(ARQUIVO_EXCEL), data_modificacao)
except Exception as e:
    st.error(f"Não foi possível ler a planilha: {e}")
    st.stop()


if raw["Data"].notna().sum() == 0:
    st.error("A coluna Data não contém datas válidas.")
    st.stop()

st.caption(f"Fonte dos dados: {ARQUIVO_EXCEL.name}")


# =========================================================
# FILTROS
# =========================================================

min_date = raw["Data"].min().date()
max_date = raw["Data"].max().date()

data_referencia_inicio = pd.Timestamp("2026-09-24").date()
data_referencia_fim = pd.Timestamp("2026-10-06").date()

start = max(min_date, data_referencia_inicio)
end = min(max_date, data_referencia_fim)

if start > end:
    start, end = min_date, max_date

dias_ordem = [
    "Segunda-feira",
    "Terça-feira",
    "Quarta-feira",
    "Quinta-feira",
    "Sexta-feira",
    "Sábado",
    "Domingo",
]


with st.sidebar:
    st.header("Filtros")
    st.caption("Escolha uma opção nos menus ou selecione Todos.")

    periodo = st.date_input(
        "Período",
        value=(start, end),
        min_value=min_date,
        max_value=max_date,
        format="DD/MM/YYYY",
    )

    if isinstance(periodo, (tuple, list)) and len(periodo) == 2:
        inicio, fim = periodo
    else:
        inicio = fim = periodo

    # Dropdown de status
    statuses = sorted(
        x for x in raw["Status da ligação"].unique() if x
    )

    sel_status = st.selectbox(
        "Status da ligação",
        options=["Todos"] + statuses,
        index=0,
    )

    # Dropdown de ramal
    ramais = sorted(
        x
        for x in raw["Ramal direcionado"].unique()
        if x and x not in ["—", "-"]
    )

    sel_ramal = st.selectbox(
        "Ramal direcionado",
        options=["Todos"] + ramais,
        index=0,
    )

    # Dropdown de dia da semana
    dias_disponiveis = [
        d
        for d in dias_ordem
        if d in raw["Dia da semana"].dropna().unique()
    ]

    sel_dia = st.selectbox(
        "Dia da semana",
        options=["Todos"] + dias_disponiveis,
        index=0,
    )

    telefone = st.text_input(
        "Buscar telefone",
        placeholder="Digite origem ou destino",
    ).strip()


# =========================================================
# APLICAÇÃO DOS FILTROS
# =========================================================

mascara = raw["Data"].dt.date.between(inicio, fim)

if sel_status != "Todos":
    mascara &= raw["Status da ligação"].eq(sel_status)

if sel_ramal != "Todos":
    mascara &= raw["Ramal direcionado"].eq(sel_ramal)

if sel_dia != "Todos":
    mascara &= raw["Dia da semana"].eq(sel_dia)

if telefone:
    mascara &= (
        raw["Número de origem"].str.contains(
            telefone, case=False, na=False, regex=False
        )
        |
        raw["Número de destino"].str.contains(
            telefone, case=False, na=False, regex=False
        )
    )

df = raw.loc[mascara].copy()

fora = int(
    (
        ~raw["Data"].dt.date.between(
            data_referencia_inicio,
            data_referencia_fim,
        )
    ).sum()
)

if fora:
    st.caption(
        f"A planilha contém {fora} registro(s) fora do "
        "período de referência 24/09–06/10/2026."
    )

if df.empty:
    st.warning("Nenhum registro corresponde aos filtros selecionados.")
    st.stop()


# =========================================================
# INDICADORES GERAIS
# =========================================================

n = len(df)

atend = int(df["Status da ligação"].eq("atendida").sum())
nao = int(df["Status da ligação"].eq("não atendida").sum())
ocupado = int(df["Status da ligação"].eq("ocupado").sum())

dur = df.loc[
    df["Status da ligação"].eq("atendida"),
    "Tempo_segundos",
].dropna()


def fmt(segundos):
    if pd.isna(segundos):
        return "—"

    segundos = int(round(float(segundos)))
    horas, resto = divmod(segundos, 3600)
    minutos, segundos = divmod(resto, 60)

    if horas:
        return f"{horas:02d}:{minutos:02d}:{segundos:02d}"

    return f"{minutos:02d}:{segundos:02d}"


st.caption(
    f"Período analisado: **{inicio:%d/%m/%Y} a "
    f"{fim:%d/%m/%Y}** · {n:,} registros".replace(",", ".")
)

k = st.columns(5)

k[0].metric("Total de ligações", f"{n:,}".replace(",", "."))
k[1].metric("Atendidas", f"{atend:,}".replace(",", "."))
k[2].metric("Não atendidas", f"{nao:,}".replace(",", "."))
k[3].metric(
    "Taxa de atendimento",
    f"{100 * atend / n:.1f}%".replace(".", ","),
)
k[4].metric(
    "Duração média atendida",
    fmt(dur.mean() if len(dur) else float("nan")),
)


# =========================================================
# ABAS DO PAINEL
# =========================================================

t1, t2, t3 = st.tabs(
    ["📊 Gestão", "🛠️ Operação", "🔎 Consulta detalhada"]
)


# =========================================================
# ABA 1 — GESTÃO
# =========================================================

with t1:
    a, b = st.columns(2)

    with a:
        daily = (
            df.groupby(
                [df["Data"].dt.date, "Status da ligação"]
            )
            .size()
            .reset_index(name="Ligações")
        )

        fig_daily = px.bar(
            daily,
            x="Data",
            y="Ligações",
            color="Status da ligação",
            barmode="stack",
            title="Ligações por dia e status",
        )

        # Datas em formato brasileiro
        fig_daily.update_xaxes(
            tickformat="%d/%m",
            title="Data",
        )

        st.plotly_chart(fig_daily, use_container_width=True)

    with b:
        stat = (
            df["Status da ligação"]
            .value_counts()
            .rename_axis("Status")
            .reset_index(name="Ligações")
        )

        st.plotly_chart(
            px.pie(
                stat,
                names="Status",
                values="Ligações",
                hole=0.55,
                title="Distribuição por status",
            ),
            use_container_width=True,
        )

    week = (
        df.groupby("Dia da semana")
        .size()
        .reindex(dias_ordem, fill_value=0)
        .rename_axis("Dia da semana")
        .reset_index(name="Ligações")
    )

    st.plotly_chart(
        px.bar(
            week,
            x="Dia da semana",
            y="Ligações",
            title="Volume por dia da semana",
        ),
        use_container_width=True,
    )

    c1, c2 = st.columns(2)

    c1.metric(
        "Tempo total em chamadas atendidas",
        fmt(dur.sum() if len(dur) else float("nan")),
    )

    c2.metric(
        "Duração média atendida",
        fmt(dur.mean() if len(dur) else float("nan")),
    )


# =========================================================
# ABA 2 — OPERAÇÃO
# =========================================================

with t2:
    st.subheader("Volume geral por horário")

    a, b = st.columns(2)

    with a:
        hora = (
            df.dropna(subset=["Hora_num"])
            .groupby("Hora_num")
            .size()
            .reindex(range(24), fill_value=0)
            .rename_axis("Hora")
            .reset_index(name="Ligações")
        )

        hora["Horário"] = hora["Hora"].map(
            lambda x: f"{int(x):02d}:00"
        )

        st.plotly_chart(
            px.bar(
                hora,
                x="Horário",
                y="Ligações",
                title="Todas as ligações por hora",
            ),
            use_container_width=True,
        )

    with b:
        faixa = (
            df.groupby("Faixa horária", observed=False)
            .size()
            .rename("Ligações")
            .reset_index()
        )

        faixa["Faixa horária"] = faixa["Faixa horária"].astype(str)

        st.plotly_chart(
            px.bar(
                faixa,
                x="Faixa horária",
                y="Ligações",
                title="Ligações por faixa horária",
            ),
            use_container_width=True,
        )

    # Mapa de calor de todas as ligações
    heat = (
        df.dropna(subset=["Hora_num", "Dia da semana"])
        .groupby(["Dia da semana", "Hora_num"])
        .size()
        .reset_index(name="Ligações")
    )

    pivot = (
        heat.pivot(
            index="Dia da semana",
            columns="Hora_num",
            values="Ligações",
        )
        .reindex(
            index=dias_ordem,
            columns=range(24),
            fill_value=0,
        )
        .fillna(0)
    )

    st.plotly_chart(
        px.imshow(
            pivot,
            aspect="auto",
            labels={
                "x": "Hora",
                "y": "Dia da semana",
                "color": "Ligações",
            },
            x=[f"{x:02d}:00" for x in range(24)],
            y=pivot.index,
            title="Mapa de calor: todas as ligações por dia e hora",
        ),
        use_container_width=True,
    )

    # Ramais mais frequentes e números de origem
    a, b = st.columns(2)

    with a:
        st.markdown("**Ramais direcionados mais frequentes**")

        rr = (
            df[
                ~df["Ramal direcionado"].isin(["", "—", "-"])
            ]
            .groupby("Ramal direcionado")
            .size()
            .sort_values(ascending=False)
            .head(10)
            .rename("Ligações")
            .reset_index()
        )

        if rr.empty:
            st.info("Sem ramais direcionados nos filtros atuais.")
        else:
            st.plotly_chart(
                px.bar(
                    rr.sort_values("Ligações"),
                    x="Ligações",
                    y="Ramal direcionado",
                    orientation="h",
                    title="Top 10 ramais",
                ),
                use_container_width=True,
            )

    with b:
        st.markdown("**Números de origem recorrentes**")

        cc = (
            df[df["Número de origem"].ne("")]
            .groupby("Número de origem")
            .size()
            .sort_values(ascending=False)
            .head(10)
            .rename("Ligações")
            .reset_index()
        )

        st.dataframe(
            cc,
            use_container_width=True,
            hide_index=True,
        )

    # =====================================================
    # NOVA ANÁLISE — LIGAÇÕES NÃO ATENDIDAS POR HORÁRIO
    # =====================================================

    st.divider()
    st.subheader("📵 Análise de ligações não atendidas por horário")

    st.caption(
        "Esta seção considera somente chamadas com status "
        "'não atendida' e respeita os filtros selecionados."
    )

    nao_atendidas = df.loc[
        df["Status da ligação"].eq("não atendida")
    ].copy()

    if nao_atendidas.empty:
        st.info(
            "Não há chamadas não atendidas para os filtros selecionados."
        )

    else:
        # Conta chamadas perdidas em cada hora
        perdidas_hora = (
            nao_atendidas.dropna(subset=["Hora_num"])
            .groupby("Hora_num")
            .size()
            .reindex(range(24), fill_value=0)
            .rename("Ligações não atendidas")
            .rename_axis("Hora")
            .reset_index()
        )

        perdidas_hora["Horário"] = perdidas_hora["Hora"].map(
            lambda x: f"{int(x):02d}:00"
        )

        total_perdidas_com_hora = int(
            perdidas_hora["Ligações não atendidas"].sum()
        )

        # Horário de pico, sem considerar horários sem chamadas
        horas_com_chamadas = perdidas_hora.loc[
            perdidas_hora["Ligações não atendidas"] > 0
        ]

        if not horas_com_chamadas.empty:
            pico = horas_com_chamadas.sort_values(
                ["Ligações não atendidas", "Hora"],
                ascending=[False, True],
            ).iloc[0]

            pico_hora = int(pico["Hora"])
            pico_quantidade = int(pico["Ligações não atendidas"])

            pico_percentual = (
                100 * pico_quantidade / total_perdidas_com_hora
                if total_perdidas_com_hora
                else 0
            )

            m1, m2, m3 = st.columns(3)

            m1.metric(
                "Horário de pico",
                f"{pico_hora:02d}:00–{pico_hora:02d}:59",
            )

            m2.metric(
                "Não atendidas no horário de pico",
                f"{pico_quantidade:,}".replace(",", "."),
            )

            m3.metric(
                "Participação no total por hora",
                f"{pico_percentual:.1f}%".replace(".", ","),
            )

        # Gráfico por hora
        fig_perdidas = px.bar(
            perdidas_hora,
            x="Horário",
            y="Ligações não atendidas",
            title="Ligações não atendidas por hora",
            labels={
                "Horário": "Horário",
                "Ligações não atendidas": "Chamadas não atendidas",
            },
            hover_data={
                "Hora": False,
                "Horário": True,
                "Ligações não atendidas": True,
            },
        )

        fig_perdidas.update_xaxes(
            categoryorder="array",
            categoryarray=[
                f"{h:02d}:00" for h in range(24)
            ],
        )

        st.plotly_chart(
            fig_perdidas,
            use_container_width=True,
        )

        # Ranking das horas com mais chamadas perdidas
        st.markdown("**Ranking de horários com mais chamadas não atendidas**")

        ranking = (
            perdidas_hora.loc[
                perdidas_hora["Ligações não atendidas"] > 0,
                ["Horário", "Ligações não atendidas"],
            ]
            .sort_values(
                "Ligações não atendidas",
                ascending=False,
            )
            .reset_index(drop=True)
        )

        ranking.index = ranking.index + 1
        ranking.index.name = "Posição"

        st.dataframe(
            ranking,
            use_container_width=True,
        )

        # Mapa de calor: dia da semana x hora, somente perdidas
        st.markdown(
            "**Mapa de calor: chamadas não atendidas por dia da semana e hora**"
        )

        heat_perdidas = (
            nao_atendidas.dropna(
                subset=["Hora_num", "Dia da semana"]
            )
            .groupby(["Dia da semana", "Hora_num"])
            .size()
            .reset_index(name="Não atendidas")
        )

        pivot_perdidas = (
            heat_perdidas.pivot(
                index="Dia da semana",
                columns="Hora_num",
                values="Não atendidas",
            )
            .reindex(
                index=dias_ordem,
                columns=range(24),
                fill_value=0,
            )
            .fillna(0)
        )

        st.plotly_chart(
            px.imshow(
                pivot_perdidas,
                aspect="auto",
                labels={
                    "x": "Hora",
                    "y": "Dia da semana",
                    "color": "Não atendidas",
                },
                x=[f"{x:02d}:00" for x in range(24)],
                y=pivot_perdidas.index,
                title="Concentração de chamadas não atendidas",
                color_continuous_scale="Reds",
            ),
            use_container_width=True,
        )

        st.caption(
            "O horário de pico indica a hora com maior número de "
            "chamadas não atendidas dentro dos filtros aplicados. "
            "Empates são resolvidos exibindo primeiro o horário mais cedo."
        )

    # =====================================================
    # LISTA DE CHAMADAS NÃO ATENDIDAS
    # =====================================================

    st.divider()
    st.markdown("**Detalhamento das chamadas não atendidas**")

    missed = nao_atendidas[
        [
            "Data",
            "Hora",
            "Número de origem",
            "Número de destino",
            "Ramal direcionado",
        ]
    ].sort_values(
        ["Data", "Hora"],
        ascending=False,
    ).copy()

    missed["Data"] = missed["Data"].dt.strftime("%d/%m/%Y")

    st.dataframe(
        missed,
        use_container_width=True,
        hide_index=True,
    )


# =========================================================
# ABA 3 — CONSULTA DETALHADA
# =========================================================

with t3:
    st.caption(
        "Os resultados abaixo respeitam todos os filtros "
        "selecionados na barra lateral."
    )

    cols = [
        "Data",
        "Hora",
        "Número de origem",
        "Número de destino",
        "Ramal direcionado",
        "Status da ligação",
        "Tempo da ligação",
    ]

    if "Observação" in df.columns:
        if st.checkbox("Incluir observação"):
            cols.append("Observação")

    table = (
        df[cols]
        .sort_values(
            ["Data", "Hora"],
            ascending=False,
        )
        .copy()
    )

    table["Data"] = table["Data"].dt.strftime("%d/%m/%Y")

    table["Tempo da ligação"] = table["Tempo da ligação"].apply(
        lambda x: (
            str(x).split(" days ")[-1]
            if pd.notna(x)
            else "—"
        )
    )

    st.dataframe(
        table,
        use_container_width=True,
        hide_index=True,
        height=480,
    )

    # Exportação CSV
    st.download_button(
        "⬇️ Exportar CSV",
        data=table.to_csv(
            index=False,
            sep=";",
            encoding="utf-8-sig",
        ).encode("utf-8-sig"),
        file_name="ligacoes_filtradas.csv",
        mime="text/csv",
    )

    # Exportação Excel
    buf = BytesIO()

    with pd.ExcelWriter(
        buf,
        engine="openpyxl",
    ) as writer:
        table.to_excel(
            writer,
            index=False,
            sheet_name="Ligações filtradas",
        )

    st.download_button(
        "⬇️ Exportar Excel",
        data=buf.getvalue(),
        file_name="ligacoes_filtradas.xlsx",
        mime=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
    )


# =========================================================
# RODAPÉ
# =========================================================

st.divider()

st.caption(
    "A duração média considera somente chamadas atendidas "
    "com tempo válido. A taxa de atendimento é calculada como "
    "chamadas atendidas ÷ total de registros filtrados."
)