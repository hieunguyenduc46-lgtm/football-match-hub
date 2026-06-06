# Phase 4.5 — Nâng Favorites lên Supabase (auth + đồng bộ)

Hiện favorites lưu trong **localStorage** (chỉ trên 1 máy). Guide này nâng lên **Supabase**
để có **tài khoản đăng nhập thật** + **đồng bộ nhiều thiết bị**, mà **giữ nguyên** cách dùng
store `useFavoritesStore` hiện tại.

> Làm guide này khi bạn rảnh — không bắt buộc để web chạy. Web vẫn hoạt động đầy đủ với localStorage.

---

## 1. Tạo project Supabase

1. Vào https://supabase.com → tạo project (free).
2. Vào **Project Settings → API**, copy 2 giá trị:
   - **Project URL** (vd `https://abcd.supabase.co`)
   - **anon public key**

## 2. Tạo bảng `favorites` + bật bảo mật (RLS)

Vào **SQL Editor** của Supabase, chạy:

```sql
create table favorites (
  id          bigint generated always as identity primary key,
  user_id     uuid not null references auth.users (id) on delete cascade,
  kind        text not null check (kind in ('team', 'player')),
  item_id     bigint not null,
  name        text,
  image       text,
  created_at  timestamptz default now(),
  unique (user_id, kind, item_id)
);

alter table favorites enable row level security;

-- Mỗi user chỉ thấy/sửa được favorites của chính mình
create policy "own favorites" on favorites
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
```

## 3. Bật đăng nhập

**Authentication → Providers → Email**: bật Email (có thể tắt "Confirm email" cho dev nhanh).

## 4. Cài thư viện + biến môi trường

```bash
cd frontend
npm install @supabase/supabase-js
```

Thêm vào `frontend/.env` (KHÔNG commit file này):

```
VITE_SUPABASE_URL=https://abcd.supabase.co
VITE_SUPABASE_ANON_KEY=eyJhbGciOi...
```

## 5. Tạo client Supabase

`frontend/src/services/supabase.js`:

```js
import { createClient } from '@supabase/supabase-js'

const url = import.meta.env.VITE_SUPABASE_URL
const key = import.meta.env.VITE_SUPABASE_ANON_KEY

// Nếu chưa cấu hình -> null, store sẽ tự fallback về localStorage.
export const supabase = url && key ? createClient(url, key) : null
```

## 6. Cho store đồng bộ Supabase (fallback localStorage)

Sửa `frontend/src/stores/favorites.js` — thêm logic: nếu đã đăng nhập thì đọc/ghi Supabase,
chưa thì dùng localStorage như cũ.

```js
import { defineStore } from 'pinia'
import { supabase } from '../services/supabase'

export const useFavoritesStore = defineStore('favorites', {
  state: () => ({ teams: [], players: [], user: null }),
  getters: {
    isTeamFav: (s) => (id) => s.teams.some((t) => t.id === id),
    isPlayerFav: (s) => (id) => s.players.some((p) => p.id === id),
  },
  actions: {
    async init() {
      if (!supabase) { this.loadLocal(); return }
      const { data } = await supabase.auth.getUser()
      this.user = data.user
      if (this.user) await this.pull()
      else this.loadLocal()
      supabase.auth.onAuthStateChange((_e, session) => {
        this.user = session?.user || null
        this.user ? this.pull() : this.loadLocal()
      })
    },
    loadLocal() {
      try {
        this.teams = JSON.parse(localStorage.getItem('fav_teams') || '[]')
        this.players = JSON.parse(localStorage.getItem('fav_players') || '[]')
      } catch (e) { this.teams = []; this.players = [] }
    },
    async pull() {
      const { data } = await supabase.from('favorites').select('*')
      this.teams = data.filter((r) => r.kind === 'team').map((r) => ({ id: r.item_id, name: r.name, logo: r.image }))
      this.players = data.filter((r) => r.kind === 'player').map((r) => ({ id: r.item_id, name: r.name, photo: r.image }))
    },
    async toggleTeam(team) {
      const on = this.isTeamFav(team.id)
      on ? this.teams = this.teams.filter((t) => t.id !== team.id)
         : this.teams.push({ id: team.id, name: team.name, logo: team.logo })
      await this._persist('team', team.id, { name: team.name, image: team.logo }, on)
    },
    async togglePlayer(p) {
      const on = this.isPlayerFav(p.id)
      on ? this.players = this.players.filter((x) => x.id !== p.id)
         : this.players.push({ id: p.id, name: p.name, photo: p.photo })
      await this._persist('player', p.id, { name: p.name, image: p.photo }, on)
    },
    async _persist(kind, itemId, extra, wasOn) {
      if (supabase && this.user) {
        if (wasOn) await supabase.from('favorites').delete().match({ kind, item_id: itemId })
        else await supabase.from('favorites').insert({ user_id: this.user.id, kind, item_id: itemId, ...extra })
      } else {
        localStorage.setItem('fav_teams', JSON.stringify(this.teams))
        localStorage.setItem('fav_players', JSON.stringify(this.players))
      }
    },
  },
})
```

Gọi `useFavoritesStore().init()` một lần trong `App.vue` (onMounted).

## 7. Màn đăng nhập tối giản

```vue
<script setup>
import { ref } from 'vue'
import { supabase } from '../services/supabase'
const email = ref(''); const password = ref('')
const signIn = () => supabase.auth.signInWithPassword({ email: email.value, password: password.value })
const signUp = () => supabase.auth.signUp({ email: email.value, password: password.value })
const signOut = () => supabase.auth.signOut()
</script>
```

Thêm route `/login` + nút đăng nhập/đăng xuất ở header.

---

## Lưu ý
- `anon key` để lộ ở frontend là BÌNH THƯỜNG — bảo mật nằm ở **RLS** (bước 2), không phải giấu key.
- Có thể tự migrate dữ liệu localStorage cũ lên Supabase ở lần đăng nhập đầu (đọc localStorage rồi insert).
