import { createRouter, createWebHistory } from 'vue-router'
import HomePage from '@/pages/HomePage.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomePage,
    },
    {
      path: '/resort/:slug',
      name: 'resort',
      component: () => import('@/pages/ResortPage.vue'),
    },
    {
      path: '/compare',
      name: 'compare',
      component: () => import('@/pages/ComparePage.vue'),
    },
    {
      path: '/favorites',
      name: 'favorites',
      component: () => import('@/pages/FavoritesPage.vue'),
    },
    {
      path: '/custom',
      name: 'custom-locations',
      component: () => import('@/pages/CustomLocationsPage.vue'),
    },
    {
      path: '/custom/:id',
      name: 'custom-location',
      component: () => import('@/pages/CustomLocationPage.vue'),
    },
    {
      path: '/settings',
      name: 'settings',
      component: () => import('@/pages/SettingsPage.vue'),
    },
  ],
})

export default router

