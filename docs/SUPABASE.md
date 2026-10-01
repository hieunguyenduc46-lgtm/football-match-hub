# Phase 4.5 (optional, not implemented yet): moving Favorites to Supabase (auth + sync)

Favorites are currently stored in **localStorage** (on one device only). This guide moves them to **Supabase**
to get **real user accounts** + **sync across devices**, while **keeping** the current
`useFavoritesStore` interface unchanged.

> This is a future improvement. It is not needed to run the app, which works fully with localStorage.

---

## 1. Create a Supabase project

1. Go to https://supabase.com → create a project (free).
2. Open **Project Settings → API** and copy 2 values:
   - **Project URL** (e.g. `https://abcd.supabase.co`)
   - **anon public key**

## 2. Create the `favorites` table + enable row-level security (RLS)

In the Supabase **SQL Editor**, run:

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

-- Each user can only see/change their own favorites
create policy "own favorites" on favorites
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
```

## 3. Enable sign-in

**Authentication → Providers → Email**: enable Email (you can turn off "Confirm email" for faster development).

## 4. Install the library + environment variables

```bash
cd frontend
npm install @supabase/supabase-js
```

Add to `frontend/.env` (do NOT commit this file):

```
VITE_SUPABASE_URL=https://abcd.supabase.co
VITE_SUPABASE_ANON_KEY=eyJhbGciOi...
```

## 5. Create the Supabase client

`frontend/src/services/supabase.js`:

```js
import { createClient } from '@supabase/supabase-js'

const url = import.meta.env.VITE_SUPABASE_URL
const key = import.meta.env.VITE_SUPABASE_ANON_KEY

// Not configured -> null, and the store falls back to localStorage.
export const supabase = url && key ? createClient(url, key) : null
```

## 6. Make the store sync with Supabase (fallback to localStorage)

Edit `frontend/src/stores/favorites.js`: when the user is signed in, read/write Supabase;
otherwise keep using localStorage as before.

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

Call `useFavoritesStore().init()` once in `App.vue` (onMounted).

## 7. Minimal sign-in screen

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

Add a `/login` route + sign-in/sign-out buttons in the header.

---

## Notes
- Exposing the `anon key` in the frontend is NORMAL: security comes from **RLS** (step 2), not from hiding the key.
- Old localStorage data can be migrated to Supabase on the first sign-in (read localStorage, then insert).
