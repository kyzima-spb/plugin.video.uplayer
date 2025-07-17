import axios from 'axios'
import API from 'api-call-simplifier'


const { apiCall, resource } = API(axios.create({
  baseURL: import.meta.env?.DEV ? import.meta.env?.VITE_API_URL ?? '/' : '/',
}))


export const api = {
  playlists: {
    create: apiCall('/playlists', 'post', ctx => payload => {
      const config = ctx.makeConfig()
      config.data = new URLSearchParams(payload)
      return ctx.$request(config)
    }),

    delete: apiCall('/playlists', 'delete', ctx => id => {
      const config = ctx.makeConfig()
      config.params['playlist_id'] = id
      return ctx.request(config)
    }),

    list: apiCall('/playlists', 'get', ctx => () => {
      const config = ctx.makeConfig()
      return ctx.$request(config)
    }),

    update: apiCall('/playlists', 'put', ctx => (id, payload) => {
      const config = ctx.makeConfig()

      config.params['playlist_id'] = id
      config.data = new URLSearchParams(payload)

      return ctx.$request(config)
    }),
  },

  items: {
    create: apiCall('/items', 'post', ctx => (playlistId, payload) => {
      const config = ctx.makeConfig()

      playlistId && (config.params['playlist_id'] = playlistId)
      config.data = new URLSearchParams(payload)

      return ctx.$request(config)
    }),

    delete: apiCall('/items', 'delete', ctx => id => {
      const config = ctx.makeConfig()
      config.params['item_id'] = id
      return ctx.request(config)
    }),

    list: apiCall('/items', 'get', ctx => playlistId => {
      const config = ctx.makeConfig()
      playlistId && (config.params['playlist_id'] = playlistId)
      return ctx.$request(config)
    }),

    update: apiCall('/items', 'put', ctx => (id, payload) => {
      const config = ctx.makeConfig()

      config.params['item_id'] = id
      config.data = new URLSearchParams(payload)

      return ctx.$request(config)
    }),
  },
}
