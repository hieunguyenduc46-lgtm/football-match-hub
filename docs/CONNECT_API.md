# Cắm dữ liệu THẬT (API-Football)

Hướng dẫn chuyển từ dữ liệu mẫu (mock) sang dữ liệu bóng đá thật.

## 0. Hiểu cơ chế (đọc 1 phút)

- Backend là **proxy**: frontend gọi `/api/...` → backend gọi API-Football, **giấu key** + **cache**.
- Mock và API thật **cùng shape dữ liệu** → bật API thật **KHÔNG phải sửa frontend**.
- Công tắc duy nhất: biến `USE_MOCK` trong `backend/.env`.

```
Frontend (Vue)  →  /api  →  Backend (FastAPI)  →  API-Football
                                  ↑ giữ key + cache
```

---

## 1. Lấy API key

**Cách A — Trực tiếp (khuyến nghị, khớp code sẵn):**
1. Vào https://www.api-football.com/ → **Register**.
2. Vào **Dashboard** → copy **API key**.
3. Trong `.env`: đặt `API_FOOTBALL_VIA=direct` (header `x-apisports-key`).

**Cách B — Qua RapidAPI:**
1. https://rapidapi.com/ → tìm **API-Football** → **Subscribe** gói **Basic (Free)**.
2. Copy **X-RapidAPI-Key**.
3. Trong `.env`: đặt `API_FOOTBALL_VIA=rapidapi`.

---

## 2. Điền `.env` rồi restart

```bash
cd backend
cp .env.example .env     # nếu chưa có file .env
```

Mở `backend/.env` và sửa:

```
API_FOOTBALL_KEY=dán_key_của_bạn
API_FOOTBALL_VIA=direct      # hoặc rapidapi
USE_MOCK=false
SEASON=2023                  # xem mục 4 bên dưới
```

Quay lại terminal backend: `Ctrl+C` rồi `uvicorn main:app --reload`.

---

## 3. Kiểm tra đã ăn chưa

- `http://localhost:8000/api/health` → phải thấy `"mock_mode": false`.
- `http://localhost:8000/api/fixtures?date=2025-08-16` → ra trận thật (đổi ngày có lịch đấu).
- `http://localhost:8000/docs` → bấm thử từng endpoint.

Nếu trả về **rỗng mà không lỗi** → gần như chắc là **mùa giải** (mục 4), không phải bug.

---

## 4. Mùa giải — chỗ HAY NHẦM là bug ⚠️

- Gói **free thường KHÔNG có mùa hiện tại**; nó chỉ mở vài mùa cũ (ví dụ 2021–2023).
- Nếu để `SEASON=2025` mà mọi thứ rỗng → đổi `SEASON=2023` (hay mùa mà gói bạn có).
- Cách biết gói cho mùa nào: gọi `https://v3.football.api-sports.io/leagues?id=39` (kèm header key),
  xem mảng `seasons` → trường `coverage` cho biết mùa nào có dữ liệu.

---

## 5b. Giới hạn QUAN TRỌNG của gói free (đã kiểm chứng)

Gói free của API-Football giới hạn theo từng loại dữ liệu:

- **Bảng xếp hạng / cầu thủ / đội** → xem được các **mùa 2021–2023** (vd `season=2023`). ✅
- **Lịch & kết quả theo ngày (`/fixtures?date=`)** → **CHỈ trong ~3 ngày quanh hiện tại**
  (hôm qua → ngày mai). Query ngày lịch sử (vd 2023) sẽ trả `errors.plan: "Free plans do not
  have access to this date"`. ❌

Vì vậy app đã giới hạn **ô chọn ngày** ở trang chủ trong khung hôm qua→ngày mai. Muốn xem lịch
**mọi ngày / mùa** thì cần **nâng gói trả phí** (chỉ thay key, không sửa code).

## 5. Giới hạn quota (free = 100 request/ngày)

- Reset 00:00 UTC mỗi ngày.
- Backend đã cache mỗi response (mặc định `CACHE_TTL_SECONDS=300` = 5 phút). Muốn tiết kiệm hơn thì tăng số này.
- **Mẹo khi test:** đừng để tab web mở cả ngày — trang chủ tự refresh mỗi 30s sẽ đốt quota. Đóng tab khi không dùng.
- Mỗi lần mở 1 trang trận tốn ~3 request (chi tiết + line-up + sự kiện). Cân nhắc khi test nhiều.

---

## 6. Chọn / thêm giải hiển thị

Mở `backend/mock_data.py`, sửa danh sách `CURATED_LEAGUES` (đây là list cho dropdown lọc). Dùng **id giải của API-Football**:

| Giải | id |
|---|---|
| World Cup | 1 |
| Champions League | 2 |
| Premier League | 39 |
| Ligue 1 | 61 |
| Bundesliga | 78 |
| Serie A | 135 |
| La Liga | 140 |
| Saudi Pro League | 307 |

> Mẹo: với gói free, nên cho trang chủ **mặc định lọc 1 giải** (vd Premier League) thay vì "Tất cả" —
> vì `/fixtures?date=` không kèm giải sẽ trả về hàng trăm trận mọi giải, vừa rối vừa tốn data.

---

## 7. App gọi endpoint nào (đã code sẵn trong `api_football.py`)

| App | API-Football |
|---|---|
| `/api/fixtures?date=&league=&season=` | `/fixtures` |
| `/api/fixtures/{id}` | `/fixtures?id=` |
| `/api/fixtures/{id}/lineups` | `/fixtures/lineups?fixture=` |
| `/api/fixtures/{id}/events` | `/fixtures/events?fixture=` |
| `/api/standings?league=&season=` | `/standings` |
| `/api/teams/{id}` | `/teams?id=` |
| `/api/players/{id}?season=` | `/players?id=&season=` |
| `/api/topscorers?league=&season=` | `/players/topscorers` |
| `/api/search?q=` | `/teams?search=` + `/players/profiles?search=` |

Muốn thêm tính năng mới (vd thống kê trận `/fixtures/statistics`): thêm 1 hàm trong `api_football.py`
+ 1 route trong `routers/` + 1 nhánh mock trong `mock_data.py`. Cùng pattern như các phần đã có.

---

## 8. Lỗi thường gặp

| Hiện tượng | Nguyên nhân / cách sửa |
|---|---|
| 401 / 403 | Key sai, hoặc đặt sai `API_FOOTBALL_VIA` (direct vs rapidapi) |
| Rỗng nhưng không báo lỗi | Mùa giải không có trong gói free → đổi `SEASON` (mục 4) |
| "Too many requests" | Hết 100 request/ngày → đợi reset 00:00 UTC hoặc tăng cache |
| Trang chủ trống khi `USE_MOCK=false` | `/fixtures` cần `?date=` — app đã gửi sẵn; kiểm tra `SEASON` |
| CORS (khi deploy) | Đặt `FRONTEND_ORIGIN` = URL frontend trên backend |

---

## 9. Quay lại mock bất cứ lúc nào

Đặt `USE_MOCK=true` (hoặc xoá `API_FOOTBALL_KEY`) → app chạy lại bằng dữ liệu mẫu.
Tiện khi demo offline hoặc lỡ hết quota.
```
