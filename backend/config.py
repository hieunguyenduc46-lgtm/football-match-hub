"""
Đọc cấu hình từ file .env (hoặc biến môi trường).
Logic: nếu không có API key -> tự bật chế độ mock để app vẫn chạy được.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    api_football_key: str = ""
    api_football_host: str = "v3.football.api-sports.io"
    # "direct" = đăng ký dashboard api-sports.io (header x-apisports-key)
    # "rapidapi" = đăng ký qua RapidAPI (header x-rapidapi-key)
    api_football_via: str = "direct"
    season: int = 2025
    use_mock: bool = True
    # CORS: 1 hoặc nhiều origin, cách nhau bằng dấu phẩy (cho lúc deploy)
    frontend_origin: str = "http://localhost:5173"
    cache_ttl_seconds: int = 300

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()

# An toàn: chưa có key thì luôn dùng mock, tránh gọi API lỗi 401.
if not settings.api_football_key:
    settings.use_mock = True


# Mùa của từng giải khác với mùa mặc định. World Cup 2026 nằm ở season 2026,
# còn các giải VĐQG (mùa 2025/26) dùng season mặc định (2025).
LEAGUE_SEASON = {
    1: 2026,   # World Cup 2026
    2: 2025,   # Champions League 2025/26
    253: 2026, # MLS (chạy theo năm dương lịch)
}

# Giải chạy theo NĂM DƯƠNG LỊCH (tháng 1–12): season = đúng năm của ngày.
# Khác với giải châu Âu (tháng 8–5): season = năm trước nếu tháng < 7.
# Dùng cho việc tự suy season ở endpoint /fixtures.
CALENDAR_YEAR_LEAGUES = {253}  # MLS


def season_for(league):
    """Trả season đúng cho 1 giải; không có trong map thì dùng SEASON mặc định."""
    try:
        return LEAGUE_SEASON.get(int(league), settings.season)
    except (TypeError, ValueError):
        return settings.season


# ===== Mốc bàn thắng OFFICIAL (nhập tay) =====
# Vì không API miễn phí nào trả đúng con số official đang chạy, ta neo 1 con số official
# tính ĐẾN HẾT mùa `through`, rồi app TỰ CỘNG thêm bàn chính thức từ các mùa SAU đó (qua API).
# => Mỗi năm chỉ cần cập nhật 1 lần sau khi mùa kết thúc; bàn trong mùa hiện tại tự cộng.
#
# player_id: lấy từ URL trang cầu thủ (vd /player/874 -> 874).
# goals: tổng bàn official tính đến hết mùa `through` (tra Wikipedia/官 nguồn bạn tin tưởng).
# through: số mùa cuối ĐÃ neo (vd 2024 = đã tính hết mùa 2024/25).
CAREER_BASELINE = {
    # Cristiano Ronaldo — chỉnh tay để TỔNG hiện tại = 973 (official, tính theo nguồn tin cậy).
    # Cơ chế: total = goals + bàn các mùa SAU `through` (API tự cộng). Mùa hiện tại (2025) API
    # đang cộng 42 bàn, nên đặt baseline 931 để 931 + 42 = 973. Có bàn mới -> API tự cập nhật tiếp.
    874: {"goals": 931, "through": 2024},
    # Lionel Messi (id 154) — neo cứng 907 bàn official (Barça 672 + PSG 32 + Inter Miami 81 +
    # Argentina 115), tính đến ~05/2026 (đạt mốc 900 ngày 18/03/2026). Nguồn: Wikipedia/beIN/ESPN.
    # API-Football tự cộng chỉ ra 830 vì dữ liệu các mùa cũ (2004–2015) bị thiếu -> neo tay cho chuẩn.
    # `through` đặt cao (2026) để KHÔNG cộng thêm mùa nào -> hiển thị đúng 907; ghi thêm bàn thì
    # tăng số này lên (mỗi vài tháng cập nhật 1 lần), giống cách làm với Ronaldo.
    154: {"goals": 907, "through": 2026},
    # Neymar (id 276) — 491 bàn official (Santos/Barça/PSG/Al-Hilal + Brazil), tính ~06/2026.
    # Nguồn: Wikipedia/FotMob. (Đã trở lại Santos đầu 2026.)
    276: {"goals": 491, "through": 2026},
    # Karim Benzema (id 759) — vượt mốc 500 bàn ngày 30/08/2025; ước ~515 tính tới ~06/2026
    # (Lyon/Real Madrid/Al-Ittihad + France). Nguồn: Wikipedia/StatMuse. *Số ước lượng, chỉnh tay nếu cần.
    759: {"goals": 515, "through": 2026},
    # Kylian Mbappé (id 278) — chạm mốc 400 bàn ngày 13/11/2025 (CLB 345: Monaco 27 + PSG 256 +
    # Real 62; Pháp 55). Sau đó đá nốt mùa 25/26 (riêng La Liga ~25 bàn) -> ước ~430 tính tới ~06/2026.
    # Nguồn: ESPN/SI/Tribuna (mốc 400). *Số hiện tại là ước lượng, chỉnh tay 1 số nếu muốn chính xác hơn.
    278: {"goals": 430, "through": 2026},
    # Erling Haaland (id 1100) — 372 bàn official (CLB 317: Bryne/Molde/Salzburg/Dortmund/
    # Man City + Na Uy 55), tính ~06/2026. Nguồn: Wikipedia. API-Football tự cộng chỉ ra 342
    # do thiếu dữ liệu các mùa đầu sự nghiệp (Bryne/Molde/Salzburg 2016–2019) -> neo tay cho chuẩn.
    # `through` đặt cao (2026) để KHÔNG cộng thêm mùa nào -> hiển thị đúng 372; ghi thêm bàn thì
    # tăng số này lên (cập nhật vài tháng/lần), giống cách làm với Messi/Neymar.
    1100: {"goals": 372, "through": 2026},
}
