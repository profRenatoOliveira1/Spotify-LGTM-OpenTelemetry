# =============================================================================
# PROMETHEUS ALERTMANAGER - CONFIGURACAO TEMPLATE
# O placeholder __SLACK_WEBHOOK_URL__ e substituido no boot do contêiner
# pela variavel de ambiente SLACK_WEBHOOK_URL (ver docker-compose.yml).
# =============================================================================
global:
  resolve_timeout: 5m

route:
  receiver: 'null'
  group_by: ['alertname', 'severity']
  group_wait: 10s
  group_interval: 1m
  repeat_interval: 4h
  routes:
    # Alertas criticos sao notificados no Slack
    - receiver: 'slack-critical'
      matchers:
        - severity = "critical"
      group_wait: 30s
      continue: false
    # Alertas de advertencia (warning) ficam visiveis apenas na UI do Alertmanager
    - receiver: 'null'
      matchers:
        - severity = "warning"

receivers:
  - name: 'null'

  - name: 'slack-critical'
    slack_configs:
      - api_url: '__SLACK_WEBHOOK_URL__'
        channel: '#observability-alerts'
        send_resolved: true
        title: '{{ .Status | toUpper }} [{{ .CommonLabels.alertname }}] - {{ .CommonLabels.severity }}'
        text: |
          {{ range .Alerts }}
          *Serviço:* {{ .Labels.service | default "infraestrutura" }}
          *Resumo:* {{ .Annotations.summary }}
          *Detalhe:* {{ .Annotations.description }}
          {{ end }}
