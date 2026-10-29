
from pathlib import Path
import subprocess
import shutil
import os

print("=" * 68)
print("PRND PROJECT STARTUP")
print("=" * 68)

PERM_ROOT = Path(
    "/content/gdrive/MyDrive/Prnd-project"
)

PERM_REPO = PERM_ROOT / "LLMGNN_reference"
PERM_DATA = PERM_ROOT / "LLMGNN_data"
PERM_ENV  = PERM_ROOT / "env_backup"

LOCAL_REPO = Path("/content/LLMGNN_reference")
LOCAL_DATA = Path("/content/LLMGNN_data")

ENV_ROOT = Path(
    "/root/.local/share/mamba/envs"
)

ENV_DIR = ENV_ROOT / "llmgnn"

ENV_PYTHON = ENV_DIR / "bin/python"

ENV_ARCHIVE = (
    PERM_ENV / "llmgnn_env.tar.gz"
)

EXTRA_REQ = (
    PERM_ENV / "requirements-extra.txt"
)

MAMBA_BACKUP = (
    PERM_ENV / "micromamba"
)

MAMBA_LOCAL = Path(
    "/content/micromamba/micromamba"
)


# ============================================================
# A) VERIFY DRIVE
# ============================================================

if not PERM_ROOT.exists():
    raise RuntimeError(
        "Google Drive is not mounted at /content/gdrive.\n"
        "Mount Drive before running startup.py."
    )

print("✅ Permanent project root found")


# ============================================================
# B) ENSURE REPO/DATA SYMLINKS
# ============================================================

def ensure_link(local_path, drive_path, required_rel):

    required = drive_path / required_rel

    if not required.exists():
        raise FileNotFoundError(
            f"Permanent project file missing:\n{required}"
        )

    if local_path.is_symlink():

        if local_path.resolve() == drive_path.resolve():
            return

        local_path.unlink()

    elif local_path.exists():

        # Never silently delete a real local directory.
        raise RuntimeError(
            f"{local_path} exists as a real directory instead "
            "of a persistent symlink.\n"
            "Run the migration cell once before using startup.py."
        )

    os.symlink(
        str(drive_path),
        str(local_path),
        target_is_directory=True
    )


ensure_link(
    LOCAL_REPO,
    PERM_REPO,
    "src/helper/active.py"
)

ensure_link(
    LOCAL_DATA,
    PERM_DATA,
    "cora_random_sbert.pt"
)

print("✅ Repository is persistent")
print("✅ Data/cache directory is persistent")


# ============================================================
# C) RESTORE MICROMAMBA
# ============================================================

MAMBA_LOCAL.parent.mkdir(
    parents=True,
    exist_ok=True
)

if not MAMBA_LOCAL.exists():

    if not MAMBA_BACKUP.exists():
        raise FileNotFoundError(
            f"micromamba backup missing:\n{MAMBA_BACKUP}"
        )

    shutil.copy2(
        MAMBA_BACKUP,
        MAMBA_LOCAL
    )

MAMBA_LOCAL.chmod(0o755)

print("✅ micromamba ready")


# ============================================================
# D) RESTORE PYTHON ENVIRONMENT
# ============================================================

if not ENV_PYTHON.exists():

    if not ENV_ARCHIVE.exists():
        raise FileNotFoundError(
            f"Environment archive missing:\n{ENV_ARCHIVE}"
        )

    print("⏳ Restoring llmgnn environment...")

    ENV_ROOT.mkdir(
        parents=True,
        exist_ok=True
    )

    # Remove incomplete env only.
    if ENV_DIR.exists():
        shutil.rmtree(ENV_DIR)

    subprocess.run(
        [
            "tar",
            "-xzf",
            str(ENV_ARCHIVE),
            "-C",
            str(ENV_ROOT)
        ],
        check=True
    )

    print("✅ llmgnn environment restored")
else:
    print("✅ llmgnn environment already present")


if not ENV_PYTHON.exists():
    raise RuntimeError(
        "Environment restore finished but Python is missing."
    )


# ============================================================
# E) LIBRARY PATH
# ============================================================

env_lib = str(
    ENV_DIR / "lib"
)

old_ld = os.environ.get(
    "LD_LIBRARY_PATH",
    ""
)

parts = [
    x for x in old_ld.split(":")
    if x
]

if env_lib not in parts:
    os.environ["LD_LIBRARY_PATH"] = (
        env_lib +
        (":" + old_ld if old_ld else "")
    )


# ============================================================
# F) DEPENDENCY CHECK + SELF-HEAL EXTRAS
# ============================================================

check_code = (
    "import torch; "
    "import torch_geometric; "
    "import dgl; "
    "import editdistance; "
    "import tiktoken; "
    "import ipdb; "
    "import kmedoids; "
    "print('IMPORTS_OK')"
)

runtime_env = os.environ.copy()

check = subprocess.run(
    [
        str(ENV_PYTHON),
        "-c",
        check_code
    ],
    capture_output=True,
    text=True,
    env=runtime_env
)

if check.returncode != 0 and EXTRA_REQ.exists():

    print(
        "⚠️ Optional dependencies incomplete; "
        "repairing from requirements-extra.txt..."
    )

    subprocess.run(
        [
            str(ENV_PYTHON),
            "-m",
            "pip",
            "install",
            "-r",
            str(EXTRA_REQ)
        ],
        check=True,
        env=runtime_env
    )

    check = subprocess.run(
        [
            str(ENV_PYTHON),
            "-c",
            check_code
        ],
        capture_output=True,
        text=True,
        env=runtime_env
    )

if check.returncode != 0:
    print(check.stderr)

    raise RuntimeError(
        "llmgnn dependency verification failed."
    )

print("✅ Python environment verified")


# ============================================================
# G) PROJECT CHECK
# ============================================================

required = [
    LOCAL_REPO / "src/helper/active.py",
    LOCAL_REPO / "src/helper/data.py",
    LOCAL_REPO / "src/llm.py",
    LOCAL_REPO / "src/main.py",
    LOCAL_DATA / "cora_random_sbert.pt",
    LOCAL_DATA / "active/cora^cache^consistency.pt",
]

missing = [
    p for p in required
    if not p.exists()
]

if missing:

    print("Missing required project files:")

    for p in missing:
        print(" ❌", p)

    raise RuntimeError(
        "Persistent project is incomplete."
    )


# Optional research files
optional = [
    LOCAL_REPO / "src/structure/selector.py",
    LOCAL_REPO / (
        "experiments/manifests/"
        "m1_cora_pagerank2_b140_semantic_top3.json"
    ),
]

for p in optional:
    print(
        "✅" if p.exists() else "⚠️",
        p
    )


print("\n" + "=" * 68)
print("✅ PRND PROJECT READY")
print("=" * 68)

print(
    "Repo :",
    LOCAL_REPO,
    "->",
    LOCAL_REPO.resolve()
)

print(
    "Data :",
    LOCAL_DATA,
    "->",
    LOCAL_DATA.resolve()
)

print(
    "Python:",
    ENV_PYTHON
)

print(
    "\nChanges under /content/LLMGNN_reference "
    "and /content/LLMGNN_data are now written "
    "directly to Drive."
)
