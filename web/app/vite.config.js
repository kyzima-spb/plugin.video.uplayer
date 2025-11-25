import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'
import { VitePWA } from 'vite-plugin-pwa'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    vueDevTools(),
    VitePWA({
      manifest: {
        name: 'Universal Player',
        short_name: 'UPlayer',
        start_url: '/',
        display: 'standalone',
        background_color: '#ffffff',
        theme_color: '#f8f9fa',
        icons: [
          { src: '/icon-192.png', sizes: '192x192', type: 'image/png' },
          { src: '/icon-512.png', sizes: '512x512', type: 'image/png' }
        ]
      },
      manifestFilename: 'static/manifest.json',
      injectRegister: null,  // отключаем регистрацию сервис-воркера
      workbox: false,        // отключаем offline и кэширование
    }),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    },
  },
  build: {
    assetsDir: 'static/assets',
  },
})
