# Run CSOS in GitHub Codespaces

Create a Codespace from the repository branch, wait for the container setup to
finish, then run:

```bash
docker compose up --build -d
docker compose exec ollama ollama pull llama3.1
docker compose ps
```

Open the forwarded **CSOS Web** port (3000) and sign in with the development
account shown in the main README. Port visibility should remain **Private**.
The model download can take several minutes and uses several gigabytes. A
machine type with at least 4 cores and 16 GB RAM is recommended for local model
inference. The rest of the platform can be demonstrated before the model is
downloaded; AI requests return a clear availability error until Ollama is ready.

To reset demonstration data:

```bash
docker compose down -v
docker compose up --build -d
```
