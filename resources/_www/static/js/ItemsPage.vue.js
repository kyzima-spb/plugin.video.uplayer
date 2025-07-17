const ItemsPage = {
  template: `
    <h1>{{ title }}</h1>
    <nav aria-label="breadcrumb">
      <ol class="breadcrumb mt-3">
        <li class="breadcrumb-item">
          <router-link to="/">
            <i class="bi bi-house-fill"></i> Playlists
          </router-link>
        </li>
        <li class="breadcrumb-item active" aria-current="page">
          {{ title }}
        </li>
      </ol>
    </nav>
    <form @submit.prevent="handleCreate">
      <div class="input-group mb-3">
        <input
          name="url"
          type="url"
          class="form-control"
          placeholder="Video URL"
          required
          v-model="form.url"
        >
        <button class="btn btn-secondary" type="submit">Add</button>
      </div>
    </form>
    <ol class="list-group list-group-numbered list-group-flush">
      <li
        class="list-group-item d-flex justify-content-between align-items-center px-0"
        v-for="item in items"
        :key="item.id"
      >
        <list-group-item
          :obj="item"
          :defaultValue="item.url"
          :editCallback="handleEdit"
          @delete="handleDelete"
        >
          <a :href="item.url" target="_blank">{{ item.title }}</a>
        </list-group-item>
      </li>
    </ol>
  `,
  data() {
    return {
      playlist: null,
      items: [],
      form: {
        url: '',
      },
    };
  },
  computed: {
    title() {
      return this.playlist?.title ?? 'Added';
    },
  },
  methods: {
    async fetchPlaylistItems(playlistId) {
      const url = `/items?playlist_id=${playlistId ?? ''}`;
      const resp = await fetch(url);
      const data = await resp.json();
      this.playlist = data.playlist;
      this.items = data.items;
    },

    async handleCreate() {
      try {
        const resp = await fetch('/items', {
          method: 'POST',
          body: new URLSearchParams({
            playlist_id: this.$route.params.id || null,
            url: this.form.url,
          }),
        });
        this.items.unshift(await resp.json());
        this.form.url = '';
      } catch (err) {
        console.log(err);
      }
    },

    async handleDelete(item) {
      await fetch(`/items?item_id=${item.id}`, {method: 'DELETE'});
      this.items.splice(this.items.indexOf(item), 1);
    },

    async handleEdit(item, url) {
      const resp = await fetch(`/items?item_id=${item.id}`, {
        method: 'PUT',
        body: new URLSearchParams({url}),
      });
      const updated = await resp.json();
      this.items.splice(this.items.indexOf(item), 1, updated);
    },
  },
  mounted() {
    this.fetchPlaylistItems(this.$route.params.id);
  },
};