"""FastAPI 接口：UDS 测试用例自动生成。

启动方式：
    uvicorn src.uds_agent.api:app --host 0.0.0.0 --port 8000 --reload

端点：
    GET  /                — 前端页面
    POST /api/generate    — 上传 Excel + 选择服务 → 返回测试用例 JSON
    POST /api/generate/stream — SSE 流式生成，每完成一个服务推送一次
    POST /api/export      — 上传 Excel + 选择服务 → 下载生成的 Excel
    GET  /api/services    — 返回支持的服务列表
    GET  /health          — 健康检查
"""

from __future__ import annotations

import io
import json
import logging
import os
import sys
import tempfile
import time
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse

# 将 src/ 加入 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from .excel_export import export_to_excel
from .generate_pipeline import UDSGeneratePipeline
from .prompt_loader import SERVICE_NAMES, load_config

logger = logging.getLogger("api")

# ── 日志配置：同时输出到控制台和文件 ──────────────────────────────
_LOG_DIR = Path(__file__).parent.parent.parent / "logs"
_LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(_LOG_DIR / "app.log", encoding="utf-8"),
    ],
)


def _normalize_sid(sid: str) -> str:
    """统一 service_id 为小写 0xNN 格式。"""
    sid = sid.strip().lower()
    if not sid.startswith("0x"):
        sid = "0x" + sid
    return sid


# ── HTML 前端页面 ──────────────────────────────────────────────

FRONTEND_HTML = r"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>UDS 测试用例生成</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, "Segoe UI", Roboto, sans-serif; background: #f0f2f5; padding: 24px; }
  .container { max-width: 1200px; margin: 0 auto; }
  h1 { text-align: center; margin-bottom: 24px; color: #1a1a1a; }
  .card { background: #fff; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,.1); padding: 24px; margin-bottom: 16px; }
  .card h2 { font-size: 16px; margin-bottom: 12px; color: #333; }
  label { display: block; margin-bottom: 6px; font-weight: 500; color: #555; }
  input[type="file"] { width: 100%; padding: 8px; border: 1px solid #d9d9d9; border-radius: 4px; }
  .checkbox-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 6px; margin-top: 8px; }
  .checkbox-grid label { display: flex; align-items: center; gap: 6px; font-weight: 400; cursor: pointer; padding: 4px 0; }
  .checkbox-grid input { width: 16px; height: 16px; }
  .actions { display: flex; gap: 12px; margin-top: 16px; flex-wrap: wrap; }
  button { padding: 10px 28px; border: none; border-radius: 6px; font-size: 15px; cursor: pointer; font-weight: 500; }
  .btn-primary { background: #1677ff; color: #fff; }
  .btn-primary:hover { background: #4096ff; }
  .btn-primary:disabled { background: #95b8fc; cursor: not-allowed; }
  .btn-export { background: #52c41a; color: #fff; }
  .btn-export:hover { background: #73d13d; }
  .btn-export:disabled { background: #b7eb8f; cursor: not-allowed; }
  #status { margin-top: 12px; padding: 10px; border-radius: 4px; display: none; }
  .status-loading { background: #fff7e6; color: #d46b08; border: 1px solid #ffd591; }
  .status-ok { background: #f6ffed; color: #389e0d; border: 1px solid #b7eb8f; }
  .status-err { background: #fff2f0; color: #cf1322; border: 1px solid #ffccc7; }
  .progress-bar { width: 100%; height: 6px; background: #e8e8e8; border-radius: 3px; margin-top: 8px; display: none; }
  .progress-bar-fill { height: 100%; background: #1677ff; border-radius: 3px; transition: width .3s; width: 0; }
  #result-area { display: none; margin-top: 16px; }
  #result-area h3 { margin-bottom: 8px; }
  table { width: 100%; border-collapse: collapse; font-size: 13px; margin-top: 8px; }
  th, td { border: 1px solid #e8e8e8; padding: 6px 8px; text-align: left; vertical-align: top; }
  th { background: #fafafa; font-weight: 500; white-space: nowrap; }
  .section-row td { background: #e6f4ff; font-weight: 600; }
  .json-box { background: #f5f5f5; border: 1px solid #d9d9d9; border-radius: 4px; padding: 12px;
              max-height: 300px; overflow: auto; font-family: monospace; font-size: 12px; white-space: pre-wrap;
              margin-top: 12px; }
  .summary { font-size: 14px; color: #555; }
  .svc-result { margin-top: 8px; padding: 8px 12px; border-radius: 4px; border-left: 4px solid; }
  .svc-ok { border-color: #52c41a; background: #f6ffed; }
  .svc-err { border-color: #ff4d4f; background: #fff2f0; }
  .svc-loading { border-color: #faad14; background: #fffbe6; }
  #liveLog { font-size: 13px; line-height: 1.8; }
  .diag-panel { border: 1px solid #d9d9d9; border-radius: 6px; margin-bottom: 10px; overflow: hidden; }
  .diag-header { background: #fafafa; padding: 10px 16px; cursor: pointer; display: flex; justify-content: space-between; align-items: center; font-weight: 500; font-size: 14px; }
  .diag-header:hover { background: #f0f0f0; }
  .diag-body { display: none; padding: 16px; font-size: 13px; border-top: 1px solid #e8e8e8; }
  .diag-body.open { display: block; }
  .diag-section { margin-bottom: 14px; }
  .diag-section h4 { font-size: 13px; color: #1677ff; margin-bottom: 6px; }
  .diag-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 4px; }
  .diag-kv { display: flex; gap: 6px; }
  .diag-kv .dk-label { color: #888; min-width: 100px; }
  .diag-kv .dk-value { font-weight: 500; }
  .diag-arrow { transition: transform .2s; display: inline-block; }
  .diag-arrow.open { transform: rotate(90deg); }
</style>
</head>
<body>
<div class="container">
  <h1>UDS 诊断测试用例自动生成</h1>

  <div class="card">
    <h2>1. 上传 ECU 参数文件</h2>
    <input type="file" id="fileInput" accept=".xlsx,.xls">
  </div>

  <div class="card">
    <h2>2. 选择服务</h2>
    <div class="checkbox-grid" id="serviceCheckboxes">
      <label><input type="checkbox" id="selectAll"> 全选</label>
    </div>
  </div>

  <div class="card">
    <div class="actions">
      <button class="btn-primary" id="btnGenerate" disabled onclick="doStream()">生成测试用例（实时）</button>
      <button class="btn-export" id="btnExport" disabled onclick="doExport()">生成并导出 Excel</button>
    </div>
    <div class="progress-bar" id="progressBar"><div class="progress-bar-fill" id="progressFill"></div></div>
    <div id="status"></div>
    <div id="liveLog"></div>
  </div>

  <div id="result-area">
    <div class="card" id="summaryCard"></div>
    <div class="card">
      <h3>测试用例详情</h3>
      <div id="caseTabs"></div>
      <div id="caseTable"></div>
    </div>
    <div class="card">
      <h3>原始 JSON</h3>
      <div class="json-box" id="jsonOutput"></div>
    </div>
  </div>
</div>

<script>
let lastResult = null;

async function loadServices() {
  try {
    const resp = await fetch('/api/services');
    const data = await resp.json();
    const grid = document.getElementById('serviceCheckboxes');
    data.services.forEach(s => {
      const lbl = document.createElement('label');
      lbl.innerHTML = `<input type="checkbox" class="svc-cb" value="${s.service_id}"> ${s.service_id} ${s.service_name}`;
      grid.appendChild(lbl);
    });
  } catch(e) {
    console.error('加载服务列表失败', e);
  }
  document.getElementById('selectAll').addEventListener('change', e => {
    document.querySelectorAll('.svc-cb').forEach(cb => cb.checked = e.target.checked);
  });
}

document.getElementById('fileInput').addEventListener('change', e => {
  const hasFile = e.target.files.length > 0;
  document.getElementById('btnGenerate').disabled = !hasFile;
  document.getElementById('btnExport').disabled = !hasFile;
});

function setStatus(msg, cls) {
  const s = document.getElementById('status');
  s.className = cls; s.style.display = 'block'; s.textContent = msg;
}

function setButtons(disabled) {
  document.getElementById('btnGenerate').disabled = disabled;
  document.getElementById('btnExport').disabled = disabled;
}

// ── SSE 流式生成 ──
async function doStream() {
  const file = document.getElementById('fileInput').files[0];
  if (!file) return alert('请先上传文件');
  const checked = [...document.querySelectorAll('.svc-cb:checked')].map(cb => cb.value);
  if (!checked.length) return alert('请至少选择一个服务');

  // Reset UI
  document.getElementById('liveLog').innerHTML = '';
  document.getElementById('result-area').style.display = 'none';
  document.getElementById('summaryCard').innerHTML = '';
  document.getElementById('caseTabs').innerHTML = '';
  document.getElementById('caseTable').innerHTML = '';
  document.getElementById('jsonOutput').textContent = '';
  lastResult = { ecu_info: {}, services: [], meta: { total_services: checked.length, success_count: 0, error_count: 0, errors: [], total_elapsed_seconds: 0 } };

  setButtons(true);
  setStatus(`正在生成 ${checked.length} 个服务的测试用例...`, 'status-loading');
  const pb = document.getElementById('progressBar'); pb.style.display = 'block';
  document.getElementById('progressFill').style.width = '0%';

  const fd = new FormData();
  fd.append('file', file);
  fd.append('services', checked.join(','));

  try {
    const resp = await fetch('/api/generate/stream', { method: 'POST', body: fd });
    if (!resp.ok) {
      let detail = '生成失败';
      try { const j = await resp.json(); detail = j.detail || detail; } catch(e) {}
      throw new Error(detail);
    }

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      // Parse SSE events
      const lines = buffer.split('\n');
      buffer = lines.pop(); // keep incomplete line

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        const payload = line.slice(6);
        if (payload === '[DONE]') continue;

        try {
          const evt = JSON.parse(payload);
          handleSSE(evt, checked.length);
        } catch(e) {
          console.warn('SSE parse error', e, payload);
        }
      }
    }

    // Final
    setStatus(`生成完成！成功 ${lastResult.meta.success_count}/${checked.length} 个服务，耗时 ${lastResult.meta.total_elapsed_seconds}s`, 'status-ok');
    showResult(lastResult);
  } catch(e) {
    setStatus('错误: ' + e.message, 'status-err');
  } finally {
    setButtons(false);
    pb.style.display = 'none';
  }
}

function handleSSE(evt, total) {
  const log = document.getElementById('liveLog');
  if (evt.type === 'progress') {
    const pct = Math.round((evt.index / total) * 100);
    document.getElementById('progressFill').style.width = pct + '%';
    log.innerHTML += `<div class="svc-result svc-loading">[${evt.index}/${total}] 正在生成 ${evt.service_id}...</div>`;
  } else if (evt.type === 'service_done') {
    lastResult.services.push(evt.data);
    lastResult.meta.success_count++;
    lastResult.meta.total_elapsed_seconds = evt.elapsed_seconds;
    // Update last progress item
    const items = log.querySelectorAll('.svc-loading');
    const last = items[items.length - 1];
    if (last) {
      last.className = 'svc-result svc-ok';
      last.textContent = `[${lastResult.meta.success_count + lastResult.meta.error_count}/${total}] ${evt.data.service_id} 完成 - ${evt.data.total_count} 条用例 (${evt.data.meta.elapsed_seconds}s)`;
    }
  } else if (evt.type === 'service_error') {
    lastResult.meta.error_count++;
    lastResult.meta.errors.push(evt);
    const items = log.querySelectorAll('.svc-loading');
    const last = items[items.length - 1];
    if (last) {
      last.className = 'svc-result svc-err';
      last.textContent = `[${lastResult.meta.success_count + lastResult.meta.error_count}/${total}] ${evt.service_id} 失败 - ${evt.error}`;
    }
  } else if (evt.type === 'done') {
    lastResult.meta.total_elapsed_seconds = evt.elapsed_seconds;
  }
  log.scrollTop = log.scrollHeight;
}

// ── Export（先流式生成再导出）──
async function doExport() {
  const file = document.getElementById('fileInput').files[0];
  if (!file) return alert('请先上传文件');
  const checked = [...document.querySelectorAll('.svc-cb:checked')].map(cb => cb.value);
  if (!checked.length) return alert('请至少选择一个服务');

  document.getElementById('liveLog').innerHTML = '';
  setButtons(true);
  setStatus(`正在生成并导出 ${checked.length} 个服务...`, 'status-loading');
  const pb = document.getElementById('progressBar'); pb.style.display = 'block';
  document.getElementById('progressFill').style.width = '0%';
  const log = document.getElementById('liveLog');

  const fd = new FormData();
  fd.append('file', file);
  fd.append('services', checked.join(','));

  try {
    // Use SSE stream to collect data, then export
    const resp = await fetch('/api/generate/stream', { method: 'POST', body: fd });
    if (!resp.ok) throw new Error('生成失败');

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    const collected = [];
    let totalElapsed = 0;

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop();
      let doneCount = 0;
      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        const payload = line.slice(6);
        if (payload === '[DONE]') continue;
        try {
          const evt = JSON.parse(payload);
          if (evt.type === 'progress') {
            log.innerHTML += `<div class="svc-result svc-loading">[${evt.index}/${checked.length}] ${evt.service_id}...</div>`;
            document.getElementById('progressFill').style.width = Math.round((evt.index / checked.length) * 100) + '%';
          } else if (evt.type === 'service_done') {
            collected.push(evt.data);
            doneCount++;
            const items = log.querySelectorAll('.svc-loading');
            if (items.length) { const l = items[items.length-1]; l.className='svc-result svc-ok'; l.textContent=`${evt.data.service_id} - ${evt.data.total_count} 条`; }
          } else if (evt.type === 'service_error') {
            doneCount++;
            const items = log.querySelectorAll('.svc-loading');
            if (items.length) { const l = items[items.length-1]; l.className='svc-result svc-err'; l.textContent=`${evt.service_id} 失败`; }
          } else if (evt.type === 'done') {
            totalElapsed = evt.elapsed_seconds;
          }
        } catch(e) {}
      }
      log.scrollTop = log.scrollHeight;
    }

    if (!collected.length) throw new Error('未生成任何测试用例');

    // Request Excel export
    document.getElementById('progressFill').style.width = '100%';
    log.innerHTML += `<div class="svc-result svc-loading">正在导出 Excel...</div>`;

    const exportFd = new FormData();
    exportFd.append('file', file);
    exportFd.append('services', checked.join(','));
    // Use direct export with collected data via new endpoint
    const exportResp = await fetch('/api/export/json', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ services: collected }),
    });
    if (!exportResp.ok) throw new Error('Excel 导出失败');
    const blob = await exportResp.blob();
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'UDS_TestCases.xlsx';
    a.click();
    URL.revokeObjectURL(a.href);
    setStatus(`导出成功！${collected.length} 个服务，耗时 ${totalElapsed}s`, 'status-ok');

    // Show results
    lastResult = { ecu_info: {}, services: collected, meta: { success_count: collected.length, total_elapsed_seconds: totalElapsed } };
    showResult(lastResult);
  } catch(e) {
    setStatus('错误: ' + e.message, 'status-err');
  } finally {
    setButtons(false);
    pb.style.display = 'none';
  }
}

function showResult(data) {
  document.getElementById('result-area').style.display = 'block';
  const summary = document.getElementById('summaryCard');
  summary.innerHTML = '<h3>生成结果概览</h3>' +
    data.services.map(s => {
      return `<p class="summary">${s.sheet_name}: <b>${s.total_count}</b> 条用例 (${s.meta.elapsed_seconds}s)</p>`;
    }).join('');

  const tabs = document.getElementById('caseTabs');
  tabs.innerHTML = data.services.map((s, i) =>
    `<button onclick="showTab(${i})" style="padding:6px 16px;margin:4px;border:${i===0?'2px solid #1677ff':'1px solid #d9d9d9'};border-radius:4px;cursor:pointer;background:${i===0?'#e6f4ff':'#fff'}">${s.service_id} (${s.total_count})</button>`
  ).join('');
  showTab(0);
  document.getElementById('jsonOutput').textContent = JSON.stringify(data, null, 2);
}

function showTab(idx) {
  const svc = lastResult.services[idx];
  const tabs = document.getElementById('caseTabs').querySelectorAll('button');
  tabs.forEach((b, i) => { b.style.border = i===idx?'2px solid #1677ff':'1px solid #d9d9d9'; b.style.background = i===idx?'#e6f4ff':'#fff'; });
  const tableDiv = document.getElementById('caseTable');
  if (!svc || !svc.test_cases || !svc.test_cases.length) { tableDiv.innerHTML = '<p>无测试用例</p>'; return; }
  let html = '<table><tr><th>#</th><th>Case ID</th><th>Case Name</th><th>Priority</th><th>Test Procedure</th><th>Expected Output</th></tr>';
  let curSection = '', curSub = '';
  svc.test_cases.forEach(tc => {
    if (tc.section !== curSection) { curSection = tc.section; html += `<tr class="section-row"><td colspan="6">${curSection}</td></tr>`; }
    if (tc.subsection !== curSub) { curSub = tc.subsection; html += `<tr class="section-row"><td colspan="6">${curSub}</td></tr>`; }
    const proc = (tc.test_procedure || '').replace(/\n/g, '<br>');
    const exp = (tc.expected_output || '').replace(/\n/g, '<br>');
    html += `<tr><td>${tc.sequence_number}</td><td>${tc.case_id}</td><td>${tc.case_name}</td><td>${tc.priority}</td><td>${proc}</td><td>${exp}</td></tr>`;
  });
  html += '</table>';
  tableDiv.innerHTML = html;
}

loadServices();
</script>
</body>
</html>
"""


app = FastAPI(
    title="UDS Assistant API",
    version="0.1.0",
    description="UDS 诊断测试用例自动生成接口",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_pipeline: UDSGeneratePipeline | None = None


def get_pipeline() -> UDSGeneratePipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = UDSGeneratePipeline()
    return _pipeline


@app.get("/", response_class=HTMLResponse)
async def index():
    return FRONTEND_HTML


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}


@app.get("/api/services")
async def list_services():
    """返回支持的服务列表。"""
    cfg = load_config()
    prompts_map: dict = cfg.get("service_prompts", {})

    services = []
    seen = set()
    for sid, prompt_file in prompts_map.items():
        name = SERVICE_NAMES.get(sid, f"Service{sid}")
        key = f"{name}_{sid}"
        if key not in seen:
            seen.add(key)
            services.append({
                "service_id": sid,
                "service_name": name,
                "prompt_file": prompt_file,
            })

    return {"services": services, "total": len(services)}


@app.post("/api/generate")
async def generate_test_cases(
    file: UploadFile = File(...),
    services: str = Form(...),
    domain: str = Form("App"),
):
    """上传 Excel + 选择服务 → 返回测试用例 JSON。"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="未提供文件名")

    ext = Path(file.filename).suffix.lower()
    if ext not in (".xlsx", ".xls"):
        raise HTTPException(status_code=400, detail=f"不支持的文件格式: {ext}")

    service_ids = [s.strip() for s in services.split(",") if s.strip()]
    if not service_ids:
        raise HTTPException(status_code=400, detail="未指定服务 ID")

    cfg = load_config()
    available = set(k.lower() for k in cfg.get("service_prompts", {}).keys())
    for sid in service_ids:
        if _normalize_sid(sid) not in available:
            raise HTTPException(status_code=400, detail=f"不支持的服务: {sid}")

    start = time.time()
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        pipeline = get_pipeline()
        results = []
        errors = []
        ecu_info = {}

        for sid in service_ids:
            normalized = _normalize_sid(sid)
            try:
                result = pipeline.generate(excel_path=tmp_path, service_id=normalized, domain=domain, original_filename=file.filename or "")
                results.append(result)
                if not ecu_info and result.test_cases:
                    ecu_info = {"provider": result.meta.get("provider", ""), "model": result.meta.get("model", "")}
            except Exception as e:
                logger.error(f"服务 {normalized} 生成失败: {e}")
                errors.append({"service_id": normalized, "error": str(e)})

        elapsed = time.time() - start
        return {
            "ecu_info": ecu_info,
            "services": [r.model_dump() for r in results],
            "meta": {
                "total_services": len(service_ids),
                "success_count": len(results),
                "error_count": len(errors),
                "errors": errors,
                "total_elapsed_seconds": round(elapsed, 2),
            },
        }
    finally:
        os.unlink(tmp_path)


@app.post("/api/generate/stream")
async def generate_stream(
    file: UploadFile = File(...),
    services: str = Form(...),
    domain: str = Form("App"),
):
    """SSE 流式生成：每完成一个服务推送一条事件。"""

    if not file.filename:
        raise HTTPException(status_code=400, detail="未提供文件名")
    ext = Path(file.filename).suffix.lower()
    if ext not in (".xlsx", ".xls"):
        raise HTTPException(status_code=400, detail=f"不支持的文件格式: {ext}")

    service_ids = [_normalize_sid(s) for s in services.split(",") if s.strip()]
    if not service_ids:
        raise HTTPException(status_code=400, detail="未指定服务 ID")

    cfg = load_config()
    available = set(k.lower() for k in cfg.get("service_prompts", {}).keys())
    for sid in service_ids:
        if sid not in available:
            raise HTTPException(status_code=400, detail=f"不支持的服务: {sid}")

    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    async def event_generator():
        pipeline = get_pipeline()
        start = time.time()

        for i, sid in enumerate(service_ids, 1):
            # 发送 progress 事件
            yield f"data: {json.dumps({'type': 'progress', 'index': i, 'total': len(service_ids), 'service_id': sid}, ensure_ascii=False)}\n\n"

            try:
                result = pipeline.generate(excel_path=tmp_path, service_id=sid, domain=domain, original_filename=file.filename or "")
                yield f"data: {json.dumps({'type': 'service_done', 'data': result.model_dump(), 'elapsed_seconds': round(time.time() - start, 2)}, ensure_ascii=False)}\n\n"
            except Exception as e:
                logger.error(f"SSE: 服务 {sid} 失败: {e}")
                yield f"data: {json.dumps({'type': 'service_error', 'service_id': sid, 'error': str(e)}, ensure_ascii=False)}\n\n"

        elapsed = time.time() - start
        yield f"data: {json.dumps({'type': 'done', 'elapsed_seconds': round(elapsed, 2)}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

        os.unlink(tmp_path)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/export")
async def export_excel(
    file: UploadFile = File(...),
    services: str = Form(...),
    domain: str = Form("App"),
):
    """上传 Excel + 选择服务 → 下载生成的测试用例 Excel。"""
    gen_resp = await generate_test_cases(file=file, services=services, domain=domain)
    if not gen_resp.get("services"):
        raise HTTPException(status_code=500, detail="未生成任何测试用例")
    try:
        xlsx_bytes = export_to_excel(gen_resp["services"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Excel 导出失败: {e}")
    return StreamingResponse(
        io.BytesIO(xlsx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=UDS_TestCases.xlsx"},
    )


@app.post("/api/export/json")
async def export_from_json(body: dict):
    """从 JSON 数据直接导出 Excel（前端流式收集后调用）。"""
    services_data = body.get("services", [])
    if not services_data:
        raise HTTPException(status_code=400, detail="无服务数据")
    try:
        xlsx_bytes = export_to_excel(services_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Excel 导出失败: {e}")
    return StreamingResponse(
        io.BytesIO(xlsx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=UDS_TestCases.xlsx"},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
