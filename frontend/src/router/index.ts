import { createRouter, createWebHistory } from 'vue-router'
import HomePage from '@/pages/HomePage.vue'

const BASE_TITLE = 'ActuallyOpenSnow'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomePage,
      meta: { title: 'Free Mountain Snow Forecasts' },
    },
    {
      path: '/resort/:slug',
      name: 'resort',
      component: () => import('@/pages/ResortPage.vue'),
      meta: { title: 'Resort Forecast' }, // Will be overridden dynamically
    },
    {
      path: '/compare',
      name: 'compare',
      component: () => import('@/pages/ComparePage.vue'),
      meta: { title: 'Compare Weather Models' },
    },
    {
      path: '/favorites',
      name: 'favorites',
      component: () => import('@/pages/FavoritesPage.vue'),
      meta: { title: 'Your Favorite Resorts' },
    },
    {
      path: '/custom',
      name: 'custom-locations',
      component: () => import('@/pages/CustomLocationsPage.vue'),
      meta: { title: 'Custom Locations' },
    },
    {
      path: '/custom/:id',
      name: 'custom-location',
      component: () => import('@/pages/CustomLocationPage.vue'),
      meta: { title: 'Custom Location Forecast' },
    },
    {
      path: '/settings',
      name: 'settings',
      component: () => import('@/pages/SettingsPage.vue'),
      meta: { title: 'Settings' },
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'not-found',
      component: () => import('@/pages/NotFoundPage.vue'),
      meta: { title: 'Page Not Found' },
    },
  ],
  scrollBehavior(_to, _from, savedPosition) {
    // Restore scroll position on back/forward navigation
    if (savedPosition) {
      return savedPosition
    }
    return { top: 0 }
  },
})

// Update document title on navigation
router.afterEach((to) => {
  const pageTitle = to.meta.title as string | undefined
  document.title = pageTitle ? `${pageTitle} | ${BASE_TITLE}` : BASE_TITLE
})

export default router

