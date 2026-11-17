# Roadmap — Portfolio Risk Dashboard

Plano em 6 fases. Cada fase termina com algo que funciona e um commit/tag no GitHub, para que o histórico do repositório mostre uma evolução organizada.

**Duração estimada:** 5 a 7 semanas a ritmo de part-time (6–8 h/semana).

**Regra de ouro:** todos os cálculos ficam em `src/portfolio/` e têm testes. A app Streamlit só mostra resultados.

---

## Fase 0 — Setup (≈ 1 dia)

- [x] Criar repositório **privado** `portfolio-dashboard` na conta pessoal do GitHub
- [x] Copiar esta estrutura, primeiro commit
- [x] Criar ambiente virtual, `pip install -r requirements.txt` e `pip install -e .`
- [x] Confirmar no finance.yahoo.com que os tickers de `config/settings.yaml` existem (incluindo o benchmark)
- [x] Correr `pytest` — os testes devem ser **recolhidos** e falhar com `NotImplementedError` (é o esperado)

**Concluído quando:** `streamlit run app/streamlit_app.py` abre a página com as tabs vazias.

---

## Fase 1 — Pipeline de dados (≈ 3–4 dias)

Ficheiros: `src/portfolio/ingest.py`, `src/portfolio/db.py`, `scripts/update_data.py`

- [x] `fetch_prices()`: descarregar com yfinance e converter para formato longo
- [x] `upsert_prices()`: `INSERT OR REPLACE` para não haver duplicados
- [x] `last_date_per_ticker()` + `update_database()`: atualização incremental (só puxa dias novos)
- [x] `load_close_prices()`: devolver tabela larga (datas × tickers)
- [x] Explorar os dados num notebook rápido: dias em falta, feriados diferentes entre bolsas, valores estranhos
- [x] Decidir e documentar como tratar dias em falta (`ffill` limitado? remover?)

**Concluído quando:** correr `update_data.py` duas vezes seguidas não duplica linhas e a segunda execução é quase instantânea.

**Tag:** `v0.1-data`

---

## Fase 2 — Métricas (≈ 1 semana)

Ficheiro: `src/portfolio/metrics.py` · Testes: `tests/test_metrics.py`

- [x] Retornos simples e logarítmicos
- [x] Retorno anualizado (CAGR) e volatilidade anualizada
- [x] Sharpe ratio (com taxa sem risco da config)
- [x] Drawdown e max drawdown
- [x] Matriz de correlação
- [x] Retornos da carteira com pesos (validar soma = 1)
- [x] Beta face ao benchmark
- [x] `summary_table()` que junta tudo por ativo
- [x] Opcional: Sortino ratio, volatilidade móvel (rolling 60 dias)

**Concluído quando:** `pytest tests/test_metrics.py` passa todo a verde.

**Tag:** `v0.2-metrics`

---

## Fase 3 — Dashboard (≈ 1 semana)

Ficheiro: `app/streamlit_app.py` · Usar **Plotly** (gráficos interativos)

- [x] Carregar preços com `@st.cache_data`
- [x] Aplicar a decisão da Fase 1: `prices.dropna()` antes de calcular retornos (datas incompletas removidas)
- [x] Sidebar: ativos, pesos (aviso se não somarem 1), intervalo de datas, taxa sem risco
- [x] **Overview:** linha de KPIs (`st.metric`), preços normalizados a base 100 vs benchmark, tabela resumo
- [x] **Risk:** gráfico de drawdown (underwater), volatilidade móvel
- [x] **Correlation:** heatmap com escala divergente de -1 a 1
- [x] Formatar percentagens e casas decimais de forma consistente

**Concluído quando:** alguém que nunca viu o projeto consegue mudar os pesos e perceber o efeito em 30 segundos.

**Tag:** `v0.3-dashboard` — a partir daqui o repositório pode passar a **público**.

---

## Fase 4 — Apoio à decisão (≈ 1–2 semanas)

Ficheiros: `src/portfolio/risk.py`, `src/portfolio/optimization.py`

- [ ] VaR e CVaR históricos; VaR paramétrico (normal)
- [ ] Histograma dos retornos com as linhas de VaR — comentar a diferença (caudas pesadas)
- [ ] Carteiras aleatórias (Monte Carlo) colorida pelo Sharpe
- [ ] Carteira de variância mínima e de Sharpe máximo (`scipy.optimize`, long-only)
- [ ] Fronteira eficiente
- [ ] Tab **Optimisation**: gráfico risco × retorno com ativos individuais, carteira atual e carteiras ótimas; tabela de pesos sugeridos
- [ ] Opcional: backtest simples — carteira de Sharpe máximo calculada até ano X, desempenho fora da amostra no ano X+1 (mostra espírito crítico)

**Concluído quando:** `pytest` passa todo e a tab de otimização responde à pergunta "como devia distribuir os pesos?".

**Tag:** `v0.4-optimisation`

---

## Fase 5 — Produção e apresentação (≈ 3–4 dias)

- [ ] **Deploy** no Streamlit Community Cloud (ligar ao repositório GitHub)
- [ ] Dados em produção: o disco do Streamlit Cloud não é permanente. Opções:
  - (a) descarregar os dados no arranque e guardar em cache (mais simples), ou
  - (b) GitHub Action agendada que corre `update_data.py` diariamente e faz commit de um ficheiro Parquet (mais "engenharia de dados")
- [ ] GitHub Actions a correr os testes em cada push (já incluído em `.github/workflows/tests.yml`) + badge no README
- [ ] README final: screenshot ou GIF, link da demo, secções **Methodology** e **Limitations** preenchidas
- [ ] Rever código: nomes claros, docstrings, sem código morto
- [ ] Adicionar ao CV e LinkedIn (link da demo + link do repositório) e escrever um post curto com 1 insight concreto tirado dos dados

**Tag:** `v1.0`

---

## Ideias para depois (só se sobrar tempo)

- Comparar períodos (ex.: 2020 vs 2022) com um seletor
- Exportar relatório em PDF
- Rebalanceamento mensal vs diário e impacto nos resultados
- Adicionar ativos de outras moedas com conversão cambial

## Perguntas para conseguires responder em entrevista

- Porque é que a correlação se calcula sobre retornos e não sobre preços?
- Porque é que se usa o preço ajustado?
- O que assume o VaR paramétrico e quando falha?
- Porque é que a carteira de Sharpe máximo do passado pode correr mal no futuro?
- Que decisões de engenharia tomaste (SQLite, atualização incremental, testes) e porquê?
