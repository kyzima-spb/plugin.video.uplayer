import axios from 'axios'
import API from 'api-call-simplifier'


const { apiCall, resource } = API(axios.create({
  baseURL: import.meta.env?.DEV ? import.meta.env?.VITE_API_URL ?? '/' : '/',
}))


export const api = {
  items: {
    create: apiCall('/items', 'post', ctx => (folderId, payload) => {
      const config = ctx.makeConfig()

      folderId && (config.params['folder_id'] = folderId)
      config.data = new URLSearchParams(payload)

      return ctx.$request(config)
    }),

    delete: apiCall('/items', 'delete', ctx => id => {
      const config = ctx.makeConfig()
      config.params['item_id'] = id
      return ctx.request(config)
    }),

    list: apiCall('/items', 'get', ctx => folderId => {
      const config = ctx.makeConfig()
      folderId && (config.params['folder_id'] = folderId)
      return ctx.$request(config)
    }),

    update: apiCall('/items', 'put', ctx => (id, payload) => {
      const config = ctx.makeConfig()

      config.params['item_id'] = id
      config.data = new URLSearchParams(payload)

      return ctx.$request(config)
    }),
  },

  security: {
    list: apiCall('/security', 'get'),
    update: apiCall('/security', 'put', ctx => payload => {
      const config = ctx.makeConfig()
      config.data = payload
      return ctx.$request(config)
    }),
  },
}
