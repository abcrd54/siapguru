from __future__ import annotations

from pathlib import Path

from services.admin_api_service import AdminApiService
from services.cloudinary_service import CloudinaryService


class RemoteStorageService:
    def __init__(self, admin_api: AdminApiService, direct_storage: CloudinaryService | None = None) -> None:
        self.admin_api = admin_api
        self.direct_storage = direct_storage or CloudinaryService()

    def is_configured(self) -> bool:
        return self.admin_api.is_configured() or self.direct_storage.is_configured()

    def upload_pdf(self, file_path: str | Path, *, folder: str = "siapguru/modules") -> dict:
        if self.admin_api.is_configured():
            path = Path(file_path)
            response = self.admin_api.post_multipart(
                "/api/desktop/modules/upload-cloud",
                fields={
                    "folder": folder,
                    "module_title": path.stem,
                },
                file_field="file",
                file_path=path,
            )
            data = response.get("data", response)
            if response.get("success", True) is False:
                raise RuntimeError(str(response.get("message") or response.get("error") or "Upload cloud gagal."))
            return {
                "public_id": str(data.get("public_id", "") or ""),
                "secure_url": str(data.get("secure_url", "") or ""),
                "resource_type": str(data.get("resource_type", "") or "auto"),
            }
        return self.direct_storage.upload_pdf(file_path, folder=folder)

    def delete_asset(self, public_id: str, *, resource_type: str = "image") -> None:
        if self.direct_storage and self.direct_storage.is_configured():
            self.direct_storage.delete_asset(public_id, resource_type=resource_type)
            return
        if self.admin_api.is_configured():
            return
        self.direct_storage.delete_asset(public_id, resource_type=resource_type)
