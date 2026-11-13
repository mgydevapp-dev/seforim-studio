"""Download Qwen3-VL 4B Instruct as GGUF (the model + its picture reader 'mmproj') for the Android AI pack.
Usage: python tools/make_android_ai.py OUTDIR   -> OUTDIR/ai_android/{model.gguf, mmproj.gguf}"""
import os
import sys

from huggingface_hub import HfApi, hf_hub_download

REPOS = ["Qwen/Qwen3-VL-4B-Instruct-GGUF", "ggml-org/Qwen3-VL-4B-Instruct-GGUF", "unsloth/Qwen3-VL-4B-Instruct-GGUF"]
out = os.path.join(sys.argv[1], "ai_android")
os.makedirs(out, exist_ok=True)
api = HfApi()
for repo in REPOS:
    try:
        files = [f for f in api.list_repo_files(repo) if f.lower().endswith(".gguf")]
    except Exception as e:  # noqa
        print(repo, "not available:", e)
        continue
    print(repo, files)
    mm = [f for f in files if "mmproj" in f.lower()]
    models = [f for f in files if "mmproj" not in f.lower()]
    model = next((f for q in ("q4_k_m", "q4_k_s", "q4_0") for f in models if q in f.lower()), None)
    mmp = next((f for q in ("q8_0", "f16", "bf16") for f in mm if q in f.lower()), mm[0] if mm else None)
    if not (model and mmp):
        continue
    for f, name in ((model, "Qwen3-VL-4B-Instruct.gguf"), (mmp, "mmproj-Qwen3-VL-4B-Instruct.gguf")):
        p = hf_hub_download(repo, f, local_dir=os.path.join(sys.argv[1], "_dl"))
        os.replace(p, os.path.join(out, name))
        print("got", f, os.path.getsize(os.path.join(out, name)) // 2**20, "MB")
    break
else:
    sys.exit("No GGUF model found")
