from __future__ import annotations

import json
from urllib import error, request

from app.config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, OPENROUTER_MODEL
from services.admin_api_service import AdminApiService


class AIService:
    def __init__(self, admin_api: AdminApiService | None = None) -> None:
        self.base_url = OPENROUTER_BASE_URL.rstrip("/")
        self.api_key = OPENROUTER_API_KEY
        self.model = OPENROUTER_MODEL
        self.admin_api = admin_api

    def is_configured(self) -> bool:
        return bool((self.admin_api and self.admin_api.is_configured()) or (self.api_key and self.model))

    def generate_questions(self, prompt: str, *, metadata: dict | None = None) -> dict:
        if self.admin_api and self.admin_api.is_configured():
            payload = {"prompt_text": prompt}
            if metadata:
                payload.update(metadata)
            response = self.admin_api.post_json("/api/desktop/ai/generate-questions", payload)
            if response.get("success", True) is False:
                raise RuntimeError(str(response.get("message", "Generate soal melalui Admin API gagal.")))
            data = response.get("data", response)
            if "response_json" in data:
                parsed_json = data.get("response_json")
            else:
                raw_text = str(data.get("response_text", "") or data.get("content", "") or "")
                parsed_json = self._parse_response_json(raw_text)
            return {
                "provider": str(data.get("provider", "admin_api")),
                "model_name": str(data.get("model", data.get("model_name", "admin-managed"))),
                "response_text": json.dumps(parsed_json, ensure_ascii=False, indent=2),
                "response_json": parsed_json,
                "remote_result_id": str(data.get("id", data.get("result_id", "")) or ""),
                "raw_response": json.dumps(data, ensure_ascii=False),
            }
        if not self.is_configured():
            raise RuntimeError("Layanan generate soal belum dikonfigurasi.")
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "Anda adalah asisten guru yang menghasilkan soal dari materi pembelajaran secara akurat, rapi, dan konsisten.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            "temperature": 0.4,
        }
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            f"{self.base_url}/chat/completions",
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://siapguru.local",
                "X-Title": "SiapGuru",
            },
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=120) as response:
                raw = response.read().decode("utf-8")
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Layanan generate soal error {exc.code}: {detail or exc.reason}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"Koneksi ke layanan generate soal gagal: {exc.reason}") from exc

        parsed = json.loads(raw)
        choices = parsed.get("choices") or []
        if not choices:
            raise RuntimeError("Respons OpenRouter tidak berisi pilihan jawaban.")
        message = choices[0].get("message") or {}
        content = str(message.get("content", "") or "").strip()
        if not content:
            raise RuntimeError("Respons generator soal kosong.")
        parsed_json = self._parse_response_json(content)
        return {
            "provider": "generator_soal",
            "model_name": self.model,
            "response_text": json.dumps(parsed_json, ensure_ascii=False, indent=2),
            "response_json": parsed_json,
            "remote_result_id": "",
            "raw_response": raw,
        }

    def _parse_response_json(self, content: str):
        cleaned = content.strip()
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            if len(lines) >= 3:
                cleaned = "\n".join(lines[1:-1]).strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        for opener, closer in (("{", "}"), ("[", "]")):
            start = cleaned.find(opener)
            end = cleaned.rfind(closer)
            if start >= 0 and end > start:
                candidate = cleaned[start : end + 1]
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    continue
        raise RuntimeError("Respons generator soal bukan JSON yang valid.")
