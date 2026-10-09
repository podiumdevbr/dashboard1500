# Dashboard web de ligações — Ramal 3512-1500

Aplicação Streamlit para gestão, análise operacional e consulta de registros.

## Recursos
- KPIs de volume, atendidas, não atendidas, taxa de atendimento e duração média.
- Filtros por período, status, ramal, telefone e dia da semana.
- Gráficos por dia, status, dia da semana, hora e faixa horária.
- Mapa de calor dia da semana × hora.
- Chamadas não atendidas, ramais frequentes e origens recorrentes.
- Tabela detalhada e exportação CSV/Excel.

## Executar localmente
Requer Python 3.10+.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Carregue o arquivo `.xlsx` na barra lateral. A planilha precisa ter uma aba `Ligações` com as colunas do arquivo de referência.

## Publicar na web (Streamlit Community Cloud)
1. Crie um repositório GitHub com `app.py`, `requirements.txt` e `README.md`.
2. Não envie a planilha real a um repositório público. O `.gitignore` ignora arquivos `.xlsx`; confirme isso antes do commit.
3. Entre em https://share.streamlit.io/ com sua conta GitHub.
4. Crie um app, escolha o repositório, branch e caminho `app.py`, e publique.
5. Abra o app e carregue a planilha pela barra lateral.

Documentação oficial: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app

## Segurança
Os registros podem conter dados pessoais, como números de telefone. O pacote não inclui a planilha original. Antes de publicar, confirme as regras de segurança e privacidade da sua organização. Para dados institucionais, prefira ambiente privado autorizado, autenticação e controle de acesso. Uma URL não deve ser considerada privada apenas por não ser divulgada.

## Período de referência
O filtro padrão tenta usar 24/09/2026 a 06/10/2026. A planilha enviada contém também registros anteriores, que podem ser consultados alterando o período.
