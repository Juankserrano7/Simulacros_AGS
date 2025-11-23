import os
import subprocess
import tempfile
from pathlib import Path
from typing import Iterable, Optional, Tuple

import streamlit as st

from .config import METADATA_FILE


def _get_secrets() -> dict:
    """Devuelve secrets o {} si no existe archivo/config."""
    try:
        return st.secrets  # type: ignore[attr-defined]
    except Exception:
        return {}


def _write_deploy_key(deploy_key: str) -> Path:
    """Escribe la llave privada en un archivo temporal y la retorna."""
    tmp_file = Path(tempfile.gettempdir()) / "deploy_key"
    tmp_file.write_text(deploy_key, encoding="utf-8")
    tmp_file.chmod(0o600)
    return tmp_file


def _run_git_cmd(cmd: list[str], env_extra: Optional[dict] = None) -> Tuple[int, str, str]:
    env = os.environ.copy()
    if env_extra:
        env.update(env_extra)
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out, err = proc.communicate()
    return proc.returncode, out.strip(), err.strip()


def has_push_config() -> bool:
    # Local/tests: desactiva push si no hay secrets para evitar errores.
    secrets = _get_secrets()
    return bool(secrets.get("DEPLOY_KEY") and secrets.get("GIT_REPO_URL"))


def push_changes(ruta_archivo: Path, mensaje: str) -> None:
    """Hace commit y push del archivo cargado y los metadatos si hay configuración disponible."""
    secrets = _get_secrets()
    deploy_key = secrets.get("DEPLOY_KEY")
    repo_url = secrets.get("GIT_REPO_URL")
    branch = secrets.get("GIT_DEFAULT_BRANCH", "main")
    author_name = secrets.get("GIT_AUTHOR_NAME", "Simulacros Bot")
    author_email = secrets.get("GIT_AUTHOR_EMAIL", "bot@aspaen.edu.co")

    if not deploy_key or not repo_url:
        # En local o sin secrets configurados, omitir push sin cortar el flujo.
        return

    key_path = _write_deploy_key(deploy_key)
    ssh_cmd = f"ssh -i {key_path} -o IdentitiesOnly=yes"

    # Asegurar known_hosts
    subprocess.run(["ssh-keyscan", "github.com"], stdout=open(os.path.expanduser("~/.ssh/known_hosts"), "a"), check=False)

    env_extra = {
        "GIT_SSH_COMMAND": ssh_cmd,
        "GIT_AUTHOR_NAME": author_name,
        "GIT_AUTHOR_EMAIL": author_email,
        "GIT_COMMITTER_NAME": author_name,
        "GIT_COMMITTER_EMAIL": author_email,
    }

    # Asegurar remoto correcto
    _run_git_cmd(["git", "remote", "set-url", "origin", repo_url], env_extra)

    # git add
    archivos = [str(ruta_archivo), str(METADATA_FILE)]
    code, out, err = _run_git_cmd(["git", "add"] + archivos, env_extra)
    if code != 0:
        st.warning(f"No se pudo hacer git add: {err}")
        return

    # git commit
    code, out, err = _run_git_cmd(["git", "commit", "-m", mensaje], env_extra)
    if code != 0:
        if "nothing to commit" in err.lower():
            st.info("No hay cambios nuevos para commitear.")
        else:
            st.warning(f"No se pudo hacer commit: {err}")
            return

    # git push
    code, out, err = _run_git_cmd(["git", "push", "origin", branch], env_extra)
    if code != 0:
        st.warning(f"No se pudo hacer push automático: {err or out}")
    else:
        st.success("Cambios enviados al repositorio. Streamlit se redeplegará automáticamente.")
