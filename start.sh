#!/usr/bin/env bash
# ==============================================================================
# PROJETO FINAL DE OBSERVABILIDADE - PLATAFORMA SPOTIFY (IFMT - ATIVIDADE 04)
# Script de Inicialização Automatizada da Stack Completa
# ==============================================================================

set -e

echo "======================================================================"
echo "   INICIANDO A STACK DE OBSERVABILIDADE DO SPOTIFY (ECOSSISTEMA LGTM) "
echo "======================================================================"
echo ""

# Verifica se o Docker e Docker Compose estão instalados
if ! command -v docker &> /dev/null; then
    echo "Erro: Docker não encontrado. Instale o Docker antes de continuar."
    exit 1
fi

if ! docker compose version &> /dev/null; then
    echo "Erro: Docker Compose (V2) não encontrado."
    exit 1
fi

echo "[1/4] Parando contêineres antigos (se houver)..."
docker compose down --remove-orphans || true

echo "[2/4] Construindo as imagens e iniciando os serviços..."
docker compose up -d --build

echo "[3/4] Aguardando a estabilização dos serviços (15 segundos)..."
sleep 15

echo "[4/4] Verificando status dos contêineres..."
docker compose ps

echo ""
echo "======================================================================"
echo "   SISTEMA DE OBSERVABILIDADE OPERACIONAL COM SUCESSO!                "
echo "======================================================================"
echo ""
echo "Acesse os serviços em seu navegador:"
echo " -> Grafana Dashboards: http://localhost:3000 (User: admin | Pass: admin)"
echo "    Painel: Spotify Platform -> Spotify Platform - Observability Overview"
echo ""
echo " -> Prometheus (Métricas & Alertas): http://localhost:9090"
echo "    Regras de Alerta ativas em: http://localhost:9090/alerts"
echo ""
echo " -> Swagger API (Microsserviços Spotify): http://localhost:8000/docs"
echo " -> Métricas brutas da aplicação:        http://localhost:8000/metrics"
echo ""
echo "O gerador de tráfego sintético em segundo plano já está emitindo"
echo "métricas, logs estruturados (JSON) e traces distribuídos (OTel)!"
echo "======================================================================"
