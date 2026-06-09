"""
Giới hạn tần suất (rate limit) theo IP — chống 1 người gọi dồn dập làm cạn quota API.

Vì sao chỉ siết vài endpoint "nặng" thay vì tất cả:
  - /standings, /fixtures, /leagues... rất rẻ và DÙNG CHUNG cache (1 request API/TTL/cache key
    dù bao nhiêu user) -> spam cũng gần như không tốn thêm quota.
  - /players/{id}/motm quét ~50 trận (mỗi lần ~50 request API), /career quét nhiều mùa,
    /search gọi nhiều lần /players/profiles -> đây mới là chỗ 1 script gọi nhiều id KHÁC NHAU
    có thể đốt sạch quota. Nên chỉ cần khoá các endpoint nhân-nhiều này là đủ.

Dùng decorator @limiter.limit(...) ở từng route (không cần middleware toàn cục), nên các
endpoint khác KHÔNG bị ảnh hưởng gì.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

# key_func = IP người gọi. Không đặt default_limits -> chỉ route nào gắn decorator mới bị giới hạn.
limiter = Limiter(key_func=get_remote_address)
