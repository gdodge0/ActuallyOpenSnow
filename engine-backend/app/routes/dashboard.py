"""Dashboard HTML views."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter()


DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ActuallyOpenSnow Engine Dashboard</title>
    <style>
        body { font-family: system-ui, -apple-system, sans-serif; margin: 0; padding: 20px; background: #0f172a; color: #e2e8f0; }
        h1 { color: #38bdf8; }
        .card { background: #1e293b; border-radius: 8px; padding: 16px; margin: 12px 0; }
        .card h2 { margin-top: 0; color: #94a3b8; font-size: 14px; text-transform: uppercase; }
        .metric { font-size: 24px; font-weight: bold; color: #f8fafc; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 8px 12px; text-align: left; border-bottom: 1px solid #334155; }
        th { color: #94a3b8; font-size: 12px; text-transform: uppercase; }
        .status-completed { color: #4ade80; }
        .status-failed { color: #f87171; }
        .status-processing { color: #fbbf24; }
        .status-pending { color: #94a3b8; }
        .refresh-btn { background: #3b82f6; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; }
        .refresh-btn:hover { background: #2563eb; }
    </style>
</head>
<body>
    <h1>ActuallyOpenSnow Engine</h1>
    <button class="refresh-btn" onclick="loadAll()">Refresh</button>

    <div class="grid" id="metrics"></div>

    <div class="card">
        <h2>Model Status</h2>
        <table id="models-table">
            <thead><tr><th>Model</th><th>Provider</th><th>Interval</th><th>Last Run</th><th>Status</th><th>Action</th></tr></thead>
            <tbody></tbody>
        </table>
    </div>

    <div class="card">
        <h2>Recent Jobs</h2>
        <table id="jobs-table">
            <thead><tr><th>Type</th><th>Model</th><th>Status</th><th>Started</th><th>Duration</th><th>Resorts</th><th>Error</th></tr></thead>
            <tbody></tbody>
        </table>
    </div>

    <script>
        async function loadMetrics() {
            const res = await fetch('/api/engine/metrics');
            const data = await res.json();
            document.getElementById('metrics').innerHTML = `
                <div class="card"><h2>Jobs (24h)</h2><div class="metric">${data.last_24h.completed_jobs} / ${data.last_24h.total_jobs}</div></div>
                <div class="card"><h2>Error Rate</h2><div class="metric">${(data.last_24h.error_rate * 100).toFixed(1)}%</div></div>
                <div class="card"><h2>Cache Size</h2><div class="metric">${data.cache_size_mb} MB</div></div>
                <div class="card"><h2>Total Blends</h2><div class="metric">${data.total_blend_forecasts}</div></div>
            `;
        }

        async function loadModels() {
            const res = await fetch('/api/engine/models');
            const models = await res.json();
            const tbody = document.querySelector('#models-table tbody');
            tbody.innerHTML = models.map(m => `
                <tr>
                    <td><strong>${m.display_name}</strong></td>
                    <td>${m.provider}</td>
                    <td>${m.update_interval_hours}h</td>
                    <td>${m.last_run.run_datetime || 'Never'}</td>
                    <td class="status-${m.last_run.status}">${m.last_run.status}</td>
                    <td><button class="refresh-btn" onclick="triggerRun('${m.model_id}')" style="font-size:12px;padding:4px 8px">Run</button></td>
                </tr>
            `).join('');
        }

        async function loadJobs() {
            const res = await fetch('/api/engine/jobs?limit=20');
            const data = await res.json();
            const tbody = document.querySelector('#jobs-table tbody');
            tbody.innerHTML = data.jobs.map(j => `
                <tr>
                    <td>${j.job_type}</td>
                    <td>${j.model_id || '-'}</td>
                    <td class="status-${j.status}">${j.status}</td>
                    <td>${j.started_at ? new Date(j.started_at).toLocaleString() : '-'}</td>
                    <td>${j.duration_seconds ? j.duration_seconds.toFixed(1) + 's' : '-'}</td>
                    <td>${j.resorts_processed || 0}</td>
                    <td style="color:#f87171;font-size:12px">${j.error || ''}</td>
                </tr>
            `).join('');
        }

        async function triggerRun(modelId) {
            if (!confirm(`Trigger ${modelId} run?`)) return;
            const res = await fetch(`/api/engine/models/${modelId}/run`, {method: 'POST'});
            const data = await res.json();
            alert(JSON.stringify(data, null, 2));
            loadAll();
        }

        function loadAll() { loadMetrics(); loadModels(); loadJobs(); }
        loadAll();
        setInterval(loadAll, 30000);
    </script>
</body>
</html>
"""


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """Engine dashboard HTML page."""
    return DASHBOARD_HTML
