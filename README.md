# Secret Language App Sets - Backend

## Publishing

Generate the `public/` folder from `sets/`:

```bash
python3 publish.py
```

This copies set data from `sets/<lang>/<set>/out/` to `public/<lang>/<set>/` and generates index files.

## Running Locally

Start the static file server with CORS enabled:

```bash
python3 serve.py
```

This serves files from the current directory at `http://localhost:8080/`.

The server enables CORS headers to allow requests from local frontend development servers (e.g., Vite on port 5173).
