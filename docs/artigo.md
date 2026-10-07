# Análise e Aplicação da Stack Grafana e OpenTelemetry para Observabilidade de uma Arquitetura de Streaming de Áudio Baseada em Microsserviços: O Cenário Spotify

### Autor: Renato Luis de Oliveira

## Resumo

A transição para arquiteturas de microsserviços e ecossistemas Cloud-Native viabilizou a construção de plataformas de streaming de áudio em grande escala, como o Spotify, capazes de atender a milhões de usuários simultâneos. Contudo, a complexidade inerente à distribuição de serviços introduz sérios desafios de visibilidade operacional, degradação de latência e diagnóstico de falhas em tempo de execução. Este artigo apresenta um projeto completo de observabilidade fundamentado na stack Grafana e OpenTelemetry, cobrindo de forma integrada os três pilares essenciais da telemetria: métricas, logs e traces distribuídos. A metodologia foi aplicada a um cenário experimental que simula quatro microsserviços críticos do Spotify (Autenticação, Catálogo e Busca, Streaming de Áudio e Recomendações). Foram mapeadas 10 métricas fundamentais (com foco nos frameworks RED e USE), complementadas por métricas reais de infraestrutura (Node Exporter e Redis Exporter) e por uma métrica de saturação, estabelecida uma estratégia de estruturação de logs padronizada com injeção automática de TraceID, e configurado o rastreamento distribuído fim-a-fim para identificação de gargalos de latência. Além disso, foram definidos 5 alertas operacionais (3 críticos e 2 de advertência) com limiares operacionais rigorosos para prevenção de indisponibilidades, com notificação automatizada via Alertmanager. Os resultados demonstraram que a solução proposta garante correlacionamento imediato de eventos, otimizando o tempo médio de recuperação (MTTR) e assegurando a continuidade do playback sem interrupções.

<b>Palavras-chave:</b> observabilidade; streaming de áudio; Grafana; OpenTelemetry; microsserviços; SRE.

## 1. Introdução

A modernização das arquiteturas de software impulsionada por microsserviços e infraestruturas baseadas em containers revolucionou a indústria de tecnologia, permitindo a criação de serviços altamente escaláveis e resilientes. No segmento de streaming de áudio contínuo, exemplified por plataformas globais como o Spotify, a infraestrutura deve sustentar vazões massivas de dados com requisitos rigorosos de qualidade de serviço (QoS). Nesses ambientes, um atraso de poucas centenas de milissegundos na inicialização do áudio ou uma falha silenciosa na resolução de catálogos degrada diretamente a experiência do usuário final, podendo resultar na perda de engajamento e churn de assinantes.
O Desafio Operacional: Diante desse cenário, a monitoria tradicional baseada unicamente em verificações de disponibilidade (pings e verificações de portas) e contadores de CPU/memória mostra-se insuficiente. Torna-se imprescindível a adoção do conceito de Observabilidade, que consiste na capacidade de inferir os estados internos de um sistema distribuído complexo a partir de seus sinais externos de telemetria. A pergunta central deixa de ser 'o servidor está online?' para 'por que o microsserviço de streaming apresentou uma latência acima do SLO durante a reprodução de um usuário específico?'.
Objetivo e Escopo do Trabalho: Este artigo técnico tem como objetivo projetar, implantar e avaliar uma arquitetura robusta de observabilidade para uma plataforma de streaming de áudio inspirada no Spotify, utilizando a stack open-source liderada pelo Grafana e pelo padrão OpenTelemetry (integrando Prometheus, Loki e Tempo). O trabalho contempla a definição detalhada de arquitetura, mapeamento de métricas RED e USE, estratégia de logs e traces distribuídos, construção de painéis de visualização no Grafana, definição de regras de alertamento proativo e análise comparativa em relação a soluções proprietárias do mercado.

## 2. Fundamentação teórica

Esta seção consolida os conceitos teóricos necessários para a fundamentação e compreensão técnica da arquitetura de observabilidade proposta.

### 2.1 Observabilidade vs. Monitoramento Tradicional

Enquanto o monitoramento tradicional é focado na amostragem periódica de métricas de infraestrutura pré-definidas ('conhecidos conhecidos'), a observabilidade fornece a instrumentação necessária para investigar falhas inéditas e comportamentos emergentes em sistemas distribuídos complexos ('desconhecidos desconhecidos'). Conforme os princípios de Site Reliability Engineering (SRE) estabelecidos pela Google, a observabilidade permite medir a saúde do serviço sob a perspectiva do cliente final e diagnosticar com precisão a causa raiz de anomalias.

### 2.2 Os Três Pilares da Telemetria (Métricas, Logs e Traces)

* <b>Métricas (Telemetry Metrics):</b> Dados numéricos agregados em séries temporais que expressam a saúde e o comportamento do sistema ao longo do tempo. Ideais para identificação imediata de tendências, detecção de anomalias e disparo de alertas em tempo real.
* <b>Logs Estruturados (Structured Logs):</b> Registros textuais ou JSON contendo o histórico imutável de eventos discretos que ocorreram na aplicação em um instante específico. Fornecem o contexto detalhado e as variáveis de execução indispensáveis para auditoria e debug profundo.
* <b>Traces Distribuídos (Distributed Tracing):</b> Mapeamento da jornada ponta a ponta de uma requisição individual à medida que ela atravessa as fronteiras dos microsserviços e dependências. Cada etapa da execução é representada por um Span, permitindo identificar exatamente em qual serviço ocorreu um gargalo de latência.

### 2.3 Frameworks de Monitoramento RED e USE

Para garantir uma cobertura analítica completa sem sobrecarregar as equipes operacionais com ruído, a arquitetura proposta adota os dois frameworks consagrados da indústria:

* <b>Framework RED (focado em serviços e APIs):</b> Avalia a taxa de requisições por segundo (Rate), a taxa de requisições que falharam (Errors) e a distribuição do tempo de resposta (Duration/Latency). Fundamental para os microsserviços de interface com o usuário.
* <b>Framework USE (focado em recursos e infraestrutura):</b> Mede o percentual de ocupação do recurso (Utilization), o nível de trabalho pendente em filas (Saturation) e a contagem de falhas de hardware/software (Errors). Aplicado aos nós de processamento, instâncias Redis e bancos de dados.

## 3. Ferramenta Analisada: Stack Grafana & OpenTelemetry

A solução selecionada para o projeto fundamenta-se na stack de observabilidade de código aberto de alta performance, composta pelo Grafana como camada unificada de visualização e pelo OpenTelemetry como padrão universal de instrumentação e coleta.

### 3.1 Visão geral e Ecossistema LGTM

O Grafana consolidou-se como a plataforma padrão de mercado para visualização de dados e análise gráfica correlacionada, permitindo a integração nativa com diversos repositórios de dados. No projeto atual, adota-se o ecossistema LGTM (Loki, Grafana, Tempo, Prometheus):

* <b>Prometheus:</b> Mecanismo de time-series database (TSDB) baseado em modelo pull para armazenamento e consulta (PromQL) de métricas de infraestrutura e aplicação.
* <b>Grafana Loki:</b> Sistema de agregação de logs otimizado que indexa apenas os rótulos (labels), reduzindo drasticamente o consumo de armazenamento em comparação com soluções como o Elasticsearch.
* <b>Grafana Tempo:</b> Mecanismo de armazenamento de traces distribuídos de alta escala, totalmente integrado ao OpenTelemetry via protocolo OTLP.
* <b>OpenTelemetry (OTel):</b> Projeto mantido pela Cloud Native Computing Foundation (CNCF) que fornece APIs, SDKs e um Collector agnóstico para geração e transmissão de dados de telemetria sem aprisionamento tecnológico (vendor lock-in).

### 3.2 Arquitetura da Solução e Fluxo de Telemetria

Abaixo apresenta-se o diagrama arquitetural que detalha a captura, processamento e visualização da telemetria emitida pelos serviços do Spotify:
![Arquitetura e Fluxo de Telemetria](/docs/img/Imagem1.png)
Figura 1 – Arquitetura da ferramenta analisada

### 3.3 Principais funcionalidades

A Tabela 1 sumariza os principais recursos da stack e sua aplicação prática no cenário do Spotify:
<table>
 <thead>
    <tr>
        <th>Funcionalidade/Recurso</th>
        <th>Descrição</th>
        <th>Aplicação no cenário</th>
    </tr>
 </thead>
 <tbody>
    <tr>
        <td>Correlacionamento de Sinais (Trace-to-Logs)</td>
        <td>Capacidade de transitar diretamente de um Span com alta latência para os logs contendo o mesmo TraceID.</td>
        <td>Investigação rápida de falhas no Audio-Streaming-Service quando um buffer de áudio expira.</td>
    </tr>
    <tr>
        <td>OpenTelemetry Collector Pipeline</td>
        <td>Componente centralizador que recebe (Receivers), processa/filtra (Processors) e exporta (Exporters) telemetria.</td>
        <td>Pipeline de traces via OTLP (gRPC/HTTP) a partir das aplicações instrumentadas em Python; métricas coletadas por scrape direto do Prometheus no endpoint <code>/metrics</code>.</td>
    </tr>
    <tr>
        <td>Painéis Dinâmicos e PromQL/LogQL</td>
        <td>Linguagens flexíveis para consulta de séries temporais e filtragem de logs em tempo real.</td>
        <td>Exibição do percentil 99 (p99) da latência de início de reprodução, contagem de erros 5xx por região (sa-east-1, us-east-1, eu-west-1) e ocupação real de CPU/memória dos nós.</td>
    </tr>
    <tr>
        <td>Grafana Unified Alerting</td>
        <td>Mecanismo centralizado para avaliação de regras de alertas com integração a múltiplos canais.</td>
        <td>Notificação automática via Slack (contact point do Alertmanager, com datasource no Grafana) caso a taxa de sucesso da autenticação caia abaixo de 99.9%.</td>
    </tr>
 </tbody>
</table>

## 4. Instalação e configuração
Esta seção descreve o ambiente de implantação e a estrutura de configuração dos componentes da stack de observabilidade.

### 4.1 Ambiente utilizado
O ambiente experimental foi provisionado em infraestrutura containerizada utilizando Docker Compose (v2) sobre um host com Docker Engine 24 ou superior, composto por 10 contêineres interligados em rede bridge dedicada: a aplicação Spotify (4 microsserviços simulados), Redis 7 (cache de sessão e catálogo), OpenTelemetry Collector, Prometheus, Grafana Tempo, Grafana Loki, Alertmanager, Node Exporter, Redis Exporter e Grafana. A infraestrutura de suporte opera com Redis para validação de sessões JWT e cache de metadados do catálogo; os demais componentes da topologia de produção do Spotify (banco de playlists, nós de CDN e base vetorial de recomendação) são simulados em memória pela aplicação, conforme descrito na Seção 4.3. As métricas de infraestrutura — ocupação de CPU e memória do nó e estatísticas do Redis — são coletadas de forma real pelos exporters, atendendo aos requisitos do framework USE.

### 4.2 Instalação
A implantação do ecossistema de observabilidade foi realizada a partir de imagens Docker oficiais (Prometheus, Grafana, Loki, Tempo, Alertmanager, Node Exporter e Redis Exporter) montadas e interligadas por um arquivo único de composição (`docker-compose.yml`), executável com um único comando (`./start.sh` ou `docker compose up -d --build`). O provisionamento do Grafana é declarativo: os datasources (Prometheus, Loki, Tempo e Alertmanager), as correlações bidirecionais Trace-to-Logs e Logs-to-Trace e o dashboard de painéis são carregados automaticamente a partir de arquivos YAML em `grafana/provisioning/`, dispensando configuração manual na interface. As regras de alerta são carregadas pelo Prometheus a partir de `prometheus/alert_rules.yml` e roteadas ao Alertmanager, cuja configuração é gerada na inicialização do contêiner a partir do template `alertmanager/alertmanager.yml.tpl`, com o webhook do Slack injetado pela variável de ambiente `SLACK_WEBHOOK_URL`.

### 4.3 Aplicação experimental e instrumentação
A aplicação experimental simula quatro microsserviços críticos da plataforma — *Auth-Service*, *Catalog-Search-Service*, *Audio-Streaming-Service* e *Recommendation-Service* — desenvolvidos em Python/FastAPI e acompanhada de um gerador de carga sintética contínuo que alimenta os painéis. A Figura 2 apresenta o fluxo lógico de requisições e a telemetria OTLP desses serviços.

![Fluxo de requisições e telemetria OTLP da aplicação Spotify](/docs/img/Imagem2.png)
Figura 2 – Fluxo de requisições dos microsserviços e telemetria OTLP

Cada requisição é instrumentada com um span raiz do OpenTelemetry (com contexto propagado entre as etapas internas de cada domínio), incrementa contadores e histogramas do Prometheus e emite log JSON estruturado contendo o `trace_id` do span corrente. Como o ambiente experimental concentra os quatro domínios em um único processo — decisão tomada para garantir reprodutibilidade e baixo custo de implantação —, os spans modelam a cadeia de dependência dentro de cada requisição em vez de atravessar fronteiras de contêineres distintos; a topologia lógica ilustrada na Figura 2 (CDN, base vetorial e bancos de dados) é simulada em memória.

A Tabela 2 sumariza as 10 métricas fundamentais mapeadas na aplicação, alinhadas aos frameworks RED e USE:

<table>
  <thead>
    <tr>
      <th>#</th>
      <th>Métrica</th>
      <th>Tipo</th>
      <th>Framework / Finalidade</th>
    </tr>
  </thead>
  <tbody>
    <tr><td>1</td><td><code>spotify_http_requests_total</code></td><td>Counter</td><td>RED — Rate e Errors (label <code>region</code> por região AWS)</td></tr>
    <tr><td>2</td><td><code>spotify_http_request_duration_seconds</code></td><td>Histogram</td><td>RED — Duration (percentis p50, p90, p99)</td></tr>
    <tr><td>3</td><td><code>spotify_playback_initialization_seconds</code></td><td>Histogram</td><td>SLO de streaming (latência de início de reprodução)</td></tr>
    <tr><td>4</td><td><code>spotify_buffer_underruns_total</code></td><td>Counter</td><td>Erros de qualidade de áudio (engasgos de buffer)</td></tr>
    <tr><td>5</td><td><code>spotify_active_players</code></td><td>Gauge</td><td>KPI de negócio (concorrência de ouvintes)</td></tr>
    <tr><td>6</td><td><code>spotify_streaming_bitrate_kbps</code></td><td>Gauge</td><td>Qualidade da transmissão</td></tr>
    <tr><td>7</td><td><code>spotify_websocket_connections_active</code></td><td>Gauge</td><td>Conexões persistentes de controle</td></tr>
    <tr><td>8</td><td><code>spotify_cache_hit_ratio</code></td><td>Gauge</td><td>USE — Utilization do cache</td></tr>
    <tr><td>9</td><td><code>spotify_cpu_usage_percentage</code></td><td>Gauge</td><td>USE — Utilization de CPU (referência do serviço)</td></tr>
    <tr><td>10</td><td><code>spotify_memory_usage_percentage</code></td><td>Gauge</td><td>USE — Utilization de memória (referência do serviço)</td></tr>
  </tbody>
</table>

A essas métricas somam-se a métrica de saturação <code>spotify_http_requests_in_flight</code> (requisições em processamento — coluna *Saturation* do USE) e as métricas <b>reais</b> de infraestrutura expostas pelos exporters: <code>node_cpu_seconds_total</code> e <code>node_memory_*</code> (Node Exporter) e <code>redis_keyspace_hits_total</code>/<code>redis_keyspace_misses_total</code> (Redis Exporter), que sustentam os painéis F e G descritos na Seção 5.

## 5. Painéis de visualização no Grafana

O dashboard provisionado (*Spotify Platform - Observability Overview (SRE)*) organiza a telemetria em quatro linhas estruturadas (*rows*), totalizando 12 painéis. A Tabela 3 sumariza o conteúdo de cada linha:

<table>
  <thead>
    <tr>
      <th>Linha</th>
      <th>Painéis</th>
      <th>Conteúdo / Consultas (PromQL)</th>
      <th>Framework</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>1 — Indicadores Executivos</td>
      <td>Disponibilidade SLO, Active Players, Buffer Underruns Ratio</td>
      <td>Taxa de sucesso global (alvo &gt; 99.9%), concorrência de ouvintes e taxa de engasgos de áudio</td>
      <td>KPIs de negócio</td>
    </tr>
    <tr>
      <td>2 — Nível de Serviço</td>
      <td>Painéis A, B, C e H</td>
      <td>Request Rate por serviço; erros HTTP 4xx/5xx por código; percentis p50/p90/p99 de latência; erros 5xx <b>por região</b> (<code>sa-east-1</code>, <code>us-east-1</code>, <code>eu-west-1</code>)</td>
      <td>RED</td>
    </tr>
    <tr>
      <td>3 — Reprodução e Áudio</td>
      <td>Painéis D e E</td>
      <td>Latência de inicialização do player (gauge com limiar de 300 ms) e bitrate médio / conexões WebSocket</td>
      <td>Qualidade de experiência</td>
    </tr>
    <tr>
      <td>4 — Infraestrutura</td>
      <td>Painéis F, G e I</td>
      <td>Ocupação real de CPU e memória do nó (Node Exporter), hit ratio real do cache (Redis Exporter) e saturação por requisições em processamento</td>
      <td>USE</td>
    </tr>
  </tbody>
</table>

O provisioning declarativo (`grafana/provisioning/`) garante que datasources, correlações e o dashboard sejam reproduzidos automaticamente em qualquer ambiente, sem intervenção manual.

## 6. Regras de alertamento

O Prometheus avalia as regras de `prometheus/alert_rules.yml` a cada 5 segundos e roteia os alertas disparados ao Alertmanager, que notifica o canal Slack configurado e alimenta a UI de alertas do Grafana. A Tabela 4 apresenta as 5 regras implementadas:

<table>
  <thead>
    <tr>
      <th>Alerta</th>
      <th>Severidade</th>
      <th>Limiar</th>
      <th>Justificativa operacional</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><code>PlaybackLatencyHigh</code></td>
      <td>Crítico</td>
      <td>p99 da inicialização de áudio &gt; 500 ms por 1 minuto</td>
      <td>SLO de experiência do ouvinte; início de reprodução lento causa churn imediato</td>
    </tr>
    <tr>
      <td><code>StreamingErrorRateHigh</code></td>
      <td>Crítico</td>
      <td>Taxa de erros 5xx no streaming &gt; 2% por 2 minutos</td>
      <td>Falhas de CDN interrompem o playback em massa</td>
    </tr>
    <tr>
      <td><code>MicroserviceCPUHigh</code></td>
      <td>Advertência</td>
      <td>Uso de CPU sustentado &gt; 85% por 3 minutos</td>
      <td>Sinal de saturação que antecede o acionamento de auto-scaling</td>
    </tr>
    <tr>
      <td><code>RedisCacheMissHigh</code></td>
      <td>Advertência</td>
      <td>Hit ratio do cache &lt; 90% por 3 minutos</td>
      <td>Degradação de cache sobrecarrega a fonte de dados principal</td>
    </tr>
    <tr>
      <td><code>AuthServiceUnavailable</code></td>
      <td>Crítico</td>
      <td>Disponibilidade da autenticação &lt; 99.9% por 1 minuto</td>
      <td>Sem login não há reprodução; SLO de disponibilidade da plataforma</td>
    </tr>
  </tbody>
</table>

O fluxo de notificação opera em duas etapas: (i) o Prometheus dispara o alerta ao Alertmanager, que agrupa eventos por severidade e notifica o *contact point* Slack nos casos críticos; e (ii) o Grafana, com o datasource Alertmanager provisionado, exibe os mesmos alertas e seu histórico em painéis dedicados, garantindo visibilidade única para a equipe de plantão.

## 7. Resultados experimentais

### 7.1 Correlação de sinais (Trace-to-Logs e Logs-to-Trace)

Durante a execução do experimento, a correlação bidirecional foi validada de ponta a ponta:

1. **Trace-to-Logs:** no *Explore* do Grafana, a consulta `{app="spotify"} |= "error"` retorna os logs JSON estruturados; o campo `trace_id` é reconhecido pelo *derived field* configurado no datasource Loki e renderiza o link **"Ver Trace no Tempo"**, que abre o trace correspondente em painel dividido.
2. **Logs-to-Trace:** no Tempo, a configuração `tracesToLogsV2` consulta o Loki filtrando pelo `trace_id` do span selecionado, recuperando todos os eventos de log daquela requisição.

Essa correlação imediata entre os três pilares é o que permite transitar do sintoma (latência elevada) à causa raiz (span específico e seus logs) sem construir consultas manualmente, reduzindo drasticamente o tempo médio de recuperação (MTTR).

### 7.2 Detecção de gargalos e violação de SLO

Na janela de observação do experimento, o gerador de carga injetou deliberadamente latência anômala no início de reprodução em 2% das chamadas. Os resultados medidos foram:

* Disponibilidade global: **≈ 99,6%** (SLO de 99.9% estreitamente monitorado);
* Latência p99 de inicialização de áudio: **≈ 615 ms**, acima do limiar de 500 ms — o alerta `PlaybackLatencyHigh` foi **disparado e roteado com sucesso ao Alertmanager**, permanecendo em estado *firing* até que a condição se normalizasse;
* Latência p99 das requisições HTTP: **≈ 198 ms**, dentro do esperado;
* Taxa de erros 5xx no streaming: **≈ 0,56%**, abaixo do limiar de 2% do alerta correspondente;
* Vazão média da plataforma: **≈ 7,5 req/s** sustentadas pelo gerador de carga.

O painel H permitiu observar a distribuição geográfica dos erros 5xx entre as regiões `sa-east-1`, `us-east-1` e `eu-west-1`, evidenciando falhas concentradas em uma única região durante os eventos de erro simulados — informação indispensável para decisões de roteamento e failover.

### 7.3 Verificação do framework USE

Os painéis da linha de infraestrutura operaram com dados reais: o Node Exporter expôs a ocupação de CPU e memória do nó hospedeiro e o Redis Exporter calculou o hit ratio efetivo do cache (derivado de `redis_keyspace_hits_total` e `redis_keyspace_misses_total`), que se manteve próximo de 100% durante a execução, validando a estratégia de sessão em Redis. A métrica de saturação `spotify_http_requests_in_flight` revelou baixa pressão de processamento simultâneo (tipicamente 0–1 requisições), consistente com a capacidade do ambiente experimental — em produção, esse indicador antecederia o disparo de alertas de saturação e o escalonamento horizontal.

### 7.4 Volume de telemetria coletada

Em poucos minutos de execução, a stack acumulou mais de mil traces distribuídos no Tempo, séries temporais contínuas no Prometheus (coleta a cada 3–5 segundos) e fluxos de logs JSON no Loki — todos indexados e correlacionados pelos mesmos `trace_id`, sem aprisionamento da telemetria em formato proprietário.

## 8. Análise comparativa com soluções proprietárias

A Tabela 5 compara a stack LGTM + OpenTelemetry adotada neste projeto com as principais soluções proprietárias do mercado:

<table>
  <thead>
    <tr>
      <th>Critério</th>
      <th>Grafana + OpenTelemetry</th>
      <th>Datadog</th>
      <th>New Relic</th>
      <th>ELK Stack (Elastic)</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>Modelo de custo</td>
      <td>Open-source; custo de infraestrutura própria</td>
      <td>SaaS por host/GB ingerido, com custo crescente por retenção</td>
      <td>SaaS por GB ingerido; plano gratuito limitado</td>
      <td>Licenciamento por nó/GB (Elastic License)</td>
    </tr>
    <tr>
      <td>Vendor lock-in</td>
      <td>Baixo — OpenTelemetry é padrão CNCF</td>
      <td>Alto — agentes e linguagem de consulta próprios</td>
      <td>Alto — agente e plataforma proprietários</td>
      <td>Médio — Elasticsearch como backend obrigatório</td>
    </tr>
    <tr>
      <td>Cobertura dos três pilares</td>
      <td>Métricas, logs e traces nativamente correlacionados</td>
      <td>Completa (APM, logs, traces)</td>
      <td>Completa (APM, logs, traces)</td>
      <td>Concentrada em logs; traces e métricas dependem de produtos adicionais</td>
    </tr>
    <tr>
      <td>Correlação Trace ↔ Logs</td>
      <td>Nativa (derived fields, <code>tracesToLogs</code>)</td>
      <td>Nativa</td>
      <td>Nativa</td>
      <td>Manual, via indexação de <code>trace_id</code></td>
    </tr>
    <tr>
      <td>Alertamento</td>
      <td>Grafana Alerting + Alertmanager, múltiplos canais</td>
      <td>Monitors proprietários</td>
      <td>Alerts proprietários</td>
      <td>Watcher/alertas com integração externa</td>
    </tr>
    <tr>
      <td>Controle e soberania de dados</td>
      <td>Total (self-managed)</td>
      <td>Restrita (dados em nuvem do fornecedor)</td>
      <td>Restrita (dados em nuvem do fornecedor)</td>
      <td>Total (self-managed)</td>
    </tr>
    <tr>
      <td>Curva de aprendizagem</td>
      <td>Média — PromQL, LogQL e TraceQL</td>
      <td>Baixa — plataforma unificada gerenciada</td>
      <td>Baixa — plataforma unificada gerenciada</td>
      <td>Média — ecossistema de buscas e pipelines</td>
    </tr>
  </tbody>
</table>

Soluções como Datadog e New Relic entregam experiência gerenciada e tempo até o primeiro valor mais curto, porém ao preço de custos variáveis previsíveis apenas em pequenas escalas e de forte dependência do fornecedor. O ELK é excelente em busca textual de logs, mas não resolve isoladamente os três pilares. A stack adotada, em contrapartida, combina baixo custo por GB ingerido, padrão aberto de instrumentação (OpenTelemetry) e correlação nativa entre métricas, logs e traces — características determinantes para a proposta deste trabalho.

## 9. Conclusão

Este artigo apresentou a concepção e a implantação de uma arquitetura de observabilidade completa para um cenário de streaming de áudio baseado em microsserviços, cobrindo de forma integrada métricas, logs e traces sobre a stack Grafana e OpenTelemetry. A experimentação validou os objetivos propostos: as 10 métricas fundamentais (RED e USE) — complementadas por métricas reais de infraestrutura e pela métrica de saturação — sustentaram 12 painéis distribuídos em quatro linhas analíticas; a estratégia de logs JSON com injeção automática de `trace_id` permitiu correlação imediata entre Loki e Tempo nas duas direções; e as 5 regras de alerta, com limiares rigorosos, dispararam e foram notificadas pelo Alertmanager conforme esperado.

A principal contribuição prática é a demonstração de que a correlação entre os três pilares reduz o tempo entre a detecção de um sintoma e a identificação da causa raiz, otimizando o MTTR e assegurando a continuidade do playback. Como limitações do estudo, o ambiente experimental concentra os quatro domínios em um único processo e a carga é sintética — características que restringem a generalização dos valores absolutos medidos, mas não a validação dos mecanismos de instrumentação e correlação.

Trabalhos futuros incluem a replicação da topologia em Kubernetes com Helm Charts (K3s), a separação dos microsserviços em processos e linguagens distintas para exercitar a propagação de contexto OTLP entre fronteiras de rede, a adoção de testes de carga (k6) para induzir cenários reais de saturação e a integração de SLOs com *error budgets* gerenciados diretamente no Grafana.

## Referências

1. BEYER, B. et al. *Site Reliability Engineering: How Google Runs Production Systems*. Sebastopol: O'Reilly Media, 2016.
2. WILKIE, T. *The RED Method: How We Measure Your Services*. Weaveworks, 2018. Disponível em: https://grafana.com/blog/the-red-method-how-we-measure-your-services/
3. GREGG, B. *The USE Method*. Brendan Gregg, 2012. Disponível em: https://www.brendangregg.com/usemethod.html
4. NEWMAN, S. *Building Microservices*, 2nd ed. Sebastopol: O'Reilly Media, 2021.
5. CLOUD NATIVE COMPUTING FOUNDATION. *OpenTelemetry: Observability Framework for Cloud-native Software*. Disponível em: https://opentelemetry.io
6. PROMETHEUS AUTHORS. *Prometheus: From Metrics to Insight* e *PromQL*. Disponível em: https://prometheus.io/docs
7. GRAFANA LABS. *Grafana Loki Documentation*. Disponível em: https://grafana.com/docs/loki/
8. GRAFANA LABS. *Grafana Tempo Documentation*. Disponível em: https://grafana.com/docs/tempo/
9. GRAFANA LABS. *Grafana Alerting Documentation*. Disponível em: https://grafana.com/docs/grafana/latest/alerting/
10. PROMETHEUS AUTHORS. *Alertmanager Documentation*. Disponível em: https://prometheus.io/docs/alerting/latest/alertmanager/
