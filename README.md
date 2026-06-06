# Football Match Hub

Web xem kết quả, lịch thi đấu, bảng xếp hạng, thông tin đội & cầu thủ (kèm ảnh) bóng đá.

**Stack:** Vue 3 + Vite (frontend) · FastAPI (backend) · API-Football (dữ liệu).

> Backend đứng giữa giấu API key + cache lại để tiết kiệm quota. Frontend không bao giờ
> chạm trực tiếp vào API-Football.

---

## Cấu trúc thư mục

```
Football Match Hub/
├── backend/                 # FastAPI – proxy + cache API-Football
│   ├── main.py              # khởi tạo app, CORS, gắn router
│   ├── config.py            # đọc .env (API key, mock, TTL...)
│   ├── cache.py             # cache TTL trong bộ nhớ
│   ├── api_football.py      # client gọi API (có nhánh mock)
│   ├── mock_data.py         # dữ liệu mẫu đúng shape API thật
│   ├── routers/             # fixtures, standings, teams, players
│   └── requirements.txt
└── frontend/                # Vue 3 + Vite
    └── src/
        ├── views/           # Home, MatchDetail, Team, Player, League
        ├── components/      # MatchCard, TheHeader
        ├── stores/          # Pinia (fixtures)
        ├── services/api.js  # axios -> /api (proxy sang backend)
        └── router/
```

---

## Chạy thử (chỉ 4 bước)

Cần: **Python 3.10+** và **Node 18+**.

### 1. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # để trống API key -> tự chạy MOCK
uvicorn main:app --reload
```

Backend chạy ở `http://localhost:8000` · Docs tự sinh: `http://localhost:8000/docs`

### 2. Frontend (mở terminal khác)

```bash
cd frontend
npm install
npm run dev
```

Mở `http://localhost:5173`. Vite tự proxy `/api/*` sang backend nên không lo CORS.

---

## Bật dữ liệu THẬT (bỏ mock)

1. Đăng ký tại https://www.api-football.com/ → lấy **API key**.
2. Mở `backend/.env`:
   ```
   API_FOOTBALL_KEY=key_cua_ban
   USE_MOCK=false
   ```
3. Restart backend. Xong — frontend không cần sửa gì (mock và API thật cùng shape).

> Free tier = **100 request/ngày**. Cache (mặc định 5 phút) giúp không vượt nhanh.
> Nếu đăng ký qua RapidAPI, header sẽ khác (`x-rapidapi-key`) — báo mình để chỉnh `api_football.py`.

---

## Đã làm xong — Phase 1 ✅

- Backend proxy + cache + chế độ mock.
- Trang chủ "match center": tabs **Live / Hôm nay / Sắp đá / Kết quả**, gom theo giải.
- Trang chi tiết trận (tỉ số, sân, trọng tài).
- Trang đội + đội hình.
- **Trang cầu thủ có ảnh mặt + thống kê** (bàn thắng, kiến tạo, số trận, phút, thẻ, rating).
- Bảng xếp hạng.
- Giao diện dark, mobile-first.

## Đã làm xong — Phase 2 ✅

- **Line-up vẽ trên sân:** sơ đồ thực tế (4-3-3, 4-2-3-1...), đặt cầu thủ theo vị trí `grid`,
  có ảnh + số áo + tên, ghế dự bị, HLV. Bấm cầu thủ → trang cá nhân.
- **Timeline diễn biến:** bàn thắng / thẻ vàng-đỏ / thay người theo phút, chia 2 bên đội.
- **Top scorers** (vua phá lưới) trong trang giải đấu (tab riêng).
- Trang chi tiết trận có tab **Đội hình / Diễn biến**.

> **Dữ liệu mẫu hiện có:** 4 giải — **World Cup 2026**, Premier League, La Liga, **Saudi Pro
> League**. 18 đội (CLB + đội tuyển QG) có trang + squad; 45 cầu thủ có trang chi tiết + ảnh +
> thống kê (bấm "Theo dõi" được), gồm Ronaldo, Messi, Neymar, Benzema, Mbappé, Haaland, Salah…
> Line-up + diễn biến đầy đủ cho 4 trận live: **MU–Liverpool**, **Real–Barca**,
> **Argentina–France** (WC), **Al-Nassr–Al-Hilal** (Saudi). Bảng xếp hạng + vua phá lưới cho cả
> 4 giải. Mọi thứ sẽ tự đầy đủ khi cắm API thật.

## Đã làm xong — Phase 3 ✅

- **Thanh chọn ngày** ở trang chủ (lướt trận theo từng ngày, kiểu match-center) — đã gọi
  fixtures theo `?date=`, sẵn sàng cho API thật.
- **Lọc theo giải đấu** (dropdown) — đã thêm trận La Liga (Real – Barca) để thấy bộ lọc hoạt động.
- **Ô tìm kiếm hoạt động:** gõ tên đội/cầu thủ → dropdown gợi ý → bấm mở trang.
- **Nút Dark / Light** ở header, ghi nhớ lựa chọn (localStorage).
- Endpoint mới: `/api/search`, `/api/leagues`.

## Đã làm xong — Phase 4 ✅

- **Theo dõi đội & cầu thủ:** nút ☆/★ ở trang đội và cầu thủ, lưu bằng localStorage.
- **Trang "Đang theo dõi"** (icon ♥ ở header) liệt kê đội + cầu thủ đã theo dõi, bấm vào để xem.

> Hiện lưu trên máy (localStorage). Phase 4.5 (tùy chọn) sẽ nâng lên **Supabase** để có
> tài khoản thật + đồng bộ nhiều thiết bị, giữ nguyên cách dùng store hiện tại.

## Đã làm xong — Phase 5 & 6 (chuẩn bị) ✅

- **Auto-refresh live:** trang chủ tự làm mới ngầm mỗi 30s; trang trận tự cập nhật tỉ số +
  sự kiện mỗi 20s khi trận đang đá (không nhấp nháy skeleton).
- **PWA:** có `manifest`, icon, service worker (chỉ bật ở bản production) → cài được như app,
  mở offline được phần khung.
- **Sẵn sàng deploy:** frontend dùng `VITE_API_BASE`; backend CORS nhiều origin qua env;
  có sẵn `render.yaml`, `Dockerfile`, `vercel.json`, `_redirects`.
- **Sẵn sàng API thật:** chọn nguồn key `direct`/`rapidapi`, mùa giải qua `SEASON`.

## Deploy lên mạng (có link chia sẻ)

**Backend → Render:** New + → Blueprint → chọn repo (Render đọc `render.yaml`). Sau khi có URL
backend, vào Environment đặt `FRONTEND_ORIGIN` = URL frontend (bước dưới).

**Frontend → Vercel:** Import repo → Root Directory = `frontend` → Framework: Vite. Thêm biến
`VITE_API_BASE = https://<backend>.onrender.com/api`. Deploy. Dán URL frontend ngược lại vào
`FRONTEND_ORIGIN` của backend.

## Đã làm xong — Phase 7 (tính năng nâng cao) ✅

- **Trang trận giờ có 5 tab:** Đội hình · Diễn biến · **Thống kê** (kiểm soát bóng, dứt điểm,
  xG… dạng thanh so sánh) · **Chấm điểm** cầu thủ sau trận (có gắn **MOTM**) · **Đối đầu (H2H)**
  (5 trận gần nhất + tổng kết Thắng-Hòa-Thua). Các tab nặng được **lazy-load** để tiết kiệm request.
- **Trang đội:** thêm **phong độ W-D-L 5 trận** (badge màu) + **danh sách trận gần đây**.
- **So sánh 2 cầu thủ** (icon ⇄ ở header): gõ tên 2 cầu thủ → so kè bàn thắng/kiến tạo/số trận/phút/rating.
- **Bảng xếp hạng** tô màu **vùng dự cúp** (xanh) và **rớt hạng** (đỏ); Premier League mở rộng lên 10 đội.

## Đã làm xong — Phase 8 (mở rộng dữ liệu + đa ngôn ngữ) ✅

- **World Cup đầy đủ 8 bảng A–H (32 đội tuyển)** — trang giải render từng bảng riêng.
- **Premier League & La Liga đủ 20 CLB** mỗi giải (BXH + trang đội). Tổng **~76 đội** đều có trang.
- **Chuyển ngôn ngữ Anh ⇄ Việt** (nút VI/EN ở header), nhớ lựa chọn; toàn bộ nhãn giao diện +
  ngày tháng đổi theo ngôn ngữ.

> **Về "full cầu thủ mọi CLB":** không nhập tay (hàng nghìn người, sẽ thành dữ liệu giả). Mock
> giữ ngôi sao tiêu biểu; **roster đầy đủ từng đội sẽ tự có khi cắm API thật** (xem docs/CONNECT_API.md).

## Roadmap còn lại

- **Phase 4.5 (tùy chọn):** Supabase auth + đồng bộ favorites — xem [docs/SUPABASE.md](docs/SUPABASE.md).
- **Bất cứ lúc nào:** cắm **API thật** — hướng dẫn đầy đủ ở [docs/CONNECT_API.md](docs/CONNECT_API.md)
  (lấy key, chọn mùa giải, quota, lỗi thường gặp). Trang chủ đã gọi theo ngày nên không bị trống.
- Notification trước giờ bóng lăn; timezone cho người dùng chọn; thêm nhiều giải vào mock.
