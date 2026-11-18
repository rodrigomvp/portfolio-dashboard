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

## v1.1 — Dois mercados (Lisboa + Nova Iorque)

Ficheiros: `config/settings.yaml`, `src/portfolio/config.py`, `src/portfolio/fx.py` (novo), `src/portfolio/metrics.py`

- [x] Config: vários benchmarks, moeda base, moeda de cada ativo e taxa de câmbio
- [x] `fx.to_base_currency()`: converter preços em USD para EUR com o `EURUSD=X`
- [x] `metrics.align_calendars()`: feriados diferentes → último preço até 3 dias
- [x] `metrics.periods_per_year()`: anualizar com o número real de observações
- [x] `metrics.weekly_prices()`: correlações semanais (fechos a horas diferentes)
- [x] Descarregar Nvidia, Apple, McDonald's, S&P 500, Nasdaq-100 e EUR/USD
- [x] Verificar a qualidade dos dados novos (notebook `03_us_data.ipynb`)
- [x] App: escolher o benchmark, correlação diária/semanal

**Concluído quando:** `pytest` passa todo e a app mostra os 9 ativos em euros com qualquer um dos 3 benchmarks.

**Tag:** `v1.1-two-markets`

---

## v1.2 — Switch de mercado (Portugal | Estados Unidos)

**Porquê:** na v1.1 as ações americanas eram comparadas com o PSI, o que não faz sentido. Cada mercado passa a ter a sua vista, comparada com os seus próprios índices.

### Decisões
- Switch **Portugal | United States** no topo da sidebar (controlo segmentado). Muda ativos, pesos, benchmark, moeda e taxa sem risco.
- **Portugal:** 6 ações, benchmark PSI, em euros, taxa sem risco = Euribor a 3 meses.
- **Estados Unidos:** 10 ações de 9 setores, benchmark S&P 500 por defeito (Nasdaq-100 como alternativa), em dólares com botão **Show in EUR**, taxa sem risco = Tesouro americano a 3 meses.
- Cada mercado guarda os seus pesos (mudar de mercado e voltar não os perde).
- Sai da app a correlação semanal: dentro de um só mercado já não há fechos a horas diferentes.
- Modo **Both** (os dois mercados juntos, benchmark misto): fica para a v1.3.

### Ações americanas
| Empresa | Ticker | Setor |
|---|---|---|
| Nvidia | NVDA | Tecnologia |
| Apple | AAPL | Tecnologia |
| McDonald's | MCD | Consumo discricionário |
| JPMorgan Chase | JPM | Financeiro |
| Johnson & Johnson | JNJ | Saúde |
| Exxon Mobil | XOM | Energia |
| Coca-Cola | KO | Consumo básico |
| Caterpillar | CAT | Indústria |
| Alphabet | GOOGL | Comunicação |
| NextEra Energy | NEE | Utilities |

### Tarefas
Rodrigo:
- [x] `config.py`: ler `markets` (nome, moeda, tickers, benchmarks, taxa sem risco) — guiado por testes
- [x] `fx.to_new_york_close()`: corrigir o atraso de um dia do EUR/USD do Yahoo (descoberto no notebook 03)

Claude:
- [x] `settings.yaml` organizado por mercado, com as 7 ações novas e as taxas sem risco atualizadas
- [x] App: switch de mercado, benchmark por mercado, moeda $/€ com Show in EUR, taxa sem risco por mercado
- [x] Testes ajustados, README (Design, Methodology), notebook `03_us_data.ipynb` atualizado

Os dois:
- [x] `python scripts/update_data.py` para descarregar as 7 ações novas
- [x] Verificar a qualidade dos dados (notebook 03)
- [x] Testar a app com os dados reais

**Concluído quando:** `pytest` passa todo; em Portugal tudo é comparado com o PSI em euros; nos EUA com o S&P 500 ou o Nasdaq-100, em dólares ou em euros.

**Tag:** `v1.2-market-switch`

---

## v1.4 — Universo alargado de ativos (depois da Fase 5)

Plano completo guardado no projeto do Claude (`plano-v1.4-universo-alargado.md`). Resumo:

- [ ] Universo por mercado: os 16 constituintes do PSI e 44 ações americanas (4 por cada um dos 11 setores), com a carteira de hoje como seleção por defeito
- [ ] Config: `tickers` (universo), `default_tickers`, mapa `sectors`
- [ ] App: seletor com pesquisa (nome · setor), máximo de 15 ativos, exposição por setor no Overview
- [ ] Notebook `04_universe_quality.ipynb`: histórico desde 2018, saltos por explicar, moeda
- [ ] Depende da Fase 5, opção (b): os dados vêm do GitHub Action diário

**Tag:** `v1.4-asset-universe`

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

- v1.3: modo **Both** — carteira com ações dos dois mercados, em euros, com benchmark misto (ex.: 50% PSI + 50% S&P 500)
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
