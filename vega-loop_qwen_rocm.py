import json
import os
import platform
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

DEFAULT_MODEL = "qwen3.5:2b"
# ~/.local/bin/ollama-rocm-serve の既定ポートに合わせる。
DEFAULT_OLLAMA_HOST = "http://127.0.0.1:11435"

MODEL = os.environ.get("MODEL", DEFAULT_MODEL)
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", DEFAULT_OLLAMA_HOST).strip()
PROMPT = (
    "Explain the architecture of the Linux kernel including scheduler, "
    "memory management, VFS, interrupts, and device drivers."
)
EPOCHS = int(os.environ.get("EPOCHS", "20"))
NUM_PREDICT = int(os.environ.get("NUM_PREDICT", "512"))
# 単一値だけでなく "0,1,2,-1" のような複数値も受け付ける。
NUM_GPU_RAW = os.environ.get("NUM_GPU", "0,1,2,-1")
TIMEOUT = int(os.environ.get("TIMEOUT", "300"))

BASE_DIR = Path(__file__).resolve().parent
LOG_ROOT = BASE_DIR / "vega_work_log"
RUN_ID = datetime.now().strftime("run_%Y%m%d_%H%M%S")
RUN_DIR = LOG_ROOT / RUN_ID


def parse_num_gpu_values(raw: str) -> list[int]:
    normalized = raw.replace(" ", ",")
    tokens = [tok.strip() for tok in normalized.split(",") if tok.strip()]
    if not tokens:
        raise ValueError("NUM_GPU is empty")
    values: list[int] = []
    for tok in tokens:
        values.append(int(tok))
    return values


NUM_GPU_VALUES = parse_num_gpu_values(NUM_GPU_RAW)


def build_ollama_url(host: str) -> str:
    host = host.rstrip("/")
    if host.endswith("/api/generate"):
        return host
    return f"{host}/api/generate"


OLLAMA_URL = build_ollama_url(OLLAMA_HOST)


def mkdirs() -> None:
    RUN_DIR.mkdir(parents=True, exist_ok=True)


def run_cmd(cmd: list[str], timeout: int = 30) -> str:
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout,
            check=False,
        )
        return result.stdout
    except Exception as e:
        return f"[command failed] {cmd}\n{e}\n"


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def collect_env_snapshot(run_started_at: datetime) -> dict:
    return {
        "timestamp": datetime.now().isoformat(),
        "hostname": platform.node(),
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "backend_target": "rocm",
        "model": MODEL,
        "epochs": EPOCHS,
        "num_predict": NUM_PREDICT,
        "num_gpu": NUM_GPU_VALUES[0] if len(NUM_GPU_VALUES) == 1 else None,
        "num_gpu_values": NUM_GPU_VALUES,
        "num_gpu_raw": NUM_GPU_RAW,
        "ollama_host": OLLAMA_HOST,
        "ollama_url": OLLAMA_URL,
        "prompt_preview": PROMPT[:120],
        "cwd": str(Path.cwd()),
        "script_path": str(Path(__file__).resolve()),
        "run_started_at": run_started_at.isoformat(),
        "environment": {
            "HSA_OVERRIDE_GFX_VERSION": os.environ.get("HSA_OVERRIDE_GFX_VERSION"),
            "HSA_ENABLE_SDMA": os.environ.get("HSA_ENABLE_SDMA"),
            "HSA_ENABLE_INTERRUPT": os.environ.get("HSA_ENABLE_INTERRUPT"),
            "HIP_VISIBLE_DEVICES": os.environ.get("HIP_VISIBLE_DEVICES"),
            "ROCR_VISIBLE_DEVICES": os.environ.get("ROCR_VISIBLE_DEVICES"),
            "ROCM_PATH": os.environ.get("ROCM_PATH"),
            "OLLAMA_HOST": os.environ.get("OLLAMA_HOST"),
            "OLLAMA_LLM_LIBRARY": os.environ.get("OLLAMA_LLM_LIBRARY"),
            "OLLAMA_NUM_GPU": os.environ.get("OLLAMA_NUM_GPU"),
        },
    }


def extract_error_from_response(resp: requests.Response) -> tuple[str, str]:
    raw_text = resp.text
    try:
        parsed = resp.json()
    except ValueError:
        parsed = None

    if isinstance(parsed, dict):
        err = parsed.get("error")
        if err is not None:
            return str(err), raw_text[:2000]
        return json.dumps(parsed, ensure_ascii=False)[:2000], raw_text[:2000]

    return raw_text[:2000], raw_text[:2000]


def ollama_generate(prompt: str, num_gpu: int) -> dict:
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_predict": NUM_PREDICT,
            "num_gpu": num_gpu,
        },
    }

    started = time.time()
    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=TIMEOUT)
    except requests.exceptions.ConnectTimeout as e:
        elapsed = time.time() - started
        return {
            "ok": False,
            "elapsed": elapsed,
            "error_type": "connect_timeout",
            "error": str(e),
        }
    except requests.exceptions.ReadTimeout as e:
        elapsed = time.time() - started
        return {
            "ok": False,
            "elapsed": elapsed,
            "error_type": "read_timeout",
            "error": str(e),
        }
    except requests.exceptions.Timeout as e:
        elapsed = time.time() - started
        return {
            "ok": False,
            "elapsed": elapsed,
            "error_type": "timeout",
            "error": str(e),
        }
    except requests.exceptions.ConnectionError as e:
        elapsed = time.time() - started
        return {
            "ok": False,
            "elapsed": elapsed,
            "error_type": "connection_error",
            "error": str(e),
        }
    except requests.exceptions.RequestException as e:
        elapsed = time.time() - started
        return {
            "ok": False,
            "elapsed": elapsed,
            "error_type": "request_exception",
            "error": str(e),
        }

    elapsed = time.time() - started
    if not resp.ok:
        response_error, response_text = extract_error_from_response(resp)
        return {
            "ok": False,
            "elapsed": elapsed,
            "error_type": "http_error",
            "error": f"HTTP {resp.status_code} from Ollama: {response_error}",
            "http_status": resp.status_code,
            "response_error": response_error,
            "response_text_snippet": response_text,
        }

    try:
        data = resp.json()
    except ValueError as e:
        return {
            "ok": False,
            "elapsed": elapsed,
            "error_type": "json_decode_error",
            "error": f"Failed to decode JSON response: {e}",
            "http_status": resp.status_code,
            "response_text_snippet": resp.text[:2000],
        }

    return {
        "ok": True,
        "elapsed": elapsed,
        "data": data,
    }


def append_record_summary(results: dict) -> None:
    summary: dict[str, dict[str, int]] = {}
    for rec in results["records"]:
        key = str(rec.get("num_gpu"))
        if key not in summary:
            summary[key] = {"ok": 0, "error": 0}
        if rec.get("status") == "ok":
            summary[key]["ok"] += 1
        else:
            summary[key]["error"] += 1
    results["summary_by_num_gpu"] = summary


def capture_backend_probes(run_started_at: datetime) -> None:
    write_text(RUN_DIR / "env.txt", json.dumps(dict(os.environ), ensure_ascii=False, indent=2))
    write_text(RUN_DIR / "rocm_smi_before.txt", run_cmd(["rocm-smi"], timeout=60))
    write_text(RUN_DIR / "ollama_ps_before.txt", run_cmd(["ollama", "ps"], timeout=60))
    write_text(RUN_DIR / "ollama_version.txt", run_cmd(["ollama", "--version"], timeout=30))
    write_text(
        RUN_DIR / "rocminfo_gfx.txt",
        run_cmd(["bash", "-lc", "rocminfo | grep -Ei 'gfx|Name|Agent' || true"], timeout=120),
    )
    write_text(
        RUN_DIR / "backend_probe.txt",
        "\n".join([
            "== date ==",
            run_cmd(["date", "-Is"], timeout=10),
            "== ollama env ==",
            run_cmd(
                [
                    "bash",
                    "-lc",
                    "env | grep -E '^(OLLAMA|ROCR|HSA|HIP|ROCM)_' | sort || true",
                ],
                timeout=30,
            ),
            "== rocm-smi quick ==",
            run_cmd(["bash", "-lc", "rocm-smi --showdriverversion --showproductname || rocm-smi"], timeout=60),
            "== ollama ps ==",
            run_cmd(["ollama", "ps"], timeout=60),
            "== process grep ollama ==",
            run_cmd(["bash", "-lc", "ps -ef | grep -E 'ollama|llama' | grep -v grep || true"], timeout=30),
            "== systemctl user units (ollama*) ==",
            run_cmd(["bash", "-lc", "systemctl --user list-units 'ollama*' --no-pager || true"], timeout=30),
            "== listen sockets (11434/11435) ==",
            run_cmd(["bash", "-lc", "ss -ltnp | grep -E ':11434|:11435' || true"], timeout=30),
            "== journalctl (recent) ==",
            run_cmd(
                [
                    "bash",
                    "-lc",
                    "journalctl --user -n 200 --no-pager | "
                    "grep -Ei 'ollama|ggml|vulkan|rocm|hip|llama' || true",
                ],
                timeout=60,
            ),
            f"== run started at ==\n{run_started_at.isoformat()}",
        ]),
    )


def main() -> None:
    mkdirs()
    run_started_at = datetime.now()
    run_started_for_journal = run_started_at.strftime("%Y-%m-%d %H:%M:%S")

    meta = collect_env_snapshot(run_started_at)
    write_json(RUN_DIR / "meta.json", meta)
    capture_backend_probes(run_started_at)

    results = {
        "run_id": RUN_ID,
        "started_at": run_started_at.isoformat(),
        "backend_target": "rocm",
        "model": MODEL,
        "epochs": EPOCHS,
        "total_epochs": EPOCHS * len(NUM_GPU_VALUES),
        "num_predict": NUM_PREDICT,
        "num_gpu": NUM_GPU_VALUES[0] if len(NUM_GPU_VALUES) == 1 else None,
        "num_gpu_values": NUM_GPU_VALUES,
        "num_gpu_raw": NUM_GPU_RAW,
        "ollama_host": OLLAMA_HOST,
        "records": [],
    }

    response_dir = RUN_DIR / "responses"
    response_dir.mkdir(exist_ok=True)

    epoch_global = 0
    total = EPOCHS * len(NUM_GPU_VALUES)

    for num_gpu in NUM_GPU_VALUES:
        for case_epoch in range(1, EPOCHS + 1):
            epoch_global += 1
            record = {
                "epoch": epoch_global,
                "case_epoch": case_epoch,
                "started_at": datetime.now().isoformat(),
                "num_gpu": num_gpu,
            }

            rocm_before_file = f"rocm_smi_epoch_{epoch_global:03d}_before.txt"
            rocm_after_file = f"rocm_smi_epoch_{epoch_global:03d}_after.txt"
            ollama_ps_before_file = f"ollama_ps_epoch_{epoch_global:03d}_before.txt"
            ollama_ps_after_file = f"ollama_ps_epoch_{epoch_global:03d}_after.txt"

            write_text(RUN_DIR / rocm_before_file, run_cmd(["rocm-smi"], timeout=60))
            write_text(RUN_DIR / ollama_ps_before_file, run_cmd(["ollama", "ps"], timeout=60))

            try:
                outcome = ollama_generate(PROMPT, num_gpu)

                write_text(RUN_DIR / rocm_after_file, run_cmd(["rocm-smi"], timeout=60))
                write_text(RUN_DIR / ollama_ps_after_file, run_cmd(["ollama", "ps"], timeout=60))

                record.update({
                    "rocm_smi_before_file": rocm_before_file,
                    "rocm_smi_after_file": rocm_after_file,
                    "ollama_ps_before_file": ollama_ps_before_file,
                    "ollama_ps_after_file": ollama_ps_after_file,
                })

                if outcome["ok"]:
                    data = outcome["data"]
                    response_text = data.get("response", "")
                    response_file = response_dir / f"epoch_{epoch_global:03d}.txt"
                    write_text(response_file, response_text)

                    record.update({
                        "status": "ok",
                        "elapsed_sec": round(outcome["elapsed"], 3),
                        "done": data.get("done"),
                        "eval_count": data.get("eval_count"),
                        "eval_duration": data.get("eval_duration"),
                        "prompt_eval_count": data.get("prompt_eval_count"),
                        "prompt_eval_duration": data.get("prompt_eval_duration"),
                        "response_chars": len(response_text),
                        "response_file": str(response_file.name),
                    })
                    print(
                        f"[{epoch_global}/{total}] ok  num_gpu={num_gpu} "
                        f"case_epoch={case_epoch}/{EPOCHS} elapsed={outcome['elapsed']:.2f}s "
                        f"chars={len(response_text)}",
                        flush=True,
                    )
                else:
                    record.update({
                        "status": "error",
                        "elapsed_sec": round(outcome["elapsed"], 3),
                        "error_type": outcome.get("error_type"),
                        "error": outcome.get("error"),
                    })
                    if "http_status" in outcome:
                        record["http_status"] = outcome["http_status"]
                    if "response_error" in outcome:
                        record["response_error"] = outcome["response_error"]
                    if "response_text_snippet" in outcome:
                        record["response_text_snippet"] = outcome["response_text_snippet"]

                    print(
                        f"[{epoch_global}/{total}] error  num_gpu={num_gpu} "
                        f"case_epoch={case_epoch}/{EPOCHS} type={outcome.get('error_type')} "
                        f"msg={outcome.get('error')}",
                        file=sys.stderr,
                        flush=True,
                    )
            except Exception as e:
                write_text(RUN_DIR / rocm_after_file, run_cmd(["rocm-smi"], timeout=60))
                write_text(RUN_DIR / ollama_ps_after_file, run_cmd(["ollama", "ps"], timeout=60))
                record.update({
                    "status": "error",
                    "rocm_smi_before_file": rocm_before_file,
                    "rocm_smi_after_file": rocm_after_file,
                    "ollama_ps_before_file": ollama_ps_before_file,
                    "ollama_ps_after_file": ollama_ps_after_file,
                    "error_type": "script_exception",
                    "error": f"{type(e).__name__}: {e}",
                })
                print(
                    f"[{epoch_global}/{total}] error  num_gpu={num_gpu} "
                    f"case_epoch={case_epoch}/{EPOCHS} type=script_exception "
                    f"msg={type(e).__name__}: {e}",
                    file=sys.stderr,
                    flush=True,
                )

            results["records"].append(record)
            append_record_summary(results)
            write_json(RUN_DIR / "result.json", results)

    results["finished_at"] = datetime.now().isoformat()
    write_text(RUN_DIR / "rocm_smi_after.txt", run_cmd(["rocm-smi"], timeout=60))
    write_text(RUN_DIR / "ollama_ps_after.txt", run_cmd(["ollama", "ps"], timeout=60))
    write_text(
        RUN_DIR / "ollama_journal_since_start.txt",
        run_cmd(
            [
                "bash",
                "-lc",
                "journalctl --user --since "
                f"'{run_started_for_journal}' --no-pager | "
                "grep -Ei 'ollama|ggml|vulkan|rocm|hip|llama' || true",
            ],
            timeout=120,
        ),
    )
    append_record_summary(results)
    write_json(RUN_DIR / "result.json", results)

    print(f"\nlog dir: {RUN_DIR}")


if __name__ == "__main__":
    main()
