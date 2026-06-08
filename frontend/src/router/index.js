import { createRouter, createWebHistory } from 'vue-router'

import HomeView from '../views/HomeView.vue'

// Lazy-load các trang ít dùng hơn để bundle nhẹ.
const routes = [
  { path: '/', name: 'home', component: HomeView },
  { path: '/match/:id', name: 'match', component: () => import('../views/MatchDetailView.vue') },
  { path: '/matches', name: 'matches', component: () => import('../views/MatchesView.vue') },
  { path: '/team/:id', name: 'team', component: () => import('../views/TeamView.vue') },
  { path: '/player/:id', name: 'player', component: () => import('../views/PlayerView.vue') },
  { path: '/league/:id', name: 'league', component: () => import('../views/LeagueView.vue') },
  { path: '/country/:name', name: 'country', component: () => import('../views/CountryView.vue') },
  { path: '/favorites', name: 'favorites', component: () => import('../views/FavoritesView.vue') },
  { path: '/compare', name: 'compare', component: () => import('../views/CompareView.vue') },
]

export default createRouter({
  history: createWebHistory(),
  routes,
  // Vào trang mới -> lên đầu.
  // Back/forward -> có savedPosition. Nhưng trang tải data async nên lúc back nội dung
  // chưa render xong (trang còn rỗng) -> không thể cuộn tới vị trí cũ. Vì vậy ĐỢI cho
  // tới khi trang đủ cao mới khôi phục cuộn (poll tối đa ~2s rồi cuộn dù sao).
  scrollBehavior(to, from, savedPosition) {
    if (!savedPosition) return { top: 0 }
    // Trang đích có thể chưa render xong (đang tải data) -> đợi tới khi đủ cao rồi mới
    // khôi phục cuộn (poll tối đa ~2s). Với trang đã được <keep-alive> cache thì DOM còn
    // nguyên nên điều kiện đúng ngay lập tức.
    return new Promise((resolve) => {
      const target = savedPosition.top
      let tries = 0
      const tick = () => {
        const maxScroll = document.body.scrollHeight - window.innerHeight
        if (maxScroll >= target || tries++ > 40) resolve(savedPosition)
        else setTimeout(tick, 50)
      }
      tick()
    })
  },
})
