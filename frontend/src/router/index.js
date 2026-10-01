import { createRouter, createWebHistory } from 'vue-router'

import HomeView from '../views/HomeView.vue'
import { setTitle } from '../utils/title'
import { t } from '../i18n'

// Lazy-load less-used pages to keep the bundle small.
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
  // Catch ALL remaining paths (wrong URLs / old links) -> friendly 404 page. MUST BE LAST.
  { path: '/:pathMatch(.*)*', name: 'notfound', component: () => import('../views/NotFoundView.vue') },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  // New page -> scroll to the top.
  // Back/forward -> savedPosition exists. But pages load data asynchronously, so when going back the content
  // has not rendered yet (the page is still empty) -> cannot scroll to the old position. So WAIT
  // until the page is tall enough before restoring the scroll (poll up to ~2s, then scroll anyway).
  scrollBehavior(to, from, savedPosition) {
    if (!savedPosition) return { top: 0 }
    // The target page may not have finished rendering (still loading data) -> wait until it is tall enough before
    // restoring the scroll (poll up to ~2s). For pages cached by <keep-alive> the DOM is still
    // intact, so the condition is met immediately.
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

// Tab title per page. STATIC pages are set immediately; DYNAMIC pages (player/team/league/match/country)
// get a default here, which the view then overrides with the specific name once data has loaded.
router.afterEach((to) => {
  const titles = {
    home: null,
    matches: t('matchesFor'),
    favorites: t('following'),
    compare: t('compareTitle'),
  }
  setTitle(to.name in titles ? titles[to.name] : null)
})

// After DEPLOYING a new version, old chunk files are deleted -> dynamically importing a lazy page can fail with
// "Failed to fetch dynamically imported module" (user has the app open / old cache) -> blank
// page. Catch that error and RELOAD ONCE to get the new version. sessionStorage prevents an infinite loop.
router.onError((err, to) => {
  const msg = String((err && err.message) || '')
  if (/dynamically imported module|module script failed|Failed to fetch/i.test(msg)) {
    const key = 'chunk-reload:' + ((to && to.fullPath) || '')
    if (!sessionStorage.getItem(key)) {
      sessionStorage.setItem(key, '1')
      window.location.assign((to && to.fullPath) || window.location.pathname)
    }
  }
})

export default router
