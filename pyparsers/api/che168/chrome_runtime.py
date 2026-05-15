import os
import tempfile


def configure_chromium_runtime_env() -> None:
    """Keep Chromium runtime files out of the container writable layer."""
    os.environ.setdefault("XDG_CONFIG_HOME", "/tmp/.config")
    os.environ.setdefault("XDG_CACHE_HOME", "/tmp/.cache")
    os.makedirs(os.environ["XDG_CONFIG_HOME"], exist_ok=True)
    os.makedirs(os.environ["XDG_CACHE_HOME"], exist_ok=True)


def make_chromium_temp_dir(prefix: str = "che168-chrome-") -> str:
    configure_chromium_runtime_env()
    return tempfile.mkdtemp(prefix=prefix, dir="/tmp")


def add_chromium_runtime_options(chrome_options, temp_dir: str) -> None:
    chrome_options.add_argument(f"--user-data-dir={temp_dir}")
    chrome_options.add_argument(f"--disk-cache-dir={temp_dir}/cache")
    chrome_options.add_argument(f"--crash-dumps-dir={temp_dir}/crashes")
    chrome_options.add_argument("--disable-crash-reporter")
    chrome_options.add_argument("--disable-breakpad")
    chrome_options.add_argument("--disable-features=Crashpad,Breakpad,SendFeedback")
    chrome_options.add_argument("--no-crashpad")
    chrome_options.add_argument("--noerrdialogs")
