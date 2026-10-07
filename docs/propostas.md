# Propostas de Alteração — Análise `docs/artigo.md` vs. Projeto

> Análise de conformidade entre a proposta do artigo e a implementação no repositório.
>
> **Direções aprovadas:**
> 1. Infraestrutura: ajustar o artigo para Docker Compose (não implementar K3s/Helm).
> 2. Microsserviços: ajustar o artigo para Python/FastAPI (não criar Go/Node.js).
> 3. Alertas: implementar Alertmanager com notificação Slack.
> 4. Traces: ajustar o texto do artigo (não separar em processos reais).
> 5. 5xx por região: implementar no projeto (label + painel).
> 6. Métricas via OTel Collector: ajustar o artigo (scrape direto).
> 7. USE/infraestrutura real: implementar exporters + métrica de saturação.
> 8. Artigo truncado: completar as seções faltantes.
> 9. Severidade dos alertas: ajustar o texto do resumo.

---

## A. Alterações no artigo (`docs/artigo.md`)

### A1. §4.1 — Ambiente físico (divergência crítica)

- **Hoje no artigo:** Kubernetes (K3s v1.28) em nós Ubuntu Server 22.04 LTS, com cluster de Redis e cluster de Cassandra.
- **Real no projeto:** Docker Compose v2 (`docker-compose.yml`), Redis único (`docker-compose.yml:30`), **sem Cassandra** em lugar algum.
- **Proposta:** reescrever o §4.1 descrevendo a implantação via Docker Compose com Redis 7 Alpine, removendo as menções a K3s, nós Ubuntu e Cassandra.

### A2. §4.2 — Instalação

- **Hoje no artigo:** "Helm Charts oficiais do Grafana e Prometheus Operator".
- **Real no projeto:** imagens Docker oficiais montadas via `docker-compose.yml` + `start.sh`, com provisionamento automático de datasources e dashboards (`grafana/provisioning/`).
- **Proposta:** reescrever o §4.2 detalhando o `docker compose up`, o script `start.sh` e o provisioning de arquivos do Grafana.

### A3. Tabela 1 — Multi-linguagem

- **Hoje no artigo:** "Coleta agnóstica de métricas e traces em microsserviços desenvolvidos em **Go, Node.js e Python**".
- **Real no projeto:** os 4 domínios (Auth, Catálogo, Streaming, Recomendações) são simulados em Python/FastAPI dentro de um único serviço (`services/main.py`).
- **Proposta:** corrigir a célula para "Python/FastAPI, mantendo a instrumentação OpenTelemetry agnóstica à linguagem".

### A4. Tabela 1 — Pipeline de métricas do OTel Collector

- **Hoje no artigo:** "OpenTelemetry Collector Pipeline ... Coleta agnóstica de **métricas** e traces".
- **Real no projeto:** traces via OTLP → Collector → Tempo; métricas vão direto do endpoint `/metrics` da aplicação para o Prometheus em *pull* (`prometheus/prometheus.yml:17`). O exporter `prometheus` do Collector (porta 8889) permanece ocioso.
- **Proposta:** reescrever a célula: métricas coletadas via *scrape* promíscuo do Prometheus; traces coletados via OTel Collector (receivers OTLP → processors → exporters Tempo).

### A5. Resumo — Severidade dos alertas

- **Hoje no artigo:** "5 alertas **críticos**".
- **Real no projeto:** 3 `critical` + 2 `warning` (`prometheus/alert_rules.yml`).
- **Proposta:** alterar para "5 alertas operacionais (3 críticos e 2 de advertência)".

### A6. §2.2 / §3 — Traces fim-a-fim

- **Hoje no artigo:** "jornada ponta a ponta ... à medida que ela atravessa as fronteiras dos microsserviços".
- **Real no projeto:** processo único (`services/main.py`); cada requisição gera um span raiz próprio, sem propagação de contexto entre serviços distintos.
- **Proposta:** explicar que os 4 domínios são simulados no mesmo processo devido ao ambiente experimental, e que os spans modelam a cadeia de dependência com contexto OTel propagado entre as etapas internas da requisição.

### A7. Completar o artigo (truncado na linha 99)

O arquivo termina no meio da seção 4.2. Incluir as seções seguintes:

- **§5 — Painéis de visualização:** as 4 rows de `grafana/dashboards/spotify-overview.json` (KPIs, RED, Streaming, USE), utilizando `docs/img/Imagem2.png` como **Figura 2 ou 3** (hoje órfã; o `README.md` já a cita como "Figura 3").
- **§6 — Regras de alertamento:** as 5 regras de `prometheus/alert_rules.yml` com limiares, severidade e o fluxo de notificação via Alertmanager (item B1).
- **§7 — Resultados experimentais:** evidências de correlação Trace↔Logs, tempo de identificação de incidentes (MTTR) e capturas da stack em execução.
- **§8 — Análise comparativa com soluções proprietárias:** comparativo Grafana/OpenTelemetry vs. Datadog, New Relic e ELK (prometido no §1 "Objetivo e Escopo").
- **§9 — Conclusão** e **Referências bibliográficas**.

### A8. §2.3 — Framework USE

- Manter a afirmação de cobertura do USE **após** a implementação de B3 e B4 (exporters reais + métrica de saturação), que passam a sustentá-la.

### A9. `prometheus/alert_rules.yml:46`

- Remover a menção a Cassandra na anotação do alerta `RedisCacheMissHigh` (não há Cassandra no ambiente).

---

## B. Alterações no projeto (implementação)

### B1. Alertmanager com notificação Slack (Tabela 1 — Unified Alerting)

- Novo serviço `alertmanager` em `docker-compose.yml` (imagem `prom/alertmanager`, porta `9093:9093`).
- Novo arquivo `alertmanager/alertmanager.yml`:
  - receiver `slack-webhook` com webhook via env `SLACK_WEBHOOK_URL` (opcional — se ausente, usar receiver `null`/webhook.site para demonstração);
  - rotas por severidade (`critical` → Slack, `warning` → console).
- Novo job de scrape do Alertmanager em `prometheus/prometheus.yml`.
- Corrigir `loki/loki-config.yaml:30` → `ruler.alertmanager_url: http://alertmanager:9093`.
- Provisionar o datasource Alertmanager no Grafana (`grafana/provisioning/datasources/datasources.yaml`).

### B2. Label `region` (Tabela 1 — "erros 5xx por região")

- Adicionar label `region` ao Counter `REQUESTS_TOTAL` (`services/main.py:59`), com valores `sa-east-1`, `us-east-1`, `eu-west-1` (sorteio por requisição).
- Atualizar todos os `.labels(...)` de `REQUESTS_TOTAL` nos 4 endpoints.
- Novo painel **"Taxa de Erros 5xx por Região"** na Row 2 do dashboard.

### B3. Exporters de infraestrutura real (framework USE)

- Serviços `node-exporter` e `redis-exporter` no `docker-compose.yml`.
- Jobs de scrape correspondentes em `prometheus/prometheus.yml`.
- **Painel F** passa a usar métricas reais (`node_cpu_seconds_total`, `node_memory_MemAvailable_bytes`).
- **Painel G** passa a usar hit ratio real do Redis (`redis_keyspace_hits_total` / (`redis_keyspace_hits_total` + `redis_keyspace_misses_total`)).
- **Manter** os gauges simulados (`spotify_cpu_usage_percentage`, `spotify_cache_hit_ratio`) por compatibilidade com os alertas 3 e 4 — avaliar na implementação a migração desses alertas para as métricas reais.

### B4. Métrica de Saturation (completar o USE)

- Novo gauge `spotify_http_requests_in_flight` em `services/main.py`, incrementado/decrementado por requisição (contexto `try/finally` nos 4 endpoints).
- Painel de **Saturação (Requisições em Processamento)** na Row 4.
- Alerta opcional `RequestSaturationHigh` (ex.: `> 50` por 2 min).

### B5. Dashboard `grafana/dashboards/spotify-overview.json`

- Row 2: painel de 5xx por região (B2).
- Row 4: métricas reais de node/redis (B3) + saturação (B4).

### B6. `README.md`

- Atualizar: porta do Alertmanager (9093), novos painéis, lista de alertas, tabela de acessos, referência às Figuras 1–3 do artigo e instruções de notificação Slack via `SLACK_WEBHOOK_URL`.

---

## C. Plano de verificação

1. `./start.sh` → stack completa no ar.
2. Validar scrape em `http://localhost:9090/targets` (`spotify-services`, `otel-collector`, `node-exporter`, `redis-exporter`, `alertmanager`).
3. Verificar `http://localhost:9090/alerts` com as regras ativas e o Alertmanager respondendo em `http://localhost:9093`.
4. Validar correlação Loki↔Tempo no Grafana Explore e o novo painel de região.
5. Conferir o `artigo.md` completo (A1–A9 + A7) contra o estado final do repositório.
6. Conferir `README.md` (B6) contra o estado final do repositório.

---

## Resumo de impacto

| Área | Itens | Tipo |
| :--- | :--- | :--- |
| `docs/artigo.md` | A1–A8 | Edição / redação de novas seções |
| `prometheus/alert_rules.yml` | A9 | Edição pontual |
| `docker-compose.yml` | B1, B3 | Novos serviços |
| `alertmanager/alertmanager.yml` | B1 | Novo arquivo |
| `prometheus/prometheus.yml` | B1, B3 | Novos scrape jobs |
| `loki/loki-config.yaml` | B1 | Correção de URL |
| `grafana/provisioning/datasources/datasources.yaml` | B1 | Novo datasource |
| `services/main.py` | B2, B4 | Labels + nova métrica |
| `grafana/dashboards/spotify-overview.json` | B2, B3, B4, B5 | Novos/atualizados painéis |
| `README.md` | B6 | Atualização de documentação |
