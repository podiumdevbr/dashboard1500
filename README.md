# Dashboard de Ligações — Ramal 3512-1500

## Como executar
1. Instale Python 3.10 ou superior.
2. Coloque `app.py`, `requirements.txt` e `ligacoes_ramal_1500.xlsx` na mesma pasta.
3. Abra o terminal nessa pasta e execute:

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
streamlit run app.py
```

O navegador abrirá o dashboard. Também é possível carregar outro arquivo `.xlsx` pelo campo da barra lateral.

## Recursos
- Filtro por período, status, ramal direcionado e telefone.
- Indicadores de volume, atendimento e duração média.
- Gráficos por dia, status, hora e ramal.
- Tabela detalhada e exportação dos registros filtrados para CSV.

## Atenção ao período
O arquivo recebido contém registros de 21/09/2026 a 06/10/2026. O filtro inicial do painel está configurado para 24/09/2026 a 06/10/2026, conforme solicitado, mas pode ser alterado para consultar os demais registros.
