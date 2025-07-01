# tradesphere-97249-e8864a23

## Running the backend FastAPI service

Navigate to the backend_api_service folder and start the server using:

```bash
cd backend_api_service
python -m src.api
# or, directly with uvicorn:
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

- App expects SQLite DB at `tradesphere.sqlite3` by default.
- Health check: [GET /health](http://localhost:8000/health)
- OpenAPI docs: [http://localhost:8000/docs](http://localhost:8000/docs)

If behind a reverse proxy, ensure upstream connections are directed to port 8000, and CORS is enabled for browsers.