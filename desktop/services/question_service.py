from __future__ import annotations

import json

from app.database import DatabaseService
from services.module_service import ModuleService


class QuestionService:
    def __init__(self, database: DatabaseService, modules: ModuleService, ai_service=None) -> None:
        self.database = database
        self.modules = modules
        self.ai_service = ai_service

    def create_prompt(
        self,
        *,
        module_id: int | None,
        class_id: int | None,
        subject_id: int | None,
        question_count: int,
        question_type: str,
        choice_count: int,
    ) -> str:
        if not module_id:
            raise ValueError("Modul wajib dipilih.")
        if not class_id:
            raise ValueError("Kelas wajib dipilih.")
        if not subject_id:
            raise ValueError("Mapel wajib dipilih.")
        if question_count < 1 or question_count > 50:
            raise ValueError("Jumlah soal harus 1 - 50.")
        normalized_type = question_type.strip().lower()
        if normalized_type not in {"pilihan_ganda", "essay"}:
            raise ValueError("Tipe soal tidak valid.")
        if normalized_type == "pilihan_ganda" and (choice_count < 2 or choice_count > 8):
            raise ValueError("Jumlah pilihan jawaban harus 2 - 8.")

        module = self.modules.get_module_by_id(module_id)
        if not module:
            raise ValueError("Modul tidak ditemukan.")
        if int(module["class_id"]) != int(class_id) or int(module["subject_id"]) != int(subject_id):
            raise ValueError("Modul yang dipilih harus sesuai dengan kelas dan mapel.")

        text = self.modules.get_module_text(module_id).strip()
        if not text:
            raise ValueError("Teks modul kosong. Upload modul PDF terlebih dahulu.")

        option_labels = ", ".join(chr(65 + index) for index in range(choice_count)) if normalized_type == "pilihan_ganda" else ""
        prompt_lines = [
            "Anda adalah asisten guru yang membantu menyusun soal dari modul pembelajaran.",
            f"Kelas: {module['class_name']}",
            f"Mata pelajaran: {module['subject_name']}",
            f"Judul modul: {module['title']}",
            "",
            f"Buat {question_count} soal berdasarkan isi modul saja.",
            f"Tipe soal yang diminta adalah {'pilihan ganda' if normalized_type == 'pilihan_ganda' else 'essay'}.",
            "Gunakan bahasa Indonesia yang jelas dan sesuai level siswa.",
            "Jangan menambahkan materi di luar modul.",
            "Pastikan setiap soal menguji pemahaman, bukan sekadar menyalin kalimat mentah.",
        ]
        if normalized_type == "pilihan_ganda":
            prompt_lines.extend(
                [
                    f"Setiap soal harus punya {choice_count} opsi jawaban dengan label {option_labels}.",
                    "Berikan satu jawaban benar.",
                    "Sertakan pembahasan singkat untuk guru.",
                    "Acak posisi jawaban benar.",
                ]
            )
        else:
            prompt_lines.extend(
                [
                    "Sertakan poin jawaban inti atau rubrik singkat untuk setiap soal.",
                ]
            )

        prompt_lines.extend(
            [
                "",
                "Keluarkan hasil hanya dalam JSON yang valid tanpa penjelasan tambahan.",
                "Untuk pilihan ganda, gunakan struktur berikut:",
                '{"questions":[{"number":1,"type":"pilihan_ganda","question":"...","options":{"A":"...","B":"..."},"answer":"A","explanation":"..."}]}',
                "Untuk essay, gunakan struktur berikut:",
                '{"questions":[{"number":1,"type":"essay","question":"...","key_points":["...","..."],"rubric":"..."}]}',
                "",
                "Gunakan isi modul berikut sebagai satu-satunya sumber:",
                text,
            ]
        )
        return "\n".join(prompt_lines).strip()

    def save_generation_request(
        self,
        *,
        module_id: int | None,
        class_id: int | None,
        subject_id: int | None,
        question_count: int,
        question_type: str,
        choice_count: int,
    ) -> None:
        prompt_text = self.create_prompt(
            module_id=module_id,
            class_id=class_id,
            subject_id=subject_id,
            question_count=question_count,
            question_type=question_type,
            choice_count=choice_count,
        )
        self.database.execute(
            """
            INSERT INTO question_generation_requests (
                module_id, class_id, subject_id, question_type, question_count,
                choice_count, prompt_text, status, provider, model_name,
                response_text, generation_status, error_message,
                remote_result_id, remote_sync_status, remote_sync_error
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 'draft', 'generator_soal', '', '', 'draft', '', '', 'local_only', '')
            """,
            (
                module_id,
                class_id,
                subject_id,
                question_type,
                question_count,
                choice_count,
                prompt_text.strip(),
            ),
        )

    def generate_with_ai(
        self,
        *,
        module_id: int | None,
        class_id: int | None,
        subject_id: int | None,
        question_count: int,
        question_type: str,
        choice_count: int,
    ) -> dict:
        module = self.modules.get_module_by_id(module_id) if module_id else None
        if not module:
            raise ValueError("Modul tidak ditemukan.")
        prompt = self.create_prompt(
            module_id=module_id,
            class_id=class_id,
            subject_id=subject_id,
            question_count=question_count,
            question_type=question_type,
            choice_count=choice_count,
        )
        if not self.ai_service:
            raise RuntimeError("Service AI belum tersedia.")
        result = self.ai_service.generate_questions(
            prompt,
            metadata={
                "module_id": module_id,
                "class_id": class_id,
                "subject_id": subject_id,
                "question_count": question_count,
                "question_type": question_type,
                "choice_count": choice_count,
                "module_title": module.get("title", ""),
                "class_name": module.get("class_name", ""),
                "subject_name": module.get("subject_name", ""),
            },
        )
        response_json = result.get("response_json")
        generated_output = (
            json.dumps(response_json, ensure_ascii=False)
            if response_json is not None
            else str(result.get("response_text", "") or "").strip()
        )
        remote_result_id = str(result.get("remote_result_id", "") or result.get("id", "") or "")
        remote_sync_status = "synced" if remote_result_id else "local_only"
        remote_sync_error = str(result.get("remote_sync_error", "") or "")
        request_id = self.database.execute(
            """
            INSERT INTO question_generation_requests (
                module_id, class_id, subject_id, question_type, question_count, choice_count,
                prompt_text, generated_output, status, provider, model_name,
                response_text, generation_status, error_message,
                remote_result_id, remote_sync_status, remote_sync_error
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'generated', ?, ?, ?, 'success', '', ?, ?, ?)
            """,
            (
                module_id,
                class_id,
                subject_id,
                question_type,
                question_count,
                choice_count,
                prompt,
                generated_output,
                result["provider"],
                result["model_name"],
                result["raw_response"],
                remote_result_id,
                remote_sync_status,
                remote_sync_error,
            ),
        )
        result["prompt_text"] = prompt
        result["request_id"] = request_id
        return result

    def get_requests(self) -> list[dict]:
        rows = self.database.fetch_all(
            """
            SELECT q.*, m.title AS module_title, c.class_name, s.subject_name
            FROM question_generation_requests q
            LEFT JOIN learning_modules m ON m.id = q.module_id
            JOIN classes c ON c.id = q.class_id
            JOIN subjects s ON s.id = q.subject_id
            ORDER BY q.created_at DESC, q.id DESC
            """
        )
        return [dict(row) for row in rows]
