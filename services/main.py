import os
import time
import json
import random
import logging
import asyncio
import functools
import threading
from typing import Optional

from fastapi import FastAPI, Request, Response, HTTPException, status
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
import redis
import requests

from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    generate_latest,
    CONTENT_TYPE_LATEST,
)

# OpenTelemetry imports
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.trace import format_trace_id, format_span_id

# Environment variables
OTEL_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4317")
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
LOKI_URL = os.getenv("LOKI_URL", "http://loki:3100/loki/api/v1/push")

# Setup OpenTelemetry Tracer
resource = Resource.create({"service.name": "spotify-backend-platform"})
provider = TracerProvider(resource=resource)
try:
    otlp_exporter = OTLPSpanExporter(endpoint=OTEL_ENDPOINT, insecure=True)
    provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
except Exception as e:
    print(f"Warning: Failed to initialize OTLP Span Exporter: {e}")
trace.set_tracer_provider(provider)
tracer = trace.get_tracer("spotify.observability", "1.0.0")

# Setup Redis Client
redis_client = None
try:
    redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
except Exception as e:
    print(f"Warning: Failed to connect to Redis: {e}")

# -------------------------------------------------------------
# DEFINIÇÃO DAS 10+ MÉTRICAS PROMETHEUS (CONFORME ATIVIDADE 04)
# -------------------------------------------------------------
REGIONS = ["sa-east-1", "us-east-1", "eu-west-1"]

REQUESTS_TOTAL = Counter(
    "spotify_http_requests_total",
    "Total acumulado de requisições HTTP na plataforma",
    ["service", "endpoint", "method", "status", "region"],
)

REQUEST_DURATION_SECONDS = Histogram(
    "spotify_http_request_duration_seconds",
    "Latência de resposta HTTP em segundos (Percentis p50, p90, p99)",
    ["service", "endpoint"],
    buckets=[0.01, 0.025, 0.05, 0.075, 0.1, 0.2, 0.3, 0.5, 0.8, 1.2, 2.5],
)

PLAYBACK_INIT_SECONDS = Histogram(
    "spotify_playback_initialization_seconds",
    "Tempo de inicialização do áudio (buffer inicial / startup latency)",
    buckets=[0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5, 0.7, 1.0],
)

ACTIVE_PLAYERS = Gauge(
    "spotify_active_players",
    "Número estimado de players de música ativos simultaneamente",
)

STREAMING_BITRATE_KBPS = Gauge(
    "spotify_streaming_bitrate_kbps",
    "Bitrate médio da transmissão de streaming de áudio em kbps",
)

BUFFER_UNDERRUNS_TOTAL = Counter(
    "spotify_buffer_underruns_total",
    "Total acumulado de interrupções por esgotamento de buffer de mídia",
    ["service"],
)

CACHE_HIT_RATIO = Gauge(
    "spotify_cache_hit_ratio",
    "Índice de acerto no cache Redis (Hit Ratio de 0.0 a 1.0)",
)

CPU_USAGE_PERCENTAGE = Gauge(
    "spotify_cpu_usage_percentage",
    "Percentual de ocupação estimada de CPU dos nós",
)

MEMORY_USAGE_PERCENTAGE = Gauge(
    "spotify_memory_usage_percentage",
    "Percentual de consumo de memória RAM dos nós",
)

WEBSOCKET_CONNECTIONS_ACTIVE = Gauge(
    "spotify_websocket_connections_active",
    "Quantidade de conexões persistentes de controle de reprodução",
)

IN_FLIGHT = Gauge(
    "spotify_http_requests_in_flight",
    "Requisições HTTP em processamento no momento (métrica de Saturation do framework USE)",
)

# Inicialização de valores padrão
ACTIVE_PLAYERS.set(45200)
STREAMING_BITRATE_KBPS.set(320)
CACHE_HIT_RATIO.set(0.965)
CPU_USAGE_PERCENTAGE.set(62.4)
MEMORY_USAGE_PERCENTAGE.set(58.1)
WEBSOCKET_CONNECTIONS_ACTIVE.set(43100)

# -------------------------------------------------------------
# DECORATOR DE SATURAÇÃO (MÉTRICA USE: REQUISIÇÕES EM PROCESSAMENTO)
# -------------------------------------------------------------
def tracked(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        IN_FLIGHT.inc()
        try:
            return func(*args, **kwargs)
        finally:
            IN_FLIGHT.dec()
    return wrapper

# -------------------------------------------------------------
# FUNÇÃO DE LOGGING ESTRUTURADO (JSON) PARA GRAFANA LOKI
# -------------------------------------------------------------
def emit_loki_log(service: str, level: str, message: str, trace_id: str, span_id: str, extra: dict = None):
    log_data = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "level": level,
        "service": service,
        "trace_id": trace_id,
        "span_id": span_id,
        "message": message,
    }
    if extra:
        log_data.update(extra)

    # Print to container stdout
    print(json.dumps(log_data))

    # Send directly to Loki HTTP push endpoint in background thread
    def push():
        try:
            ts_ns = str(time.time_ns())
            payload = {
                "streams": [
                    {
                        "stream": {
                            "service": service,
                            "level": level,
                            "app": "spotify"
                        },
                        "values": [
                            [ts_ns, json.dumps(log_data)]
                        ]
                    }
                ]
            }
            requests.post(LOKI_URL, json=payload, timeout=0.5)
        except Exception:
            pass

    threading.Thread(target=push, daemon=True).start()

# -------------------------------------------------------------
# FASTAPI APPLICATION & MIDDLEWARE
# -------------------------------------------------------------
app = FastAPI(
    title="Spotify Platform Microservices Simulator",
    description="Simulador de microsserviços instrumentados com OpenTelemetry, Prometheus e Loki para o IFMT",
    version="1.0.0"
)

class LoginRequest(BaseModel):
    username: str
    password: str

@app.get("/metrics")
def get_metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get("/health")
def get_health():
    return {"status": "UP", "timestamp": time.time()}

# -------------------------------------------------------------
# 1. AUTH-SERVICE (LOGIN E SESSÕES JWT)
# -------------------------------------------------------------
@app.post("/api/v1/auth/login")
@tracked
def auth_login(req: LoginRequest):
    service = "auth-service"
    endpoint = "/api/v1/auth/login"
    start_time = time.time()
    region = random.choice(REGIONS)

    with tracer.start_as_current_span("auth.login") as span:
        trace_id = format_trace_id(span.get_span_context().trace_id)
        span_id = format_span_id(span.get_span_context().span_id)
        span.set_attribute("user.name", req.username)

        # Injeção de falha simulada (0.5% de erro 500)
        is_error = random.random() < 0.005
        status_code = "500" if is_error else "200"

        # Simulação de latência (30ms - 80ms)
        simulated_delay = random.uniform(0.03, 0.08)
        time.sleep(simulated_delay)

        if is_error:
            emit_loki_log(service, "ERROR", f"Falha de autenticação para usuário {req.username}: timeout interno", trace_id, span_id)
            REQUESTS_TOTAL.labels(service=service, endpoint=endpoint, method="POST", status=status_code, region=region).inc()
            REQUEST_DURATION_SECONDS.labels(service=service, endpoint=endpoint).observe(time.time() - start_time)
            raise HTTPException(status_code=500, detail="Erro interno de autenticação")

        # Consulta e grava sessão no Redis (a consulta alimenta o hit ratio real do redis_exporter)
        try:
            if redis_client:
                redis_client.get(f"session:{req.username}")
                redis_client.setex(f"session:{req.username}", 3600, "token_simulado_jwt")
        except Exception:
            pass

        emit_loki_log(service, "INFO", f"Usuário {req.username} autenticado com sucesso via JWT", trace_id, span_id)
        REQUESTS_TOTAL.labels(service=service, endpoint=endpoint, method="POST", status=status_code, region=region).inc()
        REQUEST_DURATION_SECONDS.labels(service=service, endpoint=endpoint).observe(time.time() - start_time)

        return {"status": "authenticated", "token": f"jwt_{trace_id}", "user": req.username}

# -------------------------------------------------------------
# 2. CATALOG-SEARCH-SERVICE (BUSCA DE ARTISTAS E MÚSICAS)
# -------------------------------------------------------------
@app.get("/api/v1/catalog/search")
@tracked
def catalog_search(query: Optional[str] = "The Beatles"):
    service = "catalog-search-service"
    endpoint = "/api/v1/catalog/search"
    start_time = time.time()
    region = random.choice(REGIONS)

    with tracer.start_as_current_span("catalog.search") as span:
        trace_id = format_trace_id(span.get_span_context().trace_id)
        span_id = format_span_id(span.get_span_context().span_id)
        span.set_attribute("search.query", query)

        # Simula Cache Hit / Miss
        is_cache_hit = random.random() < 0.95
        delay = random.uniform(0.02, 0.05) if is_cache_hit else random.uniform(0.12, 0.28)
        time.sleep(delay)

        # 1% de erro 404/500
        is_error = random.random() < 0.01
        status_code = "500" if is_error else "200"

        if is_error:
            emit_loki_log(service, "WARN", f"Falha ao consultar índice de catálogo para query '{query}'", trace_id, span_id)
            REQUESTS_TOTAL.labels(service=service, endpoint=endpoint, method="GET", status="500", region=region).inc()
            REQUEST_DURATION_SECONDS.labels(service=service, endpoint=endpoint).observe(time.time() - start_time)
            raise HTTPException(status_code=500, detail="Catálogo temporariamente indisponível")

        emit_loki_log(service, "INFO", f"Busca no catálogo realizada: '{query}' (Cache Hit: {is_cache_hit})", trace_id, span_id)
        REQUESTS_TOTAL.labels(service=service, endpoint=endpoint, method="GET", status="200", region=region).inc()
        REQUEST_DURATION_SECONDS.labels(service=service, endpoint=endpoint).observe(time.time() - start_time)

        return {
            "query": query,
            "cache_hit": is_cache_hit,
            "results": [
                {"id": "track_101", "title": f"Música de {query}", "duration_s": 210},
                {"id": "track_102", "title": f"Sucesso ao vivo de {query}", "duration_s": 195}
            ]
        }

# -------------------------------------------------------------
# 3. AUDIO-STREAMING-SERVICE (CHUNK DE ÁUDIO & BUFFER TIME)
# -------------------------------------------------------------
@app.get("/api/v1/streaming/track/{track_id}")
@tracked
def stream_audio(track_id: str, chunk: int = 1):
    service = "audio-streaming-service"
    endpoint = "/api/v1/streaming/track"
    start_time = time.time()
    region = random.choice(REGIONS)

    with tracer.start_as_current_span("audio.stream_chunk") as span:
        trace_id = format_trace_id(span.get_span_context().trace_id)
        span_id = format_span_id(span.get_span_context().span_id)
        span.set_attribute("audio.track_id", track_id)
        span.set_attribute("audio.chunk", chunk)

        # Calcula tempo de buffer inicial (startup latency) se for chunk 1
        if chunk == 1:
            startup_time = random.uniform(0.12, 0.38)
            # 2% de probabilidade de startup lento (> 500ms) para gerar alerta p99
            if random.random() < 0.02:
                startup_time = random.uniform(0.52, 0.75)
            PLAYBACK_INIT_SECONDS.observe(startup_time)

        # 0.8% de probabilidade de buffer underrun
        if random.random() < 0.008:
            BUFFER_UNDERRUNS_TOTAL.labels(service=service).inc()
            emit_loki_log(service, "WARN", f"Buffer underrun detectado no track {track_id} chunk {chunk}", trace_id, span_id)

        # 1.2% de erro 503/500
        is_error = random.random() < 0.012
        if is_error:
            emit_loki_log(service, "ERROR", f"Falha de streaming na CDN para track {track_id}", trace_id, span_id)
            REQUESTS_TOTAL.labels(service=service, endpoint=endpoint, method="GET", status="503", region=region).inc()
            REQUEST_DURATION_SECONDS.labels(service=service, endpoint=endpoint).observe(time.time() - start_time)
            raise HTTPException(status_code=503, detail="CDN Edge buffer indisponível")

        simulated_delay = random.uniform(0.01, 0.04)
        time.sleep(simulated_delay)

        REQUESTS_TOTAL.labels(service=service, endpoint=endpoint, method="GET", status="200", region=region).inc()
        REQUEST_DURATION_SECONDS.labels(service=service, endpoint=endpoint).observe(time.time() - start_time)

        return {"track_id": track_id, "chunk": chunk, "bitrate_kbps": 320, "bytes": 65536}

# -------------------------------------------------------------
# 4. RECOMMENDATION-SERVICE (RECOMENDAÇÕES PERSONALIZADAS)
# -------------------------------------------------------------
@app.get("/api/v1/recommendations/user/{user_id}")
@tracked
def get_recommendations(user_id: str):
    service = "recommendation-service"
    endpoint = "/api/v1/recommendations/user"
    start_time = time.time()
    region = random.choice(REGIONS)

    with tracer.start_as_current_span("recommendation.vector_calc") as span:
        trace_id = format_trace_id(span.get_span_context().trace_id)
        span_id = format_span_id(span.get_span_context().span_id)
        span.set_attribute("recommendation.user_id", user_id)

        delay = random.uniform(0.06, 0.14)
        time.sleep(delay)

        emit_loki_log(service, "INFO", f"Geradas 10 recomendações vetoriais para usuário {user_id}", trace_id, span_id)
        REQUESTS_TOTAL.labels(service=service, endpoint=endpoint, method="GET", status="200", region=region).inc()
        REQUEST_DURATION_SECONDS.labels(service=service, endpoint=endpoint).observe(time.time() - start_time)

        return {"user_id": user_id, "recommendations": ["track_501", "track_502", "track_503"]}

# -------------------------------------------------------------
# GERADOR DE CARGA EM SEGUNDO PLANO (TRAFFIC SIMULATOR)
# -------------------------------------------------------------
def background_traffic_simulator():
    """Gera requisições contínuas para alimentar os dashboards e métricas."""
    print("Gerador de tráfego sintético iniciado...")
    tracks = ["bohemian_rhapsody", "shape_of_you", "blinding_lights", "stay", "starboy"]
    users = ["user_lucas", "user_marcos", "user_ana", "user_juliana", "user_carlos"]

    while True:
        try:
            # 1. Simula oscilações de recursos
            base_players = random.randint(42000, 48000)
            ACTIVE_PLAYERS.set(base_players)
            WEBSOCKET_CONNECTIONS_ACTIVE.set(int(base_players * random.uniform(0.92, 0.98)))
            STREAMING_BITRATE_KBPS.set(random.choice([320, 320, 320, 256]))
            CACHE_HIT_RATIO.set(random.uniform(0.94, 0.985))
            CPU_USAGE_PERCENTAGE.set(random.uniform(55.0, 78.0))
            MEMORY_USAGE_PERCENTAGE.set(random.uniform(52.0, 66.0))

            # 2. Executa requisição de Auth
            u = random.choice(users)
            try:
                auth_login(LoginRequest(username=u, password="secret_password"))
            except Exception:
                pass

            # 3. Executa requisições de Busca
            try:
                catalog_search(query=random.choice(["Queen", "Ed Sheeran", "The Weeknd", "Alok"]))
            except Exception:
                pass

            # 4. Executa requisições de Streaming
            tr = random.choice(tracks)
            for c in range(1, random.randint(2, 4)):
                try:
                    stream_audio(track_id=tr, chunk=c)
                except Exception:
                    pass

            # 5. Recomendações
            try:
                get_recommendations(user_id=u)
            except Exception:
                pass

            time.sleep(random.uniform(0.2, 0.6))
        except Exception as e:
            time.sleep(1)

@app.on_event("startup")
def start_traffic_generator():
    t = threading.Thread(target=background_traffic_simulator, daemon=True)
    t.start()
