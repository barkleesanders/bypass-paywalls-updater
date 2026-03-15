#!/usr/bin/env python3
"""
Bypass Paywalls Chrome Clean Updater

Checks for updates to the Bypass Paywalls Chrome Clean extension by comparing
ETag/Last-Modified headers (with Content-Length as fallback). Downloads the new
version when a change is detected.

Configuration via environment variables:
    BPC_DOWNLOAD_DIR    - where to save the ZIP (default: ~/Downloads)
    BPC_STATE_FILE      - path to state JSON  (default: ~/.bpc_updater_state.json)
    BPC_NOTIFY          - set to "1" to enable macOS desktop notifications
"""

import argparse
import json
import logging
import os
import platform
import subprocess
import sys
import time
import zipfile

import requests

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DOWNLOAD_URL = (
    "https://gitflic.ru/project/magnolia1234/bpc_uploads"
    "/blob/raw?file=bypass-paywalls-chrome-clean-master.zip"
)
EXTENSION_FILENAME = "bypass-paywalls-chrome-clean-master.zip"

DEFAULT_DOWNLOAD_DIR = os.path.expanduser("~/Downloads")
DEFAULT_STATE_FILE = os.path.expanduser("~/.bpc_updater_state.json")

MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2  # seconds; doubles each attempt

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

log = logging.getLogger("bpc-updater")


def _setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    log.setLevel(level)
    log.addHandler(handler)


# ---------------------------------------------------------------------------
# Desktop notifications (macOS only)
# ---------------------------------------------------------------------------


def _notify(title: str, message: str) -> None:
    """Send a macOS desktop notification via osascript. Fails silently."""
    if platform.system() != "Darwin":
        log.debug("Notifications only supported on macOS; skipping.")
        return
    try:
        script = (
            f'display notification "{message}" with title "{title}"'
        )
        subprocess.run(
            ["osascript", "-e", script],
            check=False,
            capture_output=True,
            timeout=5,
        )
    except Exception:
        log.debug("Desktop notification failed (non-critical).")


# ---------------------------------------------------------------------------
# State file helpers
# ---------------------------------------------------------------------------


def _load_state(path: str) -> dict:
    """Load the JSON state file.  Returns empty dict on any error."""
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r") as fh:
            data = json.load(fh)
            if isinstance(data, dict):
                return data
    except (json.JSONDecodeError, OSError) as exc:
        log.warning("Corrupt state file (%s); starting fresh.", exc)
    # Migrate legacy formats
    try:
        with open(path, "r") as fh:
            raw = fh.read().strip()
        # Format 1: plain integer (original script)
        try:
            return {"content_length": int(raw)}
        except ValueError:
            pass
        # Format 2: key=value lines (e.g. content_length=262232)
        result: dict = {}
        for line in raw.splitlines():
            if "=" not in line:
                continue
            key, _, val = line.partition("=")
            key, val = key.strip(), val.strip()
            if not val:
                continue
            if key == "content_length":
                try:
                    result["content_length"] = int(val)
                except ValueError:
                    pass
            elif key == "etag":
                result["etag"] = val
            elif key in ("lastmod", "last_modified"):
                result["last_modified"] = val
        if result:
            return result
    except OSError:
        pass
    return {}


def _save_state(path: str, state: dict) -> None:
    state["last_check"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    tmp = path + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(state, fh, indent=2)
    os.replace(tmp, path)
    log.debug("State saved to %s", path)


# ---------------------------------------------------------------------------
# Also migrate the old dotfile if the new state file doesn't exist yet
# ---------------------------------------------------------------------------

OLD_STATE_FILE = os.path.expanduser("~/.last_content_length_bypass_paywalls")


def _maybe_migrate_legacy_state(new_path: str) -> dict:
    """One-time migration from the old plain-text state file."""
    if os.path.exists(new_path):
        return _load_state(new_path)
    if os.path.exists(OLD_STATE_FILE):
        log.info("Migrating legacy state file %s -> %s", OLD_STATE_FILE, new_path)
        state = _load_state(OLD_STATE_FILE)
        if state:
            _save_state(new_path, state)
        return state
    return {}


# ---------------------------------------------------------------------------
# HTTP helpers with retry
# ---------------------------------------------------------------------------


def _request_with_retry(method: str, url: str, **kwargs) -> requests.Response:
    """Make an HTTP request with exponential-backoff retry."""
    last_exc = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.request(method, url, allow_redirects=True, **kwargs)
            resp.raise_for_status()
            return resp
        except requests.exceptions.RequestException as exc:
            last_exc = exc
            if attempt < MAX_RETRIES:
                wait = RETRY_BACKOFF_BASE ** attempt
                log.warning(
                    "Attempt %d/%d failed (%s). Retrying in %ds...",
                    attempt, MAX_RETRIES, exc, wait,
                )
                time.sleep(wait)
            else:
                log.error("All %d attempts failed.", MAX_RETRIES)
    raise last_exc  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Change detection
# ---------------------------------------------------------------------------


def _has_changed(headers: dict, state: dict) -> bool:
    """Compare response headers against saved state.

    Priority: ETag > Last-Modified > Content-Length.
    Returns True if a change is detected (or if no prior state exists).
    """
    # ETag is the most reliable indicator
    remote_etag = headers.get("ETag")
    if remote_etag:
        saved_etag = state.get("etag")
        if saved_etag and saved_etag == remote_etag:
            log.debug("ETag unchanged: %s", remote_etag)
            return False
        if saved_etag:
            log.info("ETag changed: %s -> %s", saved_etag, remote_etag)
            return True
        # No saved ETag yet -- fall through to other checks

    # Last-Modified
    remote_lm = headers.get("Last-Modified")
    if remote_lm:
        saved_lm = state.get("last_modified")
        if saved_lm and saved_lm == remote_lm:
            log.debug("Last-Modified unchanged: %s", remote_lm)
            return False
        if saved_lm:
            log.info("Last-Modified changed: %s -> %s", saved_lm, remote_lm)
            return True

    # Content-Length fallback
    remote_cl = headers.get("Content-Length")
    if remote_cl:
        try:
            remote_cl_int = int(remote_cl)
        except ValueError:
            remote_cl_int = 0
        saved_cl = state.get("content_length", 0)
        if saved_cl and remote_cl_int == saved_cl:
            log.debug("Content-Length unchanged: %d", remote_cl_int)
            return False
        if saved_cl:
            log.info("Content-Length changed: %d -> %d", saved_cl, remote_cl_int)
            return True

    # No prior state or no usable headers -- treat as changed
    if not state:
        log.info("No prior state found; treating as new.")
    else:
        log.info("No matching header found for comparison; treating as changed.")
    return True


def _build_state_from_headers(headers: dict) -> dict:
    """Extract cacheable header values into a state dict."""
    result: dict = {}
    if headers.get("ETag"):
        result["etag"] = headers["ETag"]
    if headers.get("Last-Modified"):
        result["last_modified"] = headers["Last-Modified"]
    cl = headers.get("Content-Length")
    if cl:
        try:
            result["content_length"] = int(cl)
        except ValueError:
            pass
    return result


# ---------------------------------------------------------------------------
# ZIP validation
# ---------------------------------------------------------------------------


def _verify_zip(path: str) -> bool:
    """Return True if *path* is a valid ZIP archive."""
    try:
        with zipfile.ZipFile(path, "r") as zf:
            bad = zf.testzip()
            if bad is not None:
                log.error("Corrupt entry in ZIP: %s", bad)
                return False
        return True
    except zipfile.BadZipFile:
        log.error("Downloaded file is not a valid ZIP archive.")
        return False
    except Exception as exc:
        log.error("ZIP verification failed: %s", exc)
        return False


# ---------------------------------------------------------------------------
# Main logic
# ---------------------------------------------------------------------------


def check_for_updates(
    download_dir: str,
    state_file: str,
    force: bool = False,
    dry_run: bool = False,
    notify: bool = False,
) -> None:
    log.info("Checking for updates to Bypass Paywalls Chrome Clean...")

    # -- HEAD request to get headers ------------------------------------------
    head_resp = _request_with_retry("HEAD", DOWNLOAD_URL, timeout=10)
    remote_headers = head_resp.headers
    log.debug("Remote headers: %s", dict(remote_headers))

    # -- Load state & detect change -------------------------------------------
    state = _maybe_migrate_legacy_state(state_file)

    if force:
        log.info("--force flag set; skipping change detection.")
        changed = True
    else:
        changed = _has_changed(remote_headers, state)

    if not changed:
        log.info("No new version found.")
        return

    # -- Download --------------------------------------------------------------
    download_path = os.path.join(download_dir, EXTENSION_FILENAME)

    if dry_run:
        log.info("[dry-run] Would download to: %s", download_path)
        return

    log.info("New version detected! Downloading %s...", EXTENSION_FILENAME)
    os.makedirs(download_dir, exist_ok=True)

    dl_resp = _request_with_retry("GET", DOWNLOAD_URL, stream=True, timeout=60)

    tmp_path = download_path + ".part"
    try:
        with open(tmp_path, "wb") as fh:
            for chunk in dl_resp.iter_content(chunk_size=8192):
                fh.write(chunk)

        # -- Verify integrity --------------------------------------------------
        if not _verify_zip(tmp_path):
            log.error("Integrity check failed. Removing bad download.")
            os.remove(tmp_path)
            return

        os.replace(tmp_path, download_path)
    except BaseException:
        # Clean up partial download on any failure (including KeyboardInterrupt)
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise

    log.info("Downloaded to: %s", download_path)
    log.info(
        "Please manually install the updated .zip file into Chrome "
        "via chrome://extensions (drag and drop)."
    )

    # -- Persist state ---------------------------------------------------------
    new_state = _build_state_from_headers(remote_headers)
    _save_state(state_file, new_state)
    log.info("State updated.")

    # -- Optional desktop notification ----------------------------------------
    if notify:
        _notify(
            "Bypass Paywalls Updated",
            "A new version was downloaded to your Downloads folder.",
        )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check for and download Bypass Paywalls Chrome Clean updates.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Skip change detection and download regardless.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Check for changes but do not download.",
    )
    parser.add_argument(
        "--download-dir",
        default=os.environ.get("BPC_DOWNLOAD_DIR", DEFAULT_DOWNLOAD_DIR),
        help="Directory to save the downloaded ZIP (default: ~/Downloads).",
    )
    parser.add_argument(
        "--state-file",
        default=os.environ.get("BPC_STATE_FILE", DEFAULT_STATE_FILE),
        help="Path to the JSON state file (default: ~/.bpc_updater_state.json).",
    )
    parser.add_argument(
        "--notify",
        action="store_true",
        default=os.environ.get("BPC_NOTIFY", "") == "1",
        help="Send a macOS desktop notification on successful download.",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable debug-level logging.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    _setup_logging(verbose=args.verbose)

    try:
        check_for_updates(
            download_dir=args.download_dir,
            state_file=args.state_file,
            force=args.force,
            dry_run=args.dry_run,
            notify=args.notify,
        )
    except requests.exceptions.RequestException as exc:
        log.error("Network error: %s", exc)
        sys.exit(1)
    except Exception as exc:
        log.error("Unexpected error: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
