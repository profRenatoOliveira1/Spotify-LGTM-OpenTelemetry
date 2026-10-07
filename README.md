# Projeto de Observabilidade Spotify: Stack LGTM & OpenTelemetry
**Instituto Federal de Mato Grosso (IFMT) — Disciplina de Gerenciamento e Monitoramento de Aplicações e Infraestrutura**  
*Atividade 04: Projeto Final de Observabilidade*

---

## 1. Visão Geral da Solução

Este repositório contém a implementação completa e operacional da arquitetura de observabilidade proposta no artigo acadêmico para uma plataforma distribuída de streaming de áudio baseada em microsserviços (**Cenário Spotify**).

A solução entrega a união dos três pilares da observabilidade moderna (**Métricas, Logs e Traces**) correlacionados através da stack **LGTM** (Loki, Grafana, Tempo, Prometheus) e instrumentada via **OpenTelemetry (OTel)**.

### Componentes da Arquitetura:
1. **Aplicação Spotify (`spotify-services`):** Microsserviços desenvolvidos em Python/FastAPI simulando *Auth-Service*, *Catalog-Search-Service*, *Audio-Streaming-Service* e *Recommendation-Service*, com gerador de carga contínuo integrado.
2. **Camada de Cache & Sessão (`redis`):** Banco em memória para validação de sessões JWT e cache de metadados do catálogo.
3. **OpenTelemetry Collector (`otel-collector`):** Gateway central de telemetria recebendo dados via protocolo **OTLP** (gRPC e HTTP) e exportando métricas para o Prometheus e traces para o Tempo.
4. **Prometheus (`prometheus`):** Banco temporal (TSDB) coletando métricas a cada 3 a 5 segundos, avaliando as regras de alerta e notificando o Alertmanager.
5. **Grafana Tempo (`tempo`):** Backend de rastreamento distribuído (*Distributed Tracing*) para visualização de Spans e `TraceID` ponta a ponta.
6. **Grafana Loki (`loki`):** Sistema de agregação e consulta de logs JSON estruturados.
7. **Alertmanager (`alertmanager`):** Motor de notificação de alertas com *contact point* Slack (configurável via `SLACK_WEBHOOK_URL`) e datasource provisionada no Grafana.
8. **Node Exporter & Redis Exporter (`node-exporter`, `redis-exporter`):** Coletam métricas **reais** de infraestrutura (CPU/memória do nó e hit ratio do Redis) para o framework USE.
9. **Grafana (`grafana`):** Camada de apresentação com provisionamento automático de datasources (Prometheus, Loki, Tempo, Alertmanager) e do **Dashboard Executivo e Técnico (Seção 5 do artigo)**.

---

## 2. Como Executar (Turnkey Deployment)

### Pré-requisitos:
* Docker (v20.10+)
* Docker Compose (v2.0+)

### Execução em 1 Comando:
```bash
# Permissão de execução no script de inicialização
chmod +x start.sh

# Inicialização automatizada
./start.sh
```

Ou diretamente via Docker Compose:
```bash
docker compose up -d --build
```

> **Notificação no Slack (opcional):** defina o webhook do canal antes de subir a stack para que os alertas críticos sejam enviados ao Slack. Sem a variável, os alertas usam um endpoint de demonstração e continuam visíveis na UI do Alertmanager.
> ```bash
> SLACK_WEBHOOK_URL="https://hooks.slack.com/services/XXX/YYY/ZZZ" ./start.sh
> ```

---

## 3. Acessos e Portas do Sistema

| Serviço | URL | Credenciais / Notas |
| :--- | :--- | :--- |
| **Grafana Dashboards** | [http://localhost:3000](http://localhost:3000) | `admin` / `admin` (Provisionamento automático) |
| **Prometheus TSDB** | [http://localhost:9090](http://localhost:9090) | Consultas PromQL |
| **Prometheus Alerts** | [http://localhost:9090/alerts](http://localhost:9090/alerts) | 5 Regras de Alerta ativas |
| **Alertmanager** | [http://localhost:9093](http://localhost:9093) | Notificação/roteamento de alertas (Slack) |
| **Swagger API Spotify** | [http://localhost:8000/docs](http://localhost:8000/docs) | Documentação interativa dos microsserviços |
| **Métricas Brutas** | [http://localhost:8000/metrics](http://localhost:8000/metrics) | Scrape do Prometheus |
| **Grafana Loki API** | [http://localhost:3100](http://localhost:3100) | Ingestão e consulta LogQL |
| **Grafana Tempo API** | [http://localhost:3200](http://localhost:3200) | Ingestão e consulta TraceQL |
| **Node Exporter** | [http://localhost:9100/metrics](http://localhost:9100/metrics) | Métricas reais de CPU/memória do nó |
| **Redis Exporter** | [http://localhost:9121/metrics](http://localhost:9121/metrics) | Métricas reais do Redis (hit ratio) |

---

## 4. O Dashboard do Grafana (Seção 5 do artigo)

Ao acessar o Grafana em `http://localhost:3000`, navegue até **Dashboards** > **Spotify Platform** > **Spotify Platform - Observability Overview (SRE)**. O painel contém exatamente as 4 linhas estruturais definidas no artigo:

* **Row 1 — Indicadores Executivos (KPIs):**
  * `Availability SLO (%)` (Alvo > 99.9%)
  * `Active Players` (Concorrência de ouvintes ativos)
  * `Buffer Underruns Ratio (%)` (Taxa de engasgo de áudio)
* **Row 2 — Framework RED (Nível de Serviço):**
  * `PANEL A`: Request Rate (RPS por Microsserviço)
  * `PANEL B`: Taxa de Erros HTTP (4xx e 5xx) empilhados por código e serviço
  * `PANEL C`: Latência de Resposta (Percentis p50, p90 e p99 em ms)
  * `PANEL H`: Taxa de Erros 5xx por Região (`sa-east-1`, `us-east-1`, `eu-west-1`)
* **Row 3 — Desempenho de Streaming & Áudio:**
  * `PANEL D`: Playback Initialization Time (Gauge com limiar de 300ms)
  * `PANEL E`: Bitrate Médio de Streaming (kbps) & Conexões WebSocket ativas
* **Row 4 — Recursos de Infraestrutura (Framework USE & Cache):**
  * `PANEL F`: Ocupação de CPU e Memória do nó (**métricas reais** via Node Exporter)
  * `PANEL G`: Hit Ratio do Cache Redis (Gauge com limiar em 95%, **métrica real** via Redis Exporter)
  * `PANEL I`: Saturação — Requisições HTTP em Processamento (`spotify_http_requests_in_flight`)

---

## 5. Correlação Bidirecional (Logs ↔ Traces)

A stack foi configurada para integrar Logs e Traces sem fricção:
1. No menu lateral do Grafana, abra o **Explore** e selecione o datasource **Loki**.
2. Faça uma consulta simples: `{app="spotify"} |= "error"`.
3. Nos resultados dos logs JSON, você verá o campo `trace_id`.
4. Ao lado do valor do `trace_id`, clique no botão azul **"Ver Trace no Tempo"**.
5. O Grafana abrirá automaticamente o painel dividido com o trace correspondente no **Tempo**, exibindo todos os spans da requisição e o ponto exato da lentidão ou erro!

---

## 6. As 5 Regras de Alerta Configuradas (`prometheus/alert_rules.yml`)

1. **`PlaybackLatencyHigh` (Crítico):** Disparado quando o percentil p99 da latência de início de áudio supera **500 ms** por mais de 1 minuto.
2. **`StreamingErrorRateHigh` (Crítico):** Disparado quando a taxa de falhas HTTP 5xx no serviço de streaming excede **2%** do total de chamadas.
3. **`MicroserviceCPUHigh` (Alerta):** Disparado quando o consumo sustentado de CPU supera **85%** por mais de 3 minutos.
4. **`RedisCacheMissHigh` (Alerta):** Disparado quando o hit ratio do cache de metadados cai abaixo de **90%**.
5. **`AuthServiceUnavailable` (Crítico):** Disparado quando a disponibilidade das autenticações cai abaixo de **99.9%**.

### Fluxo de Notificação (Grafana Unified Alerting + Alertmanager)

```
Prometheus (evaluação a cada 5s) ──▶ Alertmanager (:9093) ──▶ Slack (#observability-alerts)
                                          │
Grafana (datasource Alertmanager) ◀───────┘  (mesmos alertas na UI do Grafana)
```

* **Críticos** → enviados ao *contact point* Slack configurado em `alertmanager/alertmanager.yml.tpl`.
* **Warnings** → visíveis na UI do Alertmanager/Grafana, sem notificação no canal.

---

## 7. Testes Manuais de Carga e Injeção de Falhas

Embora o contêiner já possua um gerador de carga automático em segundo plano, você pode disparar chamadas manuais via `curl` ou terminal:

```bash
# 1. Login no Auth-Service
curl -X POST http://localhost:8000/api/v1/auth/login \
     -H "Content-Type: application/json" \
     -d '{"username": "aluno_ifmt", "password": "123"}'

# 2. Busca no Catálogo
curl "http://localhost:8000/api/v1/catalog/search?query=Coldplay"

# 3. Streaming de Áudio (Chunk 1)
curl "http://localhost:8000/api/v1/streaming/track/yellow_coldplay?chunk=1"

# 4. Obtenção de Recomendações
curl "http://localhost:8000/api/v1/recommendations/user/aluno_ifmt"
```

## 8. Dashboards
![Dashboard de observabilidade #1](/docs/img/Imagem3.png)
![Dashboard de observabilidade #2](/docs/img/Imagem4.png)