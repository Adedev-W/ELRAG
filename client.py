from __future__ import annotations

import argparse
import getpass
import json
import os
import stat
import tempfile
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlsplit, urlunsplit

import httpx
from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parent
DEFAULT_TOKEN_FILE = ".api_token.json"
AUTH_CALLBACK_SUFFIX = "/auth/callback"


class ClientConfigurationError(RuntimeError):
    pass


class TokenFileError(RuntimeError):
    pass


@dataclass(frozen=True)
class ClientConfig:
    base_url: str
    token_path: Path
    timeout_seconds: float


def _base_url_from_redirect_uri(redirect_uri: str) -> str:
    parsed = urlsplit(redirect_uri.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ClientConfigurationError(
            "GOOGLE_REDIRECT_URI must be an absolute http(s) URL"
        )
    if not parsed.path.endswith(AUTH_CALLBACK_SUFFIX):
        raise ClientConfigurationError(
            f"GOOGLE_REDIRECT_URI must end with {AUTH_CALLBACK_SUFFIX}"
        )

    base_path = parsed.path[: -len(AUTH_CALLBACK_SUFFIX)].rstrip("/")
    return urlunsplit((parsed.scheme, parsed.netloc, base_path, "", "")).rstrip("/")


def load_config() -> ClientConfig:
    load_dotenv(ROOT_DIR / ".env")

    base_url = os.getenv("API_BASE_URL")
    if base_url:
        parsed = urlsplit(base_url.strip())
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ClientConfigurationError("API_BASE_URL must be an absolute http(s) URL")
        base_url = base_url.rstrip("/")
    else:
        redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")
        if not redirect_uri:
            raise ClientConfigurationError(
                "Set API_BASE_URL or GOOGLE_REDIRECT_URI in .env"
            )
        base_url = _base_url_from_redirect_uri(redirect_uri)

    token_value = os.getenv("API_TOKEN_FILE", DEFAULT_TOKEN_FILE)
    token_path = Path(token_value).expanduser()
    if not token_path.is_absolute():
        token_path = ROOT_DIR / token_path

    try:
        timeout_seconds = float(os.getenv("API_TEST_TIMEOUT_SECONDS", "30"))
    except ValueError as exc:
        raise ClientConfigurationError(
            "API_TEST_TIMEOUT_SECONDS must be a number"
        ) from exc
    if timeout_seconds <= 0:
        raise ClientConfigurationError("API_TEST_TIMEOUT_SECONDS must be positive")

    return ClientConfig(
        base_url=base_url,
        token_path=token_path,
        timeout_seconds=timeout_seconds,
    )


def _token_payload(raw_value: str) -> dict[str, Any]:
    value = raw_value.strip()
    if value.lower().startswith("bearer "):
        value = value[7:].strip()
    if not value:
        raise TokenFileError("access token cannot be empty")

    if value.startswith("{"):
        try:
            payload = json.loads(value)
        except json.JSONDecodeError as exc:
            raise TokenFileError("pasted OAuth response is not valid JSON") from exc
        if not isinstance(payload, dict) or not payload.get("access_token"):
            raise TokenFileError("OAuth JSON must contain access_token")
        return payload

    return {"access_token": value, "token_type": "bearer"}


class TokenStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def save(self, payload: dict[str, Any]) -> None:
        if not payload.get("access_token"):
            raise TokenFileError("token payload must contain access_token")

        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.path.parent,
                prefix=f".{self.path.name}.",
                suffix=".tmp",
                delete=False,
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)
                json.dump(payload, temporary_file, indent=2)
                temporary_file.write("\n")
                temporary_file.flush()
                os.fchmod(temporary_file.fileno(), stat.S_IRUSR | stat.S_IWUSR)
            os.replace(temporary_path, self.path)
        except OSError as exc:
            raise TokenFileError(f"could not save token file: {self.path}") from exc
        finally:
            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink(missing_ok=True)

    def load(self) -> dict[str, Any]:
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise TokenFileError(
                f"token file not found: {self.path}; run `client.py login` first"
            ) from exc
        except (OSError, json.JSONDecodeError) as exc:
            raise TokenFileError(f"could not read token file: {self.path}") from exc

        if not isinstance(payload, dict) or not payload.get("access_token"):
            raise TokenFileError(f"token file has no access_token: {self.path}")
        return payload


def login(config: ClientConfig, *, open_browser: bool) -> None:
    login_url = f"{config.base_url}/auth/login"
    print(f"Open this URL in the same browser used for Google login:\n{login_url}")
    if open_browser:
        webbrowser.open(login_url)

    raw_value = getpass.getpass(
        "Paste access_token or the full callback JSON (input hidden): "
    )
    TokenStore(config.token_path).save(_token_payload(raw_value))
    print(f"Token saved to {config.token_path}")


@dataclass
class TestResult:
    label: str
    status: str
    detail: str


class ApiTestRunner:
    def __init__(self, config: ClientConfig, token: dict[str, Any], verbose: bool) -> None:
        self.results: list[TestResult] = []
        self.verbose = verbose
        self.client = httpx.Client(
            base_url=config.base_url,
            timeout=config.timeout_seconds,
            headers={
                "Authorization": f"Bearer {token['access_token']}",
                "Accept": "application/json",
            },
        )

    def close(self) -> None:
        self.client.close()

    def skip(self, label: str, detail: str) -> None:
        self.results.append(TestResult(label, "SKIP", detail))
        print(f"[SKIP] {label}: {detail}")

    def request(
        self,
        method: str,
        path: str,
        *,
        label: str | None = None,
        expected: Iterable[int] = (200,),
        **kwargs: Any,
    ) -> httpx.Response | None:
        display_label = label or f"{method.upper()} {path}"
        expected_codes = set(expected)
        try:
            response = self.client.request(method, path, **kwargs)
        except httpx.HTTPError as exc:
            self.results.append(TestResult(display_label, "FAIL", str(exc)))
            print(f"[FAIL] {display_label}: {exc}")
            return None

        detail = str(response.status_code)
        if response.status_code not in expected_codes:
            detail = f"HTTP {response.status_code}: {_response_preview(response)}"
            self.results.append(TestResult(display_label, "FAIL", detail))
            print(f"[FAIL] {display_label}: {detail}")
            return response

        self.results.append(TestResult(display_label, "PASS", detail))
        print(f"[PASS] {display_label}: HTTP {response.status_code}")
        if self.verbose:
            print(f"       {_response_preview(response)}")
        return response

    def summary(self) -> int:
        counts = {status: sum(result.status == status for result in self.results) for status in ("PASS", "SKIP", "FAIL")}
        print(
            f"\nSummary: {counts['PASS']} passed, "
            f"{counts['SKIP']} skipped, {counts['FAIL']} failed"
        )
        return 1 if counts["FAIL"] else 0


def _response_preview(response: httpx.Response) -> str:
    try:
        value = response.json()
        text = json.dumps(value, ensure_ascii=True, default=str)
    except (ValueError, json.JSONDecodeError):
        text = response.text
    return text[:400].replace("\n", " ")


def _fixture_path(value: str) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else ROOT_DIR / path


def run_smoke(runner: ApiTestRunner) -> None:
    runner.request("GET", "/auth/me", label="GET /auth/me")
    runner.request("GET", "/gcs/files", label="GET /gcs/files")

    blob_name = os.getenv("API_TEST_BLOB_NAME")
    if blob_name:
        runner.request("GET", "/gcs/files/info", params={"blob_name": blob_name})
        runner.request("GET", "/gcs/files/download", params={"blob_name": blob_name})
    else:
        runner.skip("GCS info/download", "set API_TEST_BLOB_NAME")

    document_id = os.getenv("API_TEST_DOCUMENT_ID")
    if document_id:
        runner.request("GET", f"/docs/documentai/{document_id}")
    else:
        runner.skip("GET document AI response", "set API_TEST_DOCUMENT_ID")

    vision_id = os.getenv("API_TEST_VISION_ID")
    if vision_id:
        runner.request("GET", f"/vision/{vision_id}")
    else:
        runner.skip("GET vision response", "set API_TEST_VISION_ID")


def run_all(runner: ApiTestRunner) -> None:
    run_smoke(runner)

    test_file = _fixture_path(os.getenv("API_TEST_FILE", "SAMPLE_OCR.pdf"))
    blob_name = os.getenv("API_TEST_BLOB_NAME", f"uploads/{test_file.name}")
    gcs_uri = os.getenv("API_TEST_GCS_URI")
    if not test_file.is_file():
        runner.skip("write/provider suite", f"fixture not found: {test_file}")
    else:
        with test_file.open("rb") as file_handle:
            upload_response = runner.request(
                "POST",
                "/gcs/upload",
                files={
                    "file": (
                        test_file.name,
                        file_handle,
                        "application/pdf" if test_file.suffix.lower() == ".pdf" else "application/octet-stream",
                    )
                },
            )
        if upload_response is not None and upload_response.is_success:
            gcs_uri = gcs_uri or _gcs_uri_from_env(blob_name)
            runner.request("GET", "/gcs/files/info", params={"blob_name": blob_name})
            runner.request("GET", "/gcs/files/download", params={"blob_name": blob_name})

        with test_file.open("rb") as file_handle:
            document_response = runner.request(
                "POST",
                "/docs/documentai/bytes",
                files={"file": (test_file.name, file_handle, "application/pdf")},
            )
        if document_response is not None and document_response.is_success:
            document_id = _json_value(document_response, "id")
            if document_id:
                runner.request("GET", f"/docs/documentai/{document_id}")

        if gcs_uri:
            runner.request("POST", "/docs/documentai/gcs", params={"gcs_uri": gcs_uri})
        else:
            runner.skip("POST document AI GCS", "set GCS_BUCKET or API_TEST_GCS_URI")

    vision_file_value = os.getenv("API_TEST_VISION_FILE")
    if not vision_file_value:
        runner.skip("Vision provider suite", "set API_TEST_VISION_FILE")
    else:
        vision_file = _fixture_path(vision_file_value)
        if not vision_file.is_file():
            runner.skip("Vision provider suite", f"fixture not found: {vision_file}")
        else:
            with vision_file.open("rb") as file_handle:
                vision_response = runner.request(
                    "POST",
                    "/vision/vision",
                    files={"files": (vision_file.name, file_handle, "application/octet-stream")},
                )
            if vision_response is not None and vision_response.is_success:
                vision_id = _json_value(vision_response, "id")
                if vision_id:
                    runner.request("GET", f"/vision/{vision_id}")
            if gcs_uri:
                runner.request("POST", "/vision/vision-gcs", params={"gcs_uri": gcs_uri})

    agent_message = os.getenv("API_TEST_AGENT_MESSAGE")
    if agent_message:
        runner.request(
            "POST",
            "/agent/run",
            json={"message": agent_message, "stream": False},
        )
    else:
        runner.skip("POST agent run", "set API_TEST_AGENT_MESSAGE")


def _gcs_uri_from_env(blob_name: str) -> str | None:
    bucket = os.getenv("GCS_BUCKET")
    return f"gs://{bucket}/{blob_name}" if bucket else None


def _json_value(response: httpx.Response, key: str) -> Any:
    try:
        return response.json().get(key)
    except (AttributeError, ValueError, json.JSONDecodeError):
        return None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Protected ELRAG API test client")
    subparsers = parser.add_subparsers(dest="command", required=True)

    login_parser = subparsers.add_parser("login", help="login through Google OAuth and save token")
    login_parser.add_argument(
        "--no-browser",
        action="store_true",
        help="print the login URL without opening a browser",
    )

    for command, help_text in (
        ("smoke", "run read-only protected API checks"),
        ("run-all", "run protected checks including write/provider APIs"),
    ):
        command_parser = subparsers.add_parser(command, help=help_text)
        command_parser.add_argument("--verbose", action="store_true")

    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        config = load_config()
        if args.command == "login":
            login(config, open_browser=not args.no_browser)
            return 0

        token = TokenStore(config.token_path).load()
        runner = ApiTestRunner(config, token, verbose=args.verbose)
        try:
            if args.command == "smoke":
                run_smoke(runner)
            else:
                run_all(runner)
            return runner.summary()
        finally:
            runner.close()
    except (ClientConfigurationError, TokenFileError) as exc:
        print(f"Configuration error: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
