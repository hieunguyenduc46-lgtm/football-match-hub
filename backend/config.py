"""
Đọc cấu hình từ file .env (hoặc biến môi trường).
Logic: nếu không có API key -> tự bật chế độ mock để app vẫn chạy được.
"""
from datetime import datetime

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    api_football_key: str = ""
    api_football_host: str = "v3.football.api-sports.io"
    # "direct" = đăng ký dashboard api-sports.io (header x-apisports-key)
    # "rapidapi" = đăng ký qua RapidAPI (header x-rapidapi-key)
    api_football_via: str = "direct"
    # 0 = TỰ SUY mùa theo ngày (khỏi cập nhật hằng năm). Đặt >0 (vd 2025) để GHIM cứng 1 mùa.
    season: int = 0
    use_mock: bool = True
    # CORS: 1 hoặc nhiều origin, cách nhau bằng dấu phẩy (cho lúc deploy)
    frontend_origin: str = "http://localhost:5173"
    cache_ttl_seconds: int = 300
    # Bật các endpoint /_debug/* (xem nguyên văn API). MẶC ĐỊNH tắt ở production để
    # không lộ dữ liệu nội bộ + không tốn quota. Đặt DEBUG=true ở local khi cần chẩn lỗi.
    debug: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()

# Làm sạch khoảng trắng/xuống dòng lẫn trong biến môi trường (vd dán key trên dashboard
# bị thừa '\n' -> httpx báo "Illegal header value" và MỌI request API thất bại).
settings.api_football_key = (settings.api_football_key or "").strip()
settings.api_football_host = (settings.api_football_host or "").strip()
settings.api_football_via = (settings.api_football_via or "").strip()

# An toàn: chưa có key thì luôn dùng mock, tránh gọi API lỗi 401.
if not settings.api_football_key:
    settings.use_mock = True


# ===== Tự suy MÙA theo ngày (khỏi cập nhật hằng năm) =====
# Mùa giải châu Âu vắt 2 năm (tháng 8 -> tháng 5). Quy ước: tháng >= 7 thuộc mùa NĂM ĐÓ,
# tháng < 7 thuộc mùa NĂM TRƯỚC. Vd: 06/2026 -> 2025 (mùa 2025/26 vừa xong);
# 08/2026 -> 2026 (mùa 2026/27 mới). Khớp đúng cách suy season ở endpoint /fixtures.
def current_season(now=None):
    now = now or datetime.now()
    return now.year if now.month >= 7 else now.year - 1


def default_season():
    """Mùa mặc định cho standings / vua phá lưới / hồ sơ cầu thủ.
    SEASON env > 0 -> GHIM đúng giá trị đó (ghi đè tay khi cần xem mùa cũ).
    SEASON = 0 (hoặc không đặt) -> TỰ SUY theo ngày, không phải sửa mỗi năm."""
    return settings.season if settings.season and settings.season > 0 else current_season()


# Giải có mùa ĐẶC BIỆT, không theo quy luật mùa-năm thường:
#  - World Cup (4 năm/lần) -> ghim năm kỳ giải; cập nhật khi có kỳ mới (2030...).
LEAGUE_SEASON = {
    1: 2026,   # World Cup 2026
}

# Giải chạy theo NĂM DƯƠNG LỊCH (tháng 1–12): season = đúng năm hiện tại (vd MLS).
CALENDAR_YEAR_LEAGUES = {253}  # MLS


def season_for(league):
    """Trả season đúng cho 1 giải:
      - giải đặc biệt (World Cup...) -> theo LEAGUE_SEASON,
      - giải năm dương lịch (MLS) -> đúng NĂM hiện tại,
      - còn lại -> mùa mặc định (tự suy theo ngày, trừ khi SEASON env ghim cứng)."""
    try:
        lid = int(league)
    except (TypeError, ValueError):
        return default_season()
    if lid in LEAGUE_SEASON:
        return LEAGUE_SEASON[lid]
    if lid in CALENDAR_YEAR_LEAGUES:
        return datetime.now().year
    return default_season()


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
    # Lionel Messi (id 154) — neo 911 bàn official, TỰ CẬP NHẬT mùa hiện tại.
    # Cơ chế: baseline = official tính ĐẾN HẾT mùa 2025 = 889; app TỰ CỘNG bàn official mùa
    # 2026 (API đang là 22) -> 889 + 22 = 911 ngay bây giờ, và tự tăng khi Messi ghi thêm.
    # (API tự cộng toàn bộ ra sai vì thiếu dữ liệu mùa cũ 2004–2015, nên phải neo phần cũ.)
    154: {"goals": 889, "through": 2025},
    # Neymar (id 276) — TỔNG official ~491 (Santos/Barça/PSG/Al-Hilal + Brazil), tính ~06/2026.
    # through=2025 + baseline 483 -> 483 + (Santos mùa 2026, API đang đếm 8) = 491; bàn mới TỰ CỘNG.
    276: {"goals": 483, "through": 2025},
    # Karim Benzema (id 759) — TỔNG official ~515 (Lyon/Real/Al-Ittihad + France), tính ~06/2026.
    # through=2025 -> mùa 2026 (API đang 0) tự cộng khi ghi bàn. Nguồn: Wikipedia/StatMuse.
    759: {"goals": 515, "through": 2025},
    # Kylian Mbappé (id 278) — TỔNG official 429 (chỉnh tay theo số thực tế). baseline 425 +
    # bàn mùa 2026 API đang đếm (hiện 4 bàn World Cup) = 429. through=2025 -> bàn mới ở WC/giải
    # chính thức do API TỰ CỘNG, không cần chỉnh tay.
    278: {"goals": 425, "through": 2025},
    # Erling Haaland (id 1100) — TỔNG official ~372 (CLB Bryne/Molde/Salzburg/Dortmund/Man City +
    # Na Uy), tính ~06/2026. API thiếu mùa đầu (Bryne/Molde 2016–2019) nên neo tay phần cũ.
    # through=2025 + baseline 370 -> 370 + (mùa 2026 API đang 2) = 372; bàn mới TỰ CỘNG.
    1100: {"goals": 370, "through": 2025},
}
