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
  { path: '/favorites', name: 'favorites', component: () => import('../views/FavoritesView.vue') },
  { path: '/compare', name: 'compare', component: () => import('../views/CompareView.vue') },
]

export default createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})
