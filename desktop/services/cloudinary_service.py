from __future__ import annotations

from pathlib import Path

from app.config import CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET, CLOUDINARY_CLOUD_NAME, CLOUDINARY_URL


class CloudinaryService:
    def __init__(self) -> None:
        self._configured = False
        self._library_available = True
        self._configure()

    def _configure(self) -> None:
        if not any([CLOUDINARY_URL, CLOUDINARY_CLOUD_NAME]):
            return
        try:
            import cloudinary
        except ImportError as exc:
            self._library_available = False
            return

        if CLOUDINARY_URL:
            cloudinary.config(cloudinary_url=CLOUDINARY_URL, secure=True)
            self._configured = True
            return
        if CLOUDINARY_CLOUD_NAME and CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET:
            cloudinary.config(
                cloud_name=CLOUDINARY_CLOUD_NAME,
                api_key=CLOUDINARY_API_KEY,
                api_secret=CLOUDINARY_API_SECRET,
                secure=True,
            )
            self._configured = True

    def is_configured(self) -> bool:
        return self._configured

    def upload_pdf(self, file_path: str | Path, *, folder: str = "siapguru/modules") -> dict:
        if not self._library_available:
            raise RuntimeError("Library cloudinary belum terpasang.")
        if not self._configured:
            raise RuntimeError("Konfigurasi Cloudinary belum diisi.")
        try:
            import cloudinary.uploader
        except ImportError as exc:
            raise RuntimeError("Library cloudinary belum terpasang.") from exc

        path = Path(file_path)
        if not path.exists():
            raise ValueError("File modul tidak ditemukan untuk upload cloud.")
        result = cloudinary.uploader.upload(
            str(path),
            folder=folder,
            resource_type="image",
            use_filename=True,
            unique_filename=True,
            overwrite=False,
        )
        return {
            "public_id": str(result.get("public_id", "") or ""),
            "secure_url": str(result.get("secure_url", "") or ""),
            "resource_type": str(result.get("resource_type", "") or "image"),
        }

    def delete_asset(self, public_id: str, *, resource_type: str = "image") -> None:
        if not self._configured or not public_id.strip():
            return
        try:
            import cloudinary.uploader
        except ImportError:
            return
        cloudinary.uploader.destroy(public_id.strip(), resource_type=resource_type, invalidate=True)
