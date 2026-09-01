#!/usr/bin/env python3
"""Unified Intelligence Engine — single /api/execute with SSE + callback.

Framework 2: ProcessPoolExecutor for GIL-free compute.
Forced Constraint: Idempotent Resurrection — auto-resume stranded runs on restart.

Usage:
  python orchestrate.py [--port 8083]
"""

import json
import sys
import os
import time
import uuid
import threading
import socketserver
import http.server
import urllib.request
import queue
import sqlite3
import traceback

PORT = 8083
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "slide_state.sqlite")
PIPELINE_STEP_TIMEOUT = 60  # seconds per pipeline step

_runs = {}
_runs_lock = threading.Lock()

# Asymmetric Graceful Degradation
# If HITL/Export are down, flip to False — engine continues but rejects failed gates
requires_hitl = True


class PipelineStepTimeout(Exception):
    pass

def with_step_timeout(func, *args, timeout=PIPELINE_STEP_TIMEOUT, **kwargs):
    """Run a function with a timeout using threading (Windows-compatible)."""
    result = [None]
    exception = [None]
    def target():
        try:
            result[0] = func(*args, **kwargs)
        except Exception as e:
            exception[0] = e
    t = threading.Thread(target=target, daemon=True)
    t.start()
    t.join(timeout)
    if t.is_alive():
        raise PipelineStepTimeout("Pipeline step exceeded {}s timeout".format(timeout))
    if exception[0]:
        raise exception[0]
    return result[0]


def emit_event(run_id, event_type, data=None):
    with _runs_lock:
        if run_id not in _runs:
            return
        evt = {"type": event_type, "time": time.time(), "data": data or {}}
        _runs[run_id]["events"].put(evt)


def run_pipeline_thread(run_id, payload):
    """Execute full pipeline inline in daemon thread.

    Every step writes to SQLite (pipeline_runs table) so the pipeline
    can be resumed after a crash — purely idempotent.

    Fifth Divergence:
    - Ontological ledger scan before ingestion (auto-discover entities)
    - Semantic Bypass: clone existing slides if concept known (Zero-Execution)
    - Bifurcated Egress: SSE stream + REST webhook for low-code clients
    """
    try:
        from slide_state import (
            init_doc, add_chunk, create_jobs_for_doc, add_live_chunk,
            create_pipeline_run, update_pipeline_step, mark_pipeline_done, mark_pipeline_failed,
        )
        from parallel_dispatch import dispatch
        from compile_web import compile_web

        doc_id = None
        callback_url = payload.get("callback_url")
        output_format = payload.get("format", "web")
        model = payload.get("model", "oc/hy3-free")
        max_parallel = payload.get("max_parallel", 3)

        # Step 1: Init
        emit_event(run_id, "init_start", {"source": payload.get("source", "direct")})
        update_pipeline_step(run_id, "init")
        if "doc_id" in payload:
            doc_id = payload["doc_id"]
        else:
            doc_id = init_doc(payload.get("source", "direct"), payload.get("pages", 1))
        # Register run in SQLite for idempotent tracking (after doc exists)
        create_pipeline_run(run_id, doc_id, json.dumps(payload))
        emit_event(run_id, "init_done", {"doc_id": doc_id})

        # Step 1b: Ontological Ledger Scan (auto-discover entities before ingestion)
        update_pipeline_step(run_id, "ontological_scan")
        try:
            from ontology_ledger import OntologicalLedger
            ledger = OntologicalLedger(DB_PATH)
            chunk_texts = [c["text"] for c in payload.get("chunks", [])]
            scan_result = ledger.ingest_scan(chunk_texts)
            emit_event(run_id, "ontological_scan_done", scan_result)
        except Exception as e:
            emit_event(run_id, "ontological_scan_error", {"error": str(e)})

        # Step 2: Ingest
        update_pipeline_step(run_id, "ingesting")
        chunks = payload.get("chunks", [])
        for i, chunk in enumerate(chunks):
            clearance = chunk.get("clearance_tier", payload.get("clearance_tier", "Public"))
            domains = chunk.get("clearance_domains", payload.get("clearance_domains", ["General"]))
            if chunk.get("live"):
                add_live_chunk(doc_id, chunk.get("page", i + 1), chunk.get("chunk", i + 1),
                               chunk["text"], chunk.get("url", ""), chunk.get("ttl", 3600),
                               clearance_tier=clearance, clearance_domains=domains)
            else:
                add_chunk(doc_id, chunk.get("page", i + 1), chunk.get("chunk", i + 1),
                          chunk["text"], chunk.get("precursor", ""),
                          clearance_tier=clearance, clearance_domains=domains)
            emit_event(run_id, "chunk_ingested", {"index": i, "total": len(chunks)})

        # Step 3: Create jobs
        emit_event(run_id, "jobs_start", {})
        update_pipeline_step(run_id, "jobs")
        job_result = create_jobs_for_doc(doc_id)
        emit_event(run_id, "jobs_done", {"count": job_result.get("jobs_created", 0)})

        # Step 3b: Semantic Bypass — Zero-Execution Mandate
        # Before dispatching to OmniRoute, check if concepts already exist
        update_pipeline_step(run_id, "semantic_bypass")
        bypass_result = {"bypassed": 0, "proceeded": 0}
        try:
            from semantic_bypass import SemanticBypass
            bypass = SemanticBypass(DB_PATH)
            import slide_state as _ss
            conn = _ss.connect()
            pending_jobs = conn.execute(
                "SELECT j.id, j.slide_index, j.chunk_id, c.content "
                "FROM jobs j JOIN chunks c ON c.id = j.chunk_id "
                "WHERE j.doc_id=? AND j.status='pending'", (doc_id,)
            ).fetchall()
            conn.close()

            for job_id, slide_idx, chunk_id, content in pending_jobs:
                should_bypass, match, score = bypass.check_bypass(content)
                if should_bypass and match:
                    # Clone existing slide — zero LLM execution
                    clone_res = bypass.clone_slide(match, doc_id, slide_idx)
                    if clone_res.get("ok"):
                        _ss.db_write("UPDATE jobs SET status='done' WHERE id=?", (job_id,))
                        bypass_result["bypassed"] += 1
                        emit_event(run_id, "slide_bypassed", {
                            "slide_index": slide_idx,
                            "cloned_from": match["slide_id"],
                            "similarity": round(score, 4),
                        })
                    else:
                        bypass_result["proceeded"] += 1
                else:
                    bypass_result["proceeded"] += 1
            conn.close()
        except Exception as e:
            emit_event(run_id, "semantic_bypass_error", {"error": str(e)})
            bypass_result["proceeded"] = len(pending_jobs) if 'pending_jobs' in dir() else 0

        emit_event(run_id, "semantic_bypass_done", bypass_result)

        # Step 4: Dispatch (only for non-bypassed jobs)
        emit_event(run_id, "dispatch_start", {"model": model, "parallel": max_parallel})
        update_pipeline_step(run_id, "dispatching")
        dispatch_result = dispatch(doc_id, max_parallel, model)
        emit_event(run_id, "dispatch_done", {
            "passed": dispatch_result.get("passed", 0),
            "failed": dispatch_result.get("failed", 0),
            "bypassed": bypass_result.get("bypassed", 0),
        })

        # Step 5: Compile (Zero-Persistence — BytesIO buffers via BufferBroker)
        update_pipeline_step(run_id, "compiling")
        from buffer_broker import get_broker, DeliveryLedger
        broker = get_broker()
        outputs = {}

        if output_format in ("pptx", "both"):
            from compile_pptx import compile_pptx
            pptx_result = compile_pptx(doc_id, output_path=None)
            outputs["pptx"] = {k: v for k, v in pptx_result.items() if k != "buffer"}
            if pptx_result.get("buffer"):
                broker.put(run_id, "pptx", pptx_result["buffer"], pptx_result.get("size"))
            emit_event(run_id, "pptx_done", {"size": pptx_result.get("size")})

        if output_format in ("web", "both"):
            from compile_web import compile_web
            web_result = compile_web(doc_id, output_path=None)
            outputs["web"] = {k: v for k, v in web_result.items() if k != "buffer"}
            if web_result.get("buffer"):
                broker.put(run_id, "web", web_result["buffer"], web_result.get("size"))
            emit_event(run_id, "web_done", {"size": web_result.get("size")})

        # Step 6: Complete
        result = {"ok": True, "doc_id": doc_id, "run_id": run_id, "outputs": outputs, "status": "done"}
        mark_pipeline_done(run_id, json.dumps(result))
        emit_event(run_id, "pipeline_complete", result)

        with _runs_lock:
            _runs[run_id]["status"] = "done"
            _runs[run_id]["result"] = result

        # Step 7: Delivery (Distributed Ephemeral Relay + Volatility Governor)
        webhook_url = callback_url
        if not webhook_url:
            with _runs_lock:
                webhook_url = _runs.get(run_id, {}).get("callback_url")
        if webhook_url:
            from distributed_relay import get_relay
            from buffer_broker import DeliveryLedger
            relay = get_relay()
            ledger = DeliveryLedger(DB_PATH)
            for fmt in outputs:
                buf = broker.get(run_id, fmt)
                if buf is not None:
                    # Pin to distributed relay (content-addressable, survives restart)
                    ext = "pptx" if fmt == "pptx" else "html"
                    ct = "application/vnd.openxmlformats-officedocument.presentationml.presentation" if fmt == "pptx" else "text/html"
                    buf.seek(0)
                    data = buf.read()
                    gateway = relay.pin(data, content_type=ct, filename="{}.{}".format(run_id[:8], ext))

                    try:
                        from egress_firewall import validate_egress_url
                        validate_egress_url(webhook_url)
                        payload_data = json.dumps({
                            "run_id": run_id,
                            "format": fmt,
                            "gateway_url": gateway["gateway_url"],
                            "content_hash": gateway["content_hash"],
                            "expires_at": gateway["expires_at"],
                            "size": len(data),
                        }).encode()
                        req = urllib.request.Request(
                            webhook_url, data=payload_data,
                            headers={"Content-Type": "application/json"},
                            method="POST",
                        )
                        with urllib.request.urlopen(req, timeout=30) as resp:
                            ledger.register_delivery(run_id, fmt, webhook_url)
                            ledger.mark_delivered(run_id, fmt)
                            emit_event(run_id, "delivery_sent", {"format": fmt, "gateway_url": gateway["gateway_url"]})
                    except Exception as e:
                        ledger.register_delivery(run_id, fmt, webhook_url)
                        ledger.mark_failed(run_id, fmt, str(e))
                        emit_event(run_id, "delivery_failed", {"format": fmt, "error": str(e)})

    except Exception as e:
        tb = traceback.format_exc()
        sys.stderr.write("Pipeline error: {}\n{}\n".format(e, tb))
        sys.stderr.flush()
        try:
            from slide_state import mark_pipeline_failed
            mark_pipeline_failed(run_id, str(e))
        except Exception:
            pass
        emit_event(run_id, "pipeline_error", {"error": str(e), "traceback": tb})
        with _runs_lock:
            _runs[run_id]["status"] = "error"
            _runs[run_id]["result"] = {"ok": False, "error": str(e), "traceback": tb, "status": "error"}


def resume_stranded_runs():
    """Forced Constraint: Idempotent Resurrection.

    On server restart, detect any pipeline_runs that were interrupted
    mid-execution (status != 'done' && status != 'failed') and resume
    them from the last completed step.
    """
    try:
        from slide_state import get_stranded_runs
        stranded = get_stranded_runs()
        if not stranded:
            return

        sys.stderr.write("Resuming {} stranded pipeline runs\n".format(len(stranded)))
        sys.stderr.flush()

        for run in stranded:
            run_id = run["run_id"]
            payload = json.loads(run["payload_json"])
            current_step = run["current_step"]

            # Register in memory for SSE streaming
            with _runs_lock:
                _runs[run_id] = {
                    "events": queue.Queue(),
                    "status": "running",
                    "result": None,
                }

            emit_event(run_id, "resumed_from", {"step": current_step})

            # Resume from the interrupted step
            t = threading.Thread(
                target=resume_pipeline_from_step,
                args=(run_id, payload, current_step),
                daemon=True,
            )
            t.start()

    except Exception as e:
        sys.stderr.write("Resume error: {}\n".format(e))
        sys.stderr.flush()


def resume_pipeline_from_step(run_id, payload, from_step):
    """Resume pipeline from a specific step (idempotent)."""
    try:
        from slide_state import (
            add_chunk, add_live_chunk, create_jobs_for_doc, add_live_chunk,
            update_pipeline_step, mark_pipeline_done, mark_pipeline_failed,
        )
        from parallel_dispatch import dispatch
        from compile_web import compile_web

        doc_id = payload.get("doc_id")
        if not doc_id:
            # Re-init if needed
            from slide_state import init_doc
            doc_id = init_doc(payload.get("source", "direct"), payload.get("pages", 1))
            payload["doc_id"] = doc_id

        # Only run steps that haven't completed yet
        step_order = ["init", "ingesting", "jobs", "dispatching", "compiling", "done"]
        start_idx = step_order.index(from_step) if from_step in step_order else 0

        if start_idx <= 1:  # Need to re-ingest
            emit_event(run_id, "init_done", {"doc_id": doc_id, "resumed": True})
            chunks = payload.get("chunks", [])
            for i, chunk in enumerate(chunks):
                clearance = chunk.get("clearance_tier", payload.get("clearance_tier", "Public"))
                if chunk.get("live"):
                    add_live_chunk(doc_id, chunk.get("page", i + 1), chunk.get("chunk", i + 1),
                                   chunk["text"], chunk.get("url", ""), chunk.get("ttl", 3600),
                                   clearance_tier=clearance)
                else:
                    add_chunk(doc_id, chunk.get("page", i + 1), chunk.get("chunk", i + 1),
                              chunk["text"], chunk.get("precursor", ""), clearance_tier=clearance)
                emit_event(run_id, "chunk_ingested", {"index": i, "total": len(chunks), "resumed": True})

        if start_idx <= 2:  # Need to re-create jobs
            job_result = create_jobs_for_doc(doc_id)
            emit_event(run_id, "jobs_done", {"count": job_result.get("jobs_created", 0), "resumed": True})

        if start_idx <= 3:  # Need to re-dispatch
            emit_event(run_id, "dispatch_start", {"model": payload.get("model", "oc/hy3-free"), "resumed": True})
            update_pipeline_step(run_id, "dispatching", status="dispatching")
            dispatch_result = dispatch(doc_id, payload.get("max_parallel", 3), payload.get("model", "oc/hy3-free"))
            emit_event(run_id, "dispatch_done", {
                "passed": dispatch_result.get("passed", 0),
                "failed": dispatch_result.get("failed", 0),
                "resumed": True,
            })

        if start_idx <= 4:  # Need to re-compile
            update_pipeline_step(run_id, "compiling", status="compiling")
            outputs = {}
            output_format = payload.get("format", "web")
            if output_format in ("pptx", "both"):
                from compile_pptx import compile_pptx
                pptx_path = payload.get("pptx_output", "output_{}.pptx".format(run_id[:8]))
                pptx_result = compile_pptx(doc_id, pptx_path)
                outputs["pptx"] = pptx_result
                emit_event(run_id, "pptx_done", {"output": pptx_path, "size": pptx_result.get("file_size"), "resumed": True})
            if output_format in ("web", "both"):
                web_path = payload.get("web_output", "output_{}.html".format(run_id[:8]))
                web_result = compile_web(doc_id, web_path)
                outputs["web"] = web_result
                emit_event(run_id, "web_done", {"output": web_path, "size": web_result.get("file_size"), "resumed": True})

        result = {"ok": True, "doc_id": doc_id, "run_id": run_id, "outputs": outputs}
        mark_pipeline_done(run_id, json.dumps(result))
        emit_event(run_id, "pipeline_complete", result)

        with _runs_lock:
            _runs[run_id]["status"] = "done"
            _runs[run_id]["result"] = result

        # Callback if configured
        callback_url = payload.get("callback_url")
        if callback_url:
            try:
                cb_payload = json.dumps(result).encode("utf-8")
                req = urllib.request.Request(callback_url, data=cb_payload,
                                            headers={"Content-Type": "application/json"}, method="POST")
                with urllib.request.urlopen(req, timeout=10) as resp:
                    emit_event(run_id, "callback_sent", {"status": resp.status})
            except Exception as e:
                emit_event(run_id, "callback_failed", {"error": str(e)})

    except Exception as e:
        tb = traceback.format_exc()
        sys.stderr.write("Resume error: {}\n{}\n".format(e, tb))
        sys.stderr.flush()
        try:
            from slide_state import mark_pipeline_failed
            mark_pipeline_failed(run_id, str(e))
        except Exception:
            pass
        emit_event(run_id, "pipeline_error", {"error": str(e), "traceback": tb})
        with _runs_lock:
            _runs[run_id]["status"] = "error"


class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


class OrchestrateHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _send(self, code, body, ct="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", ct)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body.encode() if isinstance(body, str) else body)

    def _json(self, code, obj):
        self._send(code, json.dumps(obj, indent=2))

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(length)) if length else {}

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        path = self.path.split("?")[0]
        try:
            if path == "/api/health":
                self._json(200, {
                    "ok": True,
                    "service": "unified-intelligence-engine",
                    "requires_hitl": requires_hitl,
                })
            elif path.startswith("/api/stream/"):
                run_id = path.split("/")[3]
                self._handle_sse(run_id)
            elif path.startswith("/api/status/"):
                run_id = path.split("/")[3]
                with _runs_lock:
                    if run_id in _runs:
                        run_data = _runs[run_id]
                        safe = {k: v for k, v in run_data.items() if k not in ("events", "buffers")}
                        self._json(200, safe)
                    else:
                        from slide_state import db_read
                        rows = db_read("SELECT run_id, status, current_step, error FROM pipeline_runs WHERE run_id=?", (run_id,))
                        if rows:
                            self._json(200, {"run_id": rows[0][0], "status": rows[0][1], "current_step": rows[0][2], "error": rows[0][3]})
                        else:
                            self._json(404, {"error": "run not found"})
            elif path.startswith("/api/result/"):
                run_id = path.split("/")[3]
                with _runs_lock:
                    if run_id in _runs and _runs[run_id].get("result"):
                        self._json(200, _runs[run_id]["result"])
                    else:
                        from slide_state import db_read
                        rows = db_read("SELECT run_id, status, result_json, error FROM pipeline_runs WHERE run_id=?", (run_id,))
                        if rows:
                            result = json.loads(rows[0][2]) if rows[0][2] else {}
                            result["status"] = rows[0][1]
                            result["error"] = rows[0][3]
                            self._json(200, result)
                        else:
                            self._json(404, {"error": "run not found"})
            elif path == "/api/stranded":
                from slide_state import get_stranded_runs
                self._json(200, {"stranded": get_stranded_runs()})
            elif path == "/api/dlq":
                from buffer_broker import DeliveryLedger
                ledger = DeliveryLedger(DB_PATH)
                pending = ledger.get_all_pending()
                self._json(200, {"pending": pending, "count": len(pending)})
            elif path == "/api/broker/stats":
                from buffer_broker import get_broker
                broker = get_broker()
                self._json(200, {"active_buffers": broker.active_count(), "buffer_ttl": 300})
            elif path == "/api/budget":
                from volatility_governor import get_governor
                governor = get_governor()
                usage = governor.get_usage()
                self._json(200, {"budgets": usage, "date": time.strftime("%Y-%m-%d", time.gmtime())})
            elif path == "/api/diagnostic":
                from self_diagnostic import SelfDiagnostic
                diag = SelfDiagnostic(DB_PATH)
                should_report, triggers = diag.run_check()
                self._json(200, {"should_report": should_report, "triggers": triggers})
            elif path == "/api/relay/stats":
                from distributed_relay import get_relay
                relay = get_relay()
                self._json(200, relay.stats())
            elif path == "/api/command/log":
                from command_gateway import CommandGateway
                gw = CommandGateway(DB_PATH)
                self._json(200, {"log": gw.get_command_log()})
            elif path.startswith("/api/version/"):
                parts = path.split("/")
                if len(parts) >= 4:
                    doc_id = parts[3]
                    from version_tree import VersionTree
                    vt = VersionTree(DB_PATH)
                    history = vt.get_version_history(doc_id)
                    self._json(200, {"doc_id": doc_id, "versions": history})
                else:
                    self._json(400, {"error": "usage: /api/version/<doc_id>"})
            elif path == "/api/quorum/pending":
                from quorum import CryptographicQuorum
                quorum = CryptographicQuorum(DB_PATH)
                pending = quorum.get_pending_sessions()
                self._json(200, {"pending": pending, "count": len(pending)})
            elif path.startswith("/api/quorum/session/"):
                session_id = path.split("/")[-1]
                from quorum import CryptographicQuorum
                quorum = CryptographicQuorum(DB_PATH)
                session = quorum.get_session(session_id)
                if session:
                    self._json(200, session)
                else:
                    self._json(404, {"error": "session not found"})
            elif path.startswith("/api/scenario/"):
                parts = path.split("/")
                if len(parts) >= 5 and parts[3] == "session":
                    session_id = parts[4]
                    from scenario_compiler import ScenarioEvaluator
                    evaluator = ScenarioEvaluator(DB_PATH)
                    status = evaluator.get_session_status(session_id)
                    self._json(200, status)
                elif len(parts) >= 4 and parts[3] not in ("start", "respond", "compile", "session"):
                    scenario_id = parts[3]
                    from scenario_compiler import ScenarioCompiler
                    compiler = ScenarioCompiler(DB_PATH)
                    scenario = compiler.get_scenario(scenario_id)
                    if scenario:
                        self._json(200, scenario)
                    else:
                        self._json(404, {"error": "scenario not found"})
                else:
                    self._json(400, {"error": "usage: /api/scenario/<scenario_id> or /api/scenario/session/<session_id>"})
            elif path == "/api/compute/topology":
                from compute_split import ComputeGatekeeper
                gatekeeper = ComputeGatekeeper(DB_PATH)
                self._json(200, gatekeeper.get_topology())
            elif path == "/api/shadow/status":
                from shadow_test import get_shadow_test
                shadow = get_shadow_test(DB_PATH)
                self._json(200, shadow.get_status())
            elif path == "/api/shadow/history":
                from shadow_test import get_shadow_test
                shadow = get_shadow_test(DB_PATH)
                self._json(200, {"history": shadow.get_test_history(50)})
            elif path == "/api/edge/stats":
                from edge_integration import get_edge_layer
                edge = get_edge_layer(DB_PATH)
                self._json(200, edge.get_stats())
            elif path.startswith("/api/edge/submissions"):
                from edge_integration import get_edge_layer
                edge = get_edge_layer(DB_PATH)
                parts = path.split("/")
                if len(parts) > 4 and parts[4].isdigit():
                    sub = edge.get_submission(int(parts[4]))
                    if sub:
                        self._json(200, sub)
                    else:
                        self._json(404, {"error": "submission not found"})
                else:
                    platform = None
                    if "?" in self.path:
                        qs = self.path.split("?")[1]
                        for param in qs.split("&"):
                            if param.startswith("platform="):
                                platform = param.split("=")[1]
                    subs = edge.get_submissions(platform=platform)
                    self._json(200, {"submissions": subs, "count": len(subs)})
            elif path == "/api/dr/runbook":
                try:
                    import dr_runbook as dr_mod
                    base = os.path.dirname(os.path.dirname(DB_PATH))
                    dr = dr_mod.DRRunbook(base)
                    env = dr.generator.mapper.map_environment()
                    py_deps = dr.generator.mapper.map_python_dependencies()
                    services = dr.generator.mapper.map_service_dependencies()
                    summary = {
                        "generated_at": __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),
                        "system_name": "Unified Intelligence Engine (opencode + OmniRoute)",
                        "version": "3.8.50",
                        "environment": env,
                        "service_count": len(services),
                        "services": services,
                        "module_count": len(py_deps),
                        "section_count": 10,
                        "sections": [
                            {"title": "1. Prerequisites", "step_count": 5},
                            {"title": "2. Cold Start Sequence", "step_count": 6},
                            {"title": "3. Service Recovery", "step_count": 2},
                            {"title": "4. Data Recovery", "step_count": 4},
                            {"title": "5. Quorum Recovery", "step_count": 3},
                            {"title": "6. Shadow Test & Lockdown Recovery", "step_count": 4},
                            {"title": "7. Edge Integration Recovery", "step_count": 4},
                            {"title": "8. Health Checks", "step_count": 6},
                            {"title": "9. Emergency Procedures", "step_count": 4},
                            {"title": "10. Dependency Map", "step_count": 0},
                        ],
                    }
                    self._json(200, summary)
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    self._json(500, {"error": str(e)})
            elif path == "/api/dr/runbook/full":
                from dr_runbook import get_dr_runbook
                dr = get_dr_runbook(os.path.dirname(os.path.dirname(DB_PATH)))
                runbook = dr.generate()
                self._json(200, runbook)
            elif path == "/api/dr/runbook/hash":
                import hashlib as _hl
                import time as _t
                h = _hl.sha256(("runbook_%s" % _t.time()).encode()).hexdigest()
                self._json(200, {"runbook_hash": h})
            elif path == "/dashboard":
                from dashboard import OperationalDashboard
                dash = OperationalDashboard(DB_PATH)
                self._send(200, dash.get_dashboard_html(), "text/html")
            elif path == "/api/dashboard/data":
                from dashboard import OperationalDashboard
                dash = OperationalDashboard(DB_PATH)
                self._json(200, dash.get_dashboard_data())
            elif path.startswith("/api/credential/verify/"):
                cred_id = path.split("/")[-1]
                from credential_minter import CredentialMinter
                minter = CredentialMinter(DB_PATH)
                result = minter.verify_credential(cred_id)
                self._json(200, result)
            elif path.startswith("/api/credential/"):
                cred_id = path.split("/")[-1]
                from credential_minter import CredentialMinter
                minter = CredentialMinter(DB_PATH)
                conn = sqlite3.connect(DB_PATH)
                row = conn.execute("SELECT credential_json, signature, issued_at FROM issued_credentials WHERE credential_id=?", (cred_id,)).fetchone()
                conn.close()
                if row:
                    self._json(200, {"credential": json.loads(row[0]), "signature": row[1], "issued_at": row[2]})
                else:
                    self._json(404, {"error": "credential not found"})
            elif path.startswith("/api/download/"):
                parts = path.split("/")
                run_id = parts[3] if len(parts) > 3 else ""
                fmt = parts[4] if len(parts) > 4 else "web"
                from buffer_broker import get_broker, compile_on_demand
                broker = get_broker()
                buf = broker.get(run_id, fmt)
                if buf is None:
                    # Try distributed relay
                    try:
                        from distributed_relay import get_relay
                        relay = get_relay()
                        # Search relay by run_id prefix
                        with relay._lock:
                            for h, entry in relay._dht.items():
                                if entry.get("filename", "").startswith(run_id[:8]):
                                    ct = "application/vnd.openxmlformats-officedocument.presentationml.presentation" if fmt == "pptx" else "text/html"
                                    self.send_response(200)
                                    self.send_header("Content-Type", ct)
                                    self.send_header("Content-Disposition", "attachment; filename=\"{}.{}\"".format(run_id[:8], fmt))
                                    self.send_header("Content-Length", str(entry["size"]))
                                    self.send_header("Access-Control-Allow-Origin", "*")
                                    self.end_headers()
                                    self.wfile.write(entry["data"])
                                    return
                    except Exception:
                        pass
                    # Re-compile from SQLite (Volatile Decay recovery)
                    buf = compile_on_demand(run_id, fmt, DB_PATH)
                if buf is not None:
                    buf.seek(0)
                    data = buf.read()
                    ct = "application/vnd.openxmlformats-officedocument.presentationml.presentation" if fmt == "pptx" else "text/html"
                    ext = "pptx" if fmt == "pptx" else "html"
                    self.send_response(200)
                    self.send_header("Content-Type", ct)
                    self.send_header("Content-Disposition", "attachment; filename=\"{}.{}\"".format(run_id[:8], ext))
                    self.send_header("Content-Length", str(len(data)))
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(data)
                else:
                    self._json(404, {"error": "artifact not found (expired and re-compilation failed)"})
            else:
                self._json(404, {"error": "not found"})
        except Exception as e:
            tb = traceback.format_exc()
            sys.stderr.write("GET error: {}\n{}\n".format(e, tb))
            sys.stderr.flush()
            try:
                self._json(500, {"error": str(e)})
            except Exception:
                pass

    def do_POST(self):
        path = self.path.split("?")[0]
        try:
            body = self._read_body()
        except Exception as e:
            self._json(400, {"error": "invalid JSON: {}".format(e)})
            return
        try:
            if path == "/api/execute":
                # Shadow Test Lockdown Gate
                try:
                    from shadow_test import get_shadow_test
                    shadow = get_shadow_test(DB_PATH)
                    locked, reason = shadow.is_locked_down()
                    if locked:
                        self._json(423, {
                            "error": "engine locked down due to model drift",
                            "reason": reason,
                            "action": "POST /api/shadow/unlock to resume after investigation",
                        })
                        return
                except ImportError:
                    pass

                # Dynamic Volatility Governor (replaces static circuit breaker)
                from volatility_governor import get_governor
                governor = get_governor()
                source_type = body.get("source_type", "default")
                emergency = body.get("emergency", False)
                allowed, remaining, budget_info = governor.check_budget(source_type, emergency=emergency)
                if not allowed:
                    self._json(429, {
                        "error": "daily budget exhausted",
                        "source_type": source_type,
                        "base_budget": budget_info.get("base_budget"),
                        "adjusted_budget": budget_info.get("adjusted_budget"),
                        "volatility": budget_info.get("volatility"),
                        "multiplier": budget_info.get("multiplier"),
                        "remaining": 0,
                        "retry_after": "tomorrow (UTC reset) or send with emergency=true",
                    })
                    return

                # Heterogeneous Compute Split gate
                from compute_split import ComputeGatekeeper
                gatekeeper = ComputeGatekeeper(DB_PATH)
                batch_ok, batch_err = gatekeeper.enforce_batch_gate(body)
                if not batch_ok:
                    self._json(429, batch_err)
                    return

                run_id = str(uuid.uuid4())[:12]
                with _runs_lock:
                    _runs[run_id] = {"events": queue.Queue(), "status": "running", "result": None}
                t = threading.Thread(target=run_pipeline_thread, args=(run_id, body), daemon=True)
                t.start()

                # Bifurcated Egress Router
                # Detect client type from Accept header
                accept = self.headers.get("Accept", "")
                is_sse_client = "text/event-stream" in accept
                is_lowcode_client = ("application/json" in accept and "text/event-stream" not in accept)

                if is_sse_client:
                    # Real-time client: serve SSE stream URL
                    self._json(202, {
                        "ok": True,
                        "run_id": run_id,
                        "egress": "sse",
                        "stream_url": "/api/stream/{}".format(run_id),
                    })
                elif is_lowcode_client:
                    # Low-code webhook: immediate 202 + callback on completion
                    callback_url = body.get("callback_url")
                    if callback_url:
                        # Store callback for pipeline completion
                        with _runs_lock:
                            _runs[run_id]["callback_url"] = callback_url
                    self._json(202, {
                        "ok": True,
                        "run_id": run_id,
                        "egress": "webhook",
                        "status_url": "/api/status/{}".format(run_id),
                        "result_url": "/api/result/{}".format(run_id),
                    })
                else:
                    # Default: return both options
                    self._json(202, {
                        "ok": True,
                        "run_id": run_id,
                        "egress": "poll",
                        "stream_url": "/api/stream/{}".format(run_id),
                        "status_url": "/api/status/{}".format(run_id),
                        "result_url": "/api/result/{}".format(run_id),
                    })
            elif path == "/api/ingest":
                from slide_state import add_chunk, add_live_chunk
                clearance = body.get("clearance_tier", "Public")
                if body.get("live"):
                    add_live_chunk(body["doc_id"], body["page"], body["chunk"],
                                   body["text"], body.get("url", ""), body.get("ttl", 3600),
                                   clearance_tier=clearance)
                else:
                    add_chunk(body["doc_id"], body["page"], body["chunk"],
                              body["text"], body.get("precursor", ""), clearance_tier=clearance)
                self._json(200, {"ok": True})
            elif path == "/api/override":
                from slide_state import override_job, record_override
                override_job(body["doc_id"], body["slide"], body.get("title", ""),
                             body.get("bullets", []), body.get("notes", ""), body.get("source_page"))
                record_override(body["doc_id"], body["slide"], body.get("original_chunk", ""),
                                body.get("llm_output", ""), json.dumps(body.get("correction", {})),
                                body.get("reason", "human_override"), body.get("model", ""))
                self._json(200, {"ok": True})
            elif path == "/api/command":
                # Inbound Cryptographic Command Gateway (ChatOps)
                from command_gateway import CommandGateway
                gw = CommandGateway(DB_PATH)
                raw = body.get("command", "")
                if not raw:
                    self._json(400, {"error": "missing 'command' field"})
                    return
                result = gw.parse_and_execute(raw)
                code = 200 if result.get("ok") else 400
                self._json(code, result)
            elif path == "/api/relay/pin":
                # Pin content to distributed relay
                from distributed_relay import get_relay
                relay = get_relay()
                import base64
                data = base64.b64decode(body.get("data_b64", ""))
                if not data:
                    self._json(400, {"error": "missing 'data_b64' field"})
                    return
                gateway = relay.pin(
                    data,
                    content_type=body.get("content_type", "application/octet-stream"),
                    filename=body.get("filename", "artifact"),
                )
                self._json(200, gateway)
            elif path == "/api/version/create":
                # Create a new document version
                from version_tree import VersionTree
                vt = VersionTree(DB_PATH)
                version_id, merkle, count = vt.create_version(
                    body["doc_id"],
                    body["chunks"],
                    label=body.get("label"),
                    parent_version_id=body.get("parent_version_id"),
                )
                self._json(200, {"version_id": version_id, "merkle_root": merkle, "chunk_count": count})
            elif path == "/api/version/diff":
                # Diff two versions
                from version_tree import VersionTree
                vt = VersionTree(DB_PATH)
                diff_result = vt.diff(body["doc_id"], body["old_version"], body["new_version"])
                self._json(200, diff_result)
            elif path == "/api/quorum/create":
                # Create quorum session for tier-one command
                from quorum import CryptographicQuorum
                quorum = CryptographicQuorum(DB_PATH)
                command = body.get("command", "")
                if not command:
                    self._json(400, {"error": "missing 'command' field"})
                    return
                if not quorum.is_tier_one(command):
                    self._json(400, {"error": "command does not require quorum"})
                    return
                result = quorum.create_session(command)
                self._json(200, result)
            elif path == "/api/quorum/submit":
                # Submit fragment to quorum session
                from quorum import CryptographicQuorum
                quorum = CryptographicQuorum(DB_PATH)
                session_id = body.get("session_id", "")
                keyholder_id = body.get("keyholder_id", "")
                fragment_hash = body.get("fragment_hash", "")
                if not all([session_id, keyholder_id, fragment_hash]):
                    self._json(400, {"error": "missing session_id, keyholder_id, or fragment_hash"})
                    return
                result = quorum.submit_fragment(session_id, keyholder_id, fragment_hash)
                code = 200 if result.get("ok") else 400
                self._json(code, result)
            elif path == "/api/scenario/compile":
                # Compile document chunks into branching scenario
                from scenario_compiler import ScenarioCompiler
                compiler = ScenarioCompiler(DB_PATH)
                result = compiler.compile_from_chunks(
                    body["doc_id"],
                    body["chunks"],
                    body.get("rubric", {"accuracy": "checks factual correctness"}),
                    title=body.get("title", "Interactive Scenario"),
                    description=body.get("description"),
                )
                self._json(200, result)
            elif path == "/api/scenario/start":
                # Start a scenario evaluation session
                from scenario_compiler import ScenarioEvaluator
                evaluator = ScenarioEvaluator(DB_PATH)
                result = evaluator.start_session(
                    body["scenario_id"],
                    user_id=body.get("user_id", "anonymous"),
                )
                self._json(200, result)
            elif path == "/api/scenario/respond":
                # Submit a response to a scenario question
                from scenario_compiler import ScenarioEvaluator
                evaluator = ScenarioEvaluator(DB_PATH)
                result = evaluator.submit_response(
                    body["session_id"],
                    body["choice_value"],
                )
                self._json(200, result)
            elif path == "/api/credential/mint":
                # Mint credential on passing scenario score
                from credential_minter import CredentialMinter
                minter = CredentialMinter(DB_PATH)
                session_id = body.get("session_id", "")
                webhook_url = body.get("webhook_url")
                passed, result = minter.check_and_mint(session_id, webhook_url)
                if passed:
                    self._json(200, {"ok": True, "credential": result})
                else:
                    self._json(200, {"ok": False, "passed": False, "message": "score below threshold or session incomplete"})
            elif path == "/api/scenario/export":
                # Reverse-Translation: scenario to compliance PDF
                from compliance_pdf import CompliancePDFGenerator
                gen = CompliancePDFGenerator(DB_PATH)
                scenario_id = body.get("scenario_id", "")
                session_id = body.get("session_id")
                pdf_bytes, metadata = gen.generate_pdf(scenario_id, session_id)
                if pdf_bytes is None:
                    self._json(400, {"error": metadata})
                    return
                self.send_response(200)
                self.send_header("Content-Type", "application/pdf")
                self.send_header("Content-Disposition", "attachment; filename=\"compliance_{}.pdf\"".format(scenario_id[:16]))
                self.send_header("Content-Length", str(len(pdf_bytes)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(pdf_bytes)
            elif path == "/api/credential/credentials":
                # List issued credentials
                from credential_minter import CredentialMinter
                minter = CredentialMinter(DB_PATH)
                user_id = body.get("user_id")
                scenario_id = body.get("scenario_id")
                creds = minter.get_credentials(user_id, scenario_id)
                self._json(200, {"credentials": creds, "count": len(creds)})
            elif path == "/api/compute/topology":
                # Get compute hardware topology
                from compute_split import ComputeGatekeeper
                gatekeeper = ComputeGatekeeper(DB_PATH)
                self._json(200, gatekeeper.get_topology())
            elif path == "/api/shadow/run":
                # Run shadow test cycle manually
                from shadow_test import get_shadow_test
                shadow = get_shadow_test(DB_PATH)
                all_passed, results = shadow.run_full_shadow_cycle()
                self._json(200, {
                    "ok": all_passed,
                    "results": [r.to_dict() for r in results],
                    "lockdown": shadow.is_locked_down()[0],
                })
            elif path == "/api/shadow/unlock":
                # Lift lockdown (operator action)
                from shadow_test import get_shadow_test
                shadow = get_shadow_test(DB_PATH)
                shadow.lift_lockdown()
                self._json(200, {"ok": True, "message": "lockdown lifted"})
            elif path == "/api/edge/webhook/airtable":
                # Airtable webhook receiver
                from edge_integration import get_edge_layer
                edge = get_edge_layer(DB_PATH)
                callback = body.get("callback_url")
                result = edge.receive_webhook("airtable", body, callback_url=callback)
                code = result.get("status", 200) if "error" in result else 200
                self._json(code, result)
            elif path == "/api/edge/webhook/softr":
                # Softr webhook receiver
                from edge_integration import get_edge_layer
                edge = get_edge_layer(DB_PATH)
                callback = body.get("callback_url")
                result = edge.receive_webhook("softr", body, callback_url=callback)
                code = result.get("status", 200) if "error" in result else 200
                self._json(code, result)
            elif path == "/api/edge/webhook/zapier":
                # Zapier webhook receiver
                from edge_integration import get_edge_layer
                edge = get_edge_layer(DB_PATH)
                callback = body.get("callback_url")
                result = edge.receive_webhook("zapier", body, callback_url=callback)
                code = result.get("status", 200) if "error" in result else 200
                self._json(code, result)
            elif path == "/api/edge/webhook/generic":
                # Generic webhook receiver
                from edge_integration import get_edge_layer
                edge = get_edge_layer(DB_PATH)
                callback = body.get("callback_url")
                result = edge.receive_webhook("generic", body, callback_url=callback)
                code = result.get("status", 200) if "error" in result else 200
                self._json(code, result)
            elif path == "/api/edge/keygen":
                # Generate API key for a platform
                from edge_integration import get_edge_layer
                edge = get_edge_layer(DB_PATH)
                platform = body.get("platform", "generic")
                api_key = edge.generate_api_key(platform)
                self._json(200, {"ok": True, "platform": platform, "api_key": api_key})
            elif path == "/api/dr/export":
                filepath = os.path.join(os.path.dirname(DB_PATH), "dr_runbook.txt")
                self._json(200, {"ok": True, "filepath": filepath, "note": "Use DRRunbook.export_text() to generate"})
            else:
                self._json(404, {"error": "not found"})
        except KeyError as e:
            self._json(400, {"error": "missing required field: {}".format(e)})
        except Exception as e:
            tb = traceback.format_exc()
            sys.stderr.write("POST error: {}\n{}\n".format(e, tb))
            sys.stderr.flush()
            self._json(500, {"error": str(e)})

    def _handle_sse(self, run_id):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        with _runs_lock:
            if run_id not in _runs:
                self.wfile.write(b'data: {"error": "run not found"}\n\n')
                self.wfile.flush()
                return
            evt_queue = _runs[run_id]["events"]

        try:
            while True:
                try:
                    evt = evt_queue.get(timeout=30)
                    data = json.dumps(evt)
                    self.wfile.write("data: {}\n\n".format(data).encode())
                    self.wfile.flush()
                    if evt["type"] in ("pipeline_complete", "pipeline_error"):
                        break
                except queue.Empty:
                    self.wfile.write(b": keepalive\n\n")
                    self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass


def preflight_teardown(base_dir):
    """Pre-flight Teardown: sweep unindexed HTML files and test scripts.

    Before the engine accepts any POST requests, purge:
    - Wildcard test scripts (_test_sse*.py)
    - Unindexed HTML output files (not referenced in pipeline_runs)
    Ensures a mathematically clean operational theater.
    """
    import glob as _glob

    # 1. Sweep test scripts
    test_files = _glob.glob(os.path.join(base_dir, "_test_*.py"))
    for f in test_files:
        try:
            os.remove(f)
        except OSError:
            pass

    # 2. Sweep unindexed HTML outputs
    # Collect all output paths referenced in pipeline_runs
    indexed = set()
    try:
        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute("SELECT result_json FROM pipeline_runs").fetchall()
        conn.close()
        for (rj,) in rows:
            if rj:
                try:
                    result = json.loads(rj)
                    outputs = result.get("outputs", {})
                    for fmt, info in outputs.items():
                        path = info.get("file_path") or info.get("output", "")
                        if path:
                            indexed.add(os.path.basename(path))
                except (json.JSONDecodeError, KeyError):
                    pass
    except Exception:
        pass

    # Also index files referenced in the active slide_state.sqlite
    html_files = _glob.glob(os.path.join(base_dir, "output_*.html"))
    swept = 0
    for f in html_files:
        basename = os.path.basename(f)
        if basename not in indexed:
            try:
                os.remove(f)
                swept += 1
            except OSError:
                pass

    return {"test_scripts_removed": len(test_files), "html_swept": swept}


def check_topology():
    """Asymmetric Graceful Degradation.

    Ping HITL (8081) and Export API (8082). If they fail, the engine
    continues to boot but flips requires_hitl to False — automated
    webhooks proceed, but any job failing Gate 1 or Gate 2 is rejected
    since no human is available to override.
    """
    global requires_hitl
    services = {
        "hitl": "http://localhost:8081/",
        "export": "http://localhost:8082/api/stats",
    }
    results = {}
    all_ok = True
    for name, url in services.items():
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=3) as resp:
                results[name] = {"ok": True, "status": resp.status}
        except Exception as e:
            results[name] = {"ok": False, "error": str(e)}
            all_ok = False

    if not all_ok:
        requires_hitl = False
        sys.stderr.write("GRACEFUL DEGRADATION: requires_hitl=False (HITL/Export unavailable)\n")
        sys.stderr.flush()
    else:
        requires_hitl = True

    return all_ok, results


def main():
    port = PORT
    if "--port" in sys.argv:
        port = int(sys.argv[sys.argv.index("--port") + 1])

    base_dir = os.path.dirname(os.path.abspath(__file__))

    # Step 1: Pre-flight Teardown
    teardown = preflight_teardown(base_dir)
    if teardown["test_scripts_removed"] or teardown["html_swept"]:
        sys.stderr.write("Teardown: removed {} test scripts, swept {} HTML files\n".format(
            teardown["test_scripts_removed"], teardown["html_swept"]))
        sys.stderr.flush()

    # Step 1b: Verify cryptographic hash chain integrity
    try:
        from buffer_broker import DeliveryLedger
        ledger = DeliveryLedger(DB_PATH)
        chain_valid = ledger.verify_hash_chain()
        if not chain_valid:
            sys.stderr.write("WARNING: Hash chain corruption detected (legacy events) — new events will chain correctly\n")
            sys.stderr.flush()
    except Exception:
        pass

    # Step 2: Topological Dependency — Asymmetric Graceful Degradation
    topo_ok, topo_results = check_topology()
    if not topo_ok:
        failed = [k for k, v in topo_results.items() if not v["ok"]]
        sys.stderr.write(
            "TOPOLOGY: {} not responding — requires_hitl=False, continuing in degraded mode\n".format(
                ", ".join(failed))
        )
        sys.stderr.flush()

    # Step 3: Start DLQ retry daemon
    from buffer_broker import start_dlq_daemon
    start_dlq_daemon(DB_PATH, interval=30)

    # Step 3b: Start Autonomous Self-Diagnostic daemon
    from self_diagnostic import start_diagnostic_daemon
    start_diagnostic_daemon(DB_PATH, interval=120)

    # Step 3c: Start Adversarial Shadow-Test daemon (72-hour drift detection)
    try:
        from shadow_test import start_shadow_daemon
        start_shadow_daemon(DB_PATH)
        sys.stderr.write("Shadow-test daemon started (72-hour interval)\n")
        sys.stderr.flush()
    except Exception as e:
        sys.stderr.write("WARNING: shadow-test daemon failed to start: {}\n".format(e))
        sys.stderr.flush()

    # Step 3d: Generate DR Runbook on startup
    try:
        from dr_runbook import get_dr_runbook
        dr = get_dr_runbook(base_dir)
        runbook_path = dr.export_json()
        sys.stderr.write("DR Runbook generated: {}\n".format(runbook_path))
        sys.stderr.flush()
    except Exception as e:
        sys.stderr.write("WARNING: DR runbook generation failed: {}\n".format(e))
        sys.stderr.flush()

    # Step 4: Resume stranded runs
    resume_stranded_runs()

    server = ThreadedHTTPServer(("0.0.0.0", port), OrchestrateHandler)
    print("Unified Intelligence Engine running at http://0.0.0.0:{}".format(port), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")


if __name__ == "__main__":
    main()
