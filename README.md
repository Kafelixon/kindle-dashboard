# Kindle Dashboard Renderer

## Build

Install the build tooling:

```bash
conda install -c conda-forge conda-build
```

Build the conda package from the recipe:

```bash
conda build recipe
```

Install the locally built package:

```bash
conda install --use-local kindle-dashboard-renderer
```

## Run

Render a dashboard image:

```bash
kindle-dashboard render dashboard.png
```

Run the HTTP server:

```bash
kindle-dashboard serve --host 127.0.0.1 --port 8000
```

Check the server:

```bash
curl http://127.0.0.1:8000/health
```

Fetch the rendered dashboard PNG:

```bash
curl -o dashboard.png http://127.0.0.1:8000/dashboard.png
```
