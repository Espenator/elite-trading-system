# Brain Service (PC2)

gRPC-based LLM inference service that runs on PC2 (ProfitTrader GPU machine).
Uses Ollama for local LLM inference.

## Prerequisites

1. Install Ollama: https://ollama.ai
2. Pull a model: `ollama pull llama3.2`
3. Ensure Ollama is running: `ollama serve`

## Setup

```bash
cd brain_service
pip install -r requirements.txt
python compile_proto.py
```

## Run

```bash
python server.py
```

Default port: 50051

## Configuration (Environment Variables)

| Variable | Default | Description |
|----------|---------|-------------|
| BRAIN_PORT | 50051 | gRPC server port |
| BRAIN_MAX_WORKERS | 4 | Thread pool size |
| OLLAMA_HOST | localhost | Ollama server host |
| OLLAMA_PORT | 11434 | Ollama server port |
| OLLAMA_MODEL | llama3.2 | Model to use for inference |
| OLLAMA_TIMEOUT | 30 | Request timeout (seconds) |
| LOG_LEVEL | INFO | Logging level |

## Firewall (Dual-PC Setup)

If running on a separate PC from the backend, allow inbound TCP on port 50051:

```powershell
netsh advfirewall firewall add rule name="Brain Service gRPC" dir=in action=allow protocol=TCP localport=50051
```

On PC1, set `BRAIN_HOST` to PC2's IP address.
