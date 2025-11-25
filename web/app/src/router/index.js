import { createRouter, createWebHistory } from 'vue-router'
import ItemsView from '@/views/ItemsView.vue'
import SecurityView from '@/views/SecurityView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/:id(\\d+)?',
      name: 'index',
      component: ItemsView,
      props: route => ({
        id: route.params.id ? parseInt(route.params.id) : null,
      }),
    },
    {
      path: '/security',
      name: 'security',
      component: SecurityView,
    },
  ],
})

export default router
