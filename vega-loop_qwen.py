import json
import os
import platform
import subprocess
import time
from datetime import datetime
from pathlib import Path

import requests

MODEL = "qwen3.5:2b"
OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
PROMPT = (
    "Explain the architecture of the Linux kernel including scheduler, "
    "memory management, VFS, interrupts, and device drivers."
)
EPOCHS = int(os.environ.get("EPOCHS", "20"))
NUM_PREDICT = int(os.environ.get("NUM_PREDICT", "512"))
# Vega + Vulkan 環境では qwen3.5 のGPU実行で runner が SIGSEGV しやすい。
# デフォルトはCPU実行にし、必要なら環境変数で上書きする。
NUM_GPU = int(os.environ.get("NUM_GPU", "0"))
TIMEOUT = 300

BASE_DIR = Path(__file__).resolve().parent
LOG_ROOT = BASE_DIR / "vega_work_log"
RUN_ID = datetime.now().strftime("run_%Y%m%d_%H%M%S")
RUN_DIR = LOG_ROOT / RUN_ID


def mkdirs() -> None:
    RUN_DIR.mkdir(parents=True, exist_ok=True)


def run_cmd(cmd: list[str]) -> str:
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=30,
            check=False,
        )
        return result.stdout
    except Exception as e:
        return f"[command failed] {cmd}\n{e}\n"


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def collect_env_snapshot() -> dict:
    return {
        "timestamp": datetime.now().isoformat(),
        "hostname": platform.node(),
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "model": MODEL,
        "epochs": EPOCHS,
        "num_predict": NUM_PREDICT,
        "num_gpu": NUM_GPU,
        "prompt_preview": PROMPT[:120],
        "cwd": str(Path.cwd()),
        "script_path": str(Path(__file__).resolve()),
        "environment": {
            "HSA_OVERRIDE_GFX_VERSION": os.environ.get("HSA_OVERRIDE_GFX_VERSION"),
            "HSA_ENABLE_SDMA": os.environ.get("HSA_ENABLE_SDMA"),
            "OLLAMA_HOST": os.environ.get("OLLAMA_HOST"),
            "OLLAMA_LLM_LIBRARY": os.environ.get("OLLAMA_LLM_LIBRARY"),
            "OLLAMA_NUM_GPU": os.environ.get("OLLAMA_NUM_GPU"),
            "ROCR_VISIBLE_DEVICES": os.environ.get("ROCR_VISIBLE_DEVICES"),
        },
    }


def ollama_generate(prompt: str) -> tuple[dict, float]:
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_predict": NUM_PREDICT,
            "num_gpu": NUM_GPU,
        },
    }
    start = time.time()
    r = requests.post(OLLAMA_URL, json=payload, timeout=TIMEOUT)
    elapsed = time.time() - start
    if not r.ok:
        detail = r.text
        try:
            parsed = r.json()
            if isinstance(parsed, dict) and parsed.get("error"):
                detail = str(parsed["error"])
        except Exception:
            pass
        raise RuntimeError(f"HTTP {r.status_code} from Ollama: {detail}")
    return r.json(), elapsed


def main() -> None:
    mkdirs()

    # 実行前スナップショット
    meta = collect_env_snapshot()
    write_json(RUN_DIR / "meta.json", meta)

    write_text(RUN_DIR / "env.txt", json.dumps(dict(os.environ), ensure_ascii=False, indent=2))
    write_text(RUN_DIR / "rocm_smi_before.txt", run_cmd(["rocm-smi"]))
    write_text(RUN_DIR / "ollama_ps_before.txt", run_cmd(["ollama", "ps"]))
    write_text(RUN_DIR / "rocminfo_gfx.txt", run_cmd(["bash", "-lc", "rocminfo | grep gfx || true"]))

    results = {
        "run_id": RUN_ID,
        "started_at": datetime.now().isoformat(),
        "model": MODEL,
        "epochs": EPOCHS,
        "num_predict": NUM_PREDICT,
        "num_gpu": NUM_GPU,
        "records": [],
    }

    response_dir = RUN_DIR / "responses"
    response_dir.mkdir(exist_ok=True)

    for epoch in range(1, EPOCHS + 1):
        record = {
            "epoch": epoch,
            "started_at": datetime.now().isoformat(),
        }

        try:
            rocm_before = run_cmd(["rocm-smi"])
            data, elapsed = ollama_generate(PROMPT)
            rocm_after = run_cmd(["rocm-smi"])

            response_text = data.get("response", "")
            eval_count = data.get("eval_count")
            eval_duration = data.get("eval_duration")
            prompt_eval_count = data.get("prompt_eval_count")
            prompt_eval_duration = data.get("prompt_eval_duration")
            done = data.get("done")

            response_file = response_dir / f"epoch_{epoch:03d}.txt"
            write_text(response_file, response_text)

            record.update({
                "status": "ok",
                "elapsed_sec": round(elapsed, 3),
                "done": done,
                "eval_count": eval_count,
                "eval_duration": eval_duration,
                "prompt_eval_count": prompt_eval_count,
                "prompt_eval_duration": prompt_eval_duration,
                "num_gpu": NUM_GPU,
                "response_chars": len(response_text),
                "response_file": str(response_file.name),
                "rocm_smi_before_file": f"rocm_smi_epoch_{epoch:03d}_before.txt",
                "rocm_smi_after_file": f"rocm_smi_epoch_{epoch:03d}_after.txt",
            })

            write_text(RUN_DIR / record["rocm_smi_before_file"], rocm_before)
            write_text(RUN_DIR / record["rocm_smi_after_file"], rocm_after)

            print(f"[{epoch}/{EPOCHS}] ok  elapsed={elapsed:.2f}s  chars={len(response_text)}")

        except Exception as e:
            record.update({
                "status": "error",
                "error": str(e),
            })
            print(f"[{epoch}/{EPOCHS}] error: {e}")

        results["records"].append(record)
        write_json(RUN_DIR / "result.json", results)

    results["finished_at"] = datetime.now().isoformat()
    write_text(RUN_DIR / "rocm_smi_after.txt", run_cmd(["rocm-smi"]))
    write_text(RUN_DIR / "ollama_ps_after.txt", run_cmd(["ollama", "ps"]))
    write_json(RUN_DIR / "result.json", results)

    print(f"\nlog dir: {RUN_DIR}")


if __name__ == "__main__":
    main()
