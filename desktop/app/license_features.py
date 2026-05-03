from __future__ import annotations


def normalize_features(raw_features: object) -> dict[str, bool]:
    if not isinstance(raw_features, dict):
        return {}
    return {str(key): bool(value) for key, value in raw_features.items()}


def has_feature(raw_features: object, *keys: str, default: bool = True) -> bool:
    features = normalize_features(raw_features)
    matched = [key for key in keys if key in features]
    if not matched:
        return default
    return any(features[key] for key in matched)


def page_enabled(raw_features: object, page_name: str) -> bool:
    page_map = {
        "Beranda": ("dashboard", "guru"),
        "Data Siswa": ("students", "reports", "guru"),
        "Data Kelas": ("classes", "reports", "guru"),
        "Mata Pelajaran": ("subjects", "reports", "guru"),
        "Nilai": ("grades", "reports", "guru"),
        "Katrol Nilai": ("nilai_katrol", "reports", "guru"),
        "Buat Raport": ("reports", "guru"),
        "Unduh Laporan": ("reports", "export_pdf", "guru"),
        "Modul": ("modules", "guru"),
        "Soal": ("questions", "ai_question_generation", "guru"),
        "Backup": ("backup", "database_local", "guru"),
        "Pengaturan": ("settings", "guru"),
    }
    keys = page_map.get(page_name)
    if not keys:
        return True
    return has_feature(raw_features, *keys, default=True)
