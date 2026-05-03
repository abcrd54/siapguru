from __future__ import annotations

import json
import mimetypes
import uuid
from pathlib import Path
from urllib import error, request

from app.config import ADMIN_API_BASE_URL, ADMIN_API_TIMEOUT, ADMIN_API_TOKEN


class AdminApiService:
    def __init__(self, settings=None) -> None:
        self.settings = settings
        self.active_license_key = ""

    def set_active_license_key(self, license_key: str) -> None:
        self.active_license_key = str(license_key or "").strip()

    def get_base_url(self) -> str:
        if self.settings:
            value = str(self.settings.get_settings().get("admin_api_base_url", "") or "").strip()
            if value:
                return value.rstrip("/")
        return ADMIN_API_BASE_URL.rstrip("/")

    def get_token(self) -> str:
        if self.settings:
            value = str(self.settings.get_settings().get("admin_api_token", "") or "").strip()
            if value:
                return value
        return ADMIN_API_TOKEN

    def is_configured(self) -> bool:
        return bool(self.get_base_url())

    def post_json(self, path: str, payload: dict, *, include_auth: bool = True) -> dict:
        payload = dict(payload)
        if self.active_license_key and "license_key" not in payload:
            payload["license_key"] = self.active_license_key
        url = f"{self.get_base_url()}{path}"
        headers = {"Content-Type": "application/json"}
        token = self.get_token()
        if include_auth and token:
            headers["Authorization"] = f"Bearer {token}"
        req = request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        return self._execute(req)

    def post_multipart(
        self,
        path: str,
        *,
        fields: dict[str, object],
        file_field: str,
        file_path: str | Path,
        include_auth: bool = True,
    ) -> dict:
        fields = dict(fields)
        if self.active_license_key and "license_key" not in fields:
            fields["license_key"] = self.active_license_key
        url = f"{self.get_base_url()}{path}"
        token = self.get_token()
        boundary = f"----SiapGuru{uuid.uuid4().hex}"
        body = self._build_multipart_body(boundary, fields, file_field, Path(file_path))
        headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
        if include_auth and token:
            headers["Authorization"] = f"Bearer {token}"
        req = request.Request(url, data=body, headers=headers, method="POST")
        return self._execute(req)

    def _build_multipart_body(self, boundary: str, fields: dict[str, object], file_field: str, file_path: Path) -> bytes:
        if not file_path.exists():
            raise ValueError("File untuk request multipart tidak ditemukan.")
        chunks: list[bytes] = []
        for key, value in fields.items():
            chunks.extend(
                [
                    f"--{boundary}\r\n".encode("utf-8"),
                    f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode("utf-8"),
                    f"{value}\r\n".encode("utf-8"),
                ]
            )
        mime_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        chunks.extend(
            [
                f"--{boundary}\r\n".encode("utf-8"),
                f'Content-Disposition: form-data; name="{file_field}"; filename="{file_path.name}"\r\n'.encode("utf-8"),
                f"Content-Type: {mime_type}\r\n\r\n".encode("utf-8"),
                file_path.read_bytes(),
                b"\r\n",
                f"--{boundary}--\r\n".encode("utf-8"),
            ]
        )
        return b"".join(chunks)

    def _execute(self, req: request.Request) -> dict:
        try:
            with request.urlopen(req, timeout=ADMIN_API_TIMEOUT) as response:
                raw = response.read().decode("utf-8")
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Admin API error {exc.code}: {detail or exc.reason}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"Koneksi ke Admin API gagal: {exc.reason}") from exc
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError("Respons Admin API bukan JSON yang valid.") from exc
        return payload
