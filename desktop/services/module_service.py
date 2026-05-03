from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path

from app.config import MODULES_DIR_NAME
from app.database import DatabaseService


class ModuleService:
    def __init__(self, database: DatabaseService, workspace_dir: Path, cloudinary=None) -> None:
        self.database = database
        self.workspace_dir = workspace_dir
        self.module_dir = workspace_dir / MODULES_DIR_NAME
        self.cloudinary = cloudinary

    def ensure_storage(self) -> None:
        self.module_dir.mkdir(parents=True, exist_ok=True)

    def add_module(
        self,
        *,
        title: str,
        class_id: int | None,
        subject_id: int | None,
        description: str,
        source_pdf_path: str,
        progress_callback=None,
    ) -> None:
        normalized_title = title.strip()
        if not normalized_title:
            raise ValueError("Judul modul wajib diisi.")
        if not class_id:
            raise ValueError("Kelas wajib dipilih.")
        if not subject_id:
            raise ValueError("Mapel wajib dipilih.")
        source_path = Path(source_pdf_path.strip())
        if not source_path.exists() or source_path.suffix.lower() != ".pdf":
            raise ValueError("Pilih file PDF yang valid.")

        self.ensure_storage()
        self._report_progress(progress_callback, "Menyalin file PDF ke workspace...", 0, 3)
        copied_path = self._copy_pdf(source_path)
        self._report_progress(progress_callback, "Menyalin file PDF ke workspace...", 1, 3)
        extracted_text, page_count = self._extract_text(copied_path, progress_callback=progress_callback)
        self._report_progress(progress_callback, "Mengupload modul ke cloud...", 2, 3)
        cloud_payload = self._upload_to_cloud(copied_path)
        self._report_progress(progress_callback, "Menyimpan data modul...", 3, 3)
        try:
            self.database.execute(
                """
                INSERT INTO learning_modules (
                    title, class_id, subject_id, description, pdf_file_name, pdf_path,
                    extracted_text, page_count, cloudinary_public_id, cloudinary_url,
                    cloudinary_resource_type, upload_status, upload_error
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    normalized_title,
                    class_id,
                    subject_id,
                    description.strip(),
                    copied_path.name,
                    str(copied_path),
                    extracted_text,
                    page_count,
                    cloud_payload["public_id"],
                    cloud_payload["secure_url"],
                    cloud_payload["resource_type"],
                    cloud_payload["upload_status"],
                    cloud_payload["upload_error"],
                ),
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError("Modul tidak dapat disimpan.") from exc

    def update_module(
        self,
        module_id: int,
        *,
        title: str,
        class_id: int | None,
        subject_id: int | None,
        description: str,
        source_pdf_path: str | None = None,
        progress_callback=None,
    ) -> None:
        row = self.get_module_by_id(module_id)
        if not row:
            raise ValueError("Modul tidak ditemukan.")
        normalized_title = title.strip()
        if not normalized_title:
            raise ValueError("Judul modul wajib diisi.")
        if not class_id:
            raise ValueError("Kelas wajib dipilih.")
        if not subject_id:
            raise ValueError("Mapel wajib dipilih.")

        pdf_file_name = row["pdf_file_name"]
        pdf_path = row["pdf_path"]
        extracted_text = row["extracted_text"]
        page_count = row.get("page_count", 0)
        cloud_public_id = row.get("cloudinary_public_id", "")
        cloud_url = row.get("cloudinary_url", "")
        cloud_resource_type = row.get("cloudinary_resource_type", "")
        upload_status = row.get("upload_status", "local_only")
        upload_error = row.get("upload_error", "")
        if source_pdf_path and source_pdf_path.strip():
            source_path = Path(source_pdf_path.strip())
            if not source_path.exists() or source_path.suffix.lower() != ".pdf":
                raise ValueError("File pengganti harus PDF yang valid.")
            self.ensure_storage()
            self._report_progress(progress_callback, "Menyalin file PDF pengganti...", 0, 3)
            copied_path = self._copy_pdf(source_path)
            self._report_progress(progress_callback, "Menyalin file PDF pengganti...", 1, 3)
            extracted_text, page_count = self._extract_text(copied_path, progress_callback=progress_callback)
            old_path = Path(pdf_path)
            if old_path.exists():
                old_path.unlink(missing_ok=True)
            self._delete_from_cloud(cloud_public_id, cloud_resource_type)
            self._report_progress(progress_callback, "Mengupload modul pengganti ke cloud...", 2, 3)
            cloud_payload = self._upload_to_cloud(copied_path)
            pdf_file_name = copied_path.name
            pdf_path = str(copied_path)
            cloud_public_id = cloud_payload["public_id"]
            cloud_url = cloud_payload["secure_url"]
            cloud_resource_type = cloud_payload["resource_type"]
            upload_status = cloud_payload["upload_status"]
            upload_error = cloud_payload["upload_error"]
        self._report_progress(progress_callback, "Menyimpan perubahan modul...", 3, 3)

        self.database.execute(
            """
            UPDATE learning_modules
            SET title = ?, class_id = ?, subject_id = ?, description = ?,
                pdf_file_name = ?, pdf_path = ?, extracted_text = ?, page_count = ?,
                cloudinary_public_id = ?, cloudinary_url = ?, cloudinary_resource_type = ?,
                upload_status = ?, upload_error = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                normalized_title,
                class_id,
                subject_id,
                description.strip(),
                pdf_file_name,
                pdf_path,
                extracted_text,
                page_count,
                cloud_public_id,
                cloud_url,
                cloud_resource_type,
                upload_status,
                upload_error,
                module_id,
            ),
        )

    def delete_module(self, module_id: int) -> None:
        row = self.get_module_by_id(module_id)
        if not row:
            raise ValueError("Modul tidak ditemukan.")
        self.database.execute("DELETE FROM question_generation_requests WHERE module_id = ?", (module_id,))
        self.database.execute("DELETE FROM learning_modules WHERE id = ?", (module_id,))
        self._delete_from_cloud(str(row.get("cloudinary_public_id", "") or ""), str(row.get("cloudinary_resource_type", "") or "image"))
        pdf_path = Path(str(row.get("pdf_path", "") or ""))
        if pdf_path.exists():
            pdf_path.unlink(missing_ok=True)

    def get_modules(
        self,
        keyword: str = "",
        *,
        class_id: int | None = None,
        subject_id: int | None = None,
    ) -> list[dict]:
        clauses = ["m.title LIKE ?"]
        params: list[object] = [f"%{keyword.strip()}%"]
        if class_id:
            clauses.append("m.class_id = ?")
            params.append(class_id)
        if subject_id:
            clauses.append("m.subject_id = ?")
            params.append(subject_id)
        rows = self.database.fetch_all(
            f"""
            SELECT m.*, c.class_name, s.subject_name
            FROM learning_modules m
            JOIN classes c ON c.id = m.class_id
            JOIN subjects s ON s.id = m.subject_id
            WHERE {' AND '.join(clauses)}
            ORDER BY m.created_at DESC, m.id DESC
            """,
            params,
        )
        return [dict(row) for row in rows]

    def get_module_by_id(self, module_id: int) -> dict | None:
        row = self.database.fetch_one(
            """
            SELECT m.*, c.class_name, s.subject_name
            FROM learning_modules m
            JOIN classes c ON c.id = m.class_id
            JOIN subjects s ON s.id = m.subject_id
            WHERE m.id = ?
            """,
            (module_id,),
        )
        return dict(row) if row else None

    def get_module_choices(
        self,
        *,
        class_id: int | None = None,
        subject_id: int | None = None,
    ) -> list[dict]:
        return self.get_modules("", class_id=class_id, subject_id=subject_id)

    def get_module_text(self, module_id: int) -> str:
        row = self.get_module_by_id(module_id)
        if not row:
            raise ValueError("Modul tidak ditemukan.")
        return str(row.get("extracted_text", "") or "")

    def get_module_excerpt(self, module_id: int, limit: int = 1200) -> str:
        text = self.get_module_text(module_id)
        if len(text) <= limit:
            return text
        return text[:limit].rstrip() + "\n..."

    def _copy_pdf(self, source_path: Path) -> Path:
        sanitized_stem = self._slugify(source_path.stem)
        candidate = self.module_dir / f"{sanitized_stem}.pdf"
        counter = 2
        while candidate.exists():
            candidate = self.module_dir / f"{sanitized_stem}_{counter}.pdf"
            counter += 1
        shutil.copy2(source_path, candidate)
        return candidate

    def _extract_text(self, pdf_path: Path, *, progress_callback=None) -> tuple[str, int]:
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise ValueError("Library pypdf belum terpasang. Jalankan install dependency terbaru.") from exc

        try:
            reader = PdfReader(str(pdf_path))
        except Exception as exc:
            raise ValueError("PDF tidak dapat dibaca.") from exc

        total_pages = len(reader.pages)
        pages: list[str] = []
        for index, page in enumerate(reader.pages, start=1):
            self._report_progress(
                progress_callback,
                f"Mengekstrak teks PDF... halaman {index} dari {total_pages}",
                index,
                total_pages,
            )
            try:
                pages.append((page.extract_text() or "").strip())
            except Exception:
                pages.append("")
        extracted_text = "\n\n".join(part for part in pages if part).strip()
        if not extracted_text:
            extracted_text = "Teks PDF tidak berhasil diekstrak. Periksa isi PDF atau gunakan file yang berbasis teks."
        return extracted_text, total_pages

    def _upload_to_cloud(self, pdf_path: Path) -> dict:
        if not self.cloudinary:
            return {
                "public_id": "",
                "secure_url": "",
                "resource_type": "",
                "upload_status": "local_only",
                "upload_error": "",
            }
        if not self.cloudinary.is_configured():
            return {
                "public_id": "",
                "secure_url": "",
                "resource_type": "",
                "upload_status": "local_only",
                "upload_error": "Cloudinary belum dikonfigurasi.",
            }
        try:
            result = self.cloudinary.upload_pdf(pdf_path)
            return {
                "public_id": result["public_id"],
                "secure_url": result["secure_url"],
                "resource_type": result["resource_type"],
                "upload_status": "uploaded",
                "upload_error": "",
            }
        except Exception as exc:
            return {
                "public_id": "",
                "secure_url": "",
                "resource_type": "",
                "upload_status": "upload_failed",
                "upload_error": str(exc),
            }

    def _delete_from_cloud(self, public_id: str, resource_type: str) -> None:
        if self.cloudinary and public_id.strip():
            try:
                self.cloudinary.delete_asset(public_id, resource_type=resource_type or "image")
            except Exception:
                return

    def _slugify(self, value: str) -> str:
        cleaned = "".join(char.lower() if char.isalnum() else "_" for char in value.strip())
        cleaned = "_".join(part for part in cleaned.split("_") if part)
        return cleaned or "modul"

    def _report_progress(self, callback, message: str, current: int | None = None, total: int | None = None) -> None:
        if callback:
            callback(message, current, total)
