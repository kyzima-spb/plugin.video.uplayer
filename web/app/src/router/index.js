import { createRouter, createWebHistory } from 'vue-router'
import ItemsView from '@/views/ItemsView.vue'
import PlaylistsView from '@/views/PlaylistsView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'index',
      component: PlaylistsView,
    },
    {
      path: '/playlists/:id?/items',
      name: 'items',
      component: ItemsView,
      props: true,
    },
  ],
})

export default router
