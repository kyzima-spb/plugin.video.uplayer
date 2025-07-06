const PlaylistsPage = {
  template: `
    <h1>Playlists</h1>
    <nav aria-label="breadcrumb">
      <ol class="breadcrumb mt-3">
        <li class="breadcrumb-item active" aria-current="page">
          <i class="bi bi-house-fill"></i> Playlists
        </li>
      </ol>
    </nav>
    <form @submit.prevent="handleCreate">
      <div class="input-group mb-3" :class="{'has-validation': error}">
        <input
          name="title"
          type="text"
          class="form-control"
          :class="{'is-invalid': error}"
          placeholder="Playlist name"
          required
        >
        <button class="btn btn-secondary" type="submit">Create</button>
        <div class="invalid-feedback">{{ error }}</div>
      </div>
    </form>
    <ol class="list-group list-group-numbered list-group-flush">
      <li class="list-group-item px-0">
        <router-link class="mx-1 fw-bold" :to="{name: 'items'}">
          Added
        </router-link>
      </li>
      <li
        class="list-group-item d-flex justify-content-between align-items-center px-0"
        v-for="p in playlists"
        :key="p.id"
      >
        <list-group-item
          :obj="p"
          :defaultValue="p.title"
          :editCallback="handleEdit"
          @delete="handleDelete"
        >
          <router-link
            class="fw-bold"
            :to="{
              name: 'items',
              params: { id: p.id }
            }"
          >
            {{ p.title }}
          </router-link>
        </list-group-item>
      </li>
    </ol>
  `,
  data() {
    return {
      playlists: [],
      error: null,
    };
  },
  methods: {
    async fetchPlaylists() {
      const resp = await fetch('/playlists');
      this.playlists = await resp.json();
    },

    async handleCreate(e) {
      const formData = new FormData(e.target);
      const resp = await fetch('/playlists', {
        method: 'POST',
        body: new URLSearchParams(formData.entries()),
      });
      this.playlists.unshift(await resp.json());
    },

    async handleDelete(p) {
      await fetch(`/playlists?playlist_id=${p.id}`, {method: 'DELETE'});
      this.playlists.splice(this.playlists.indexOf(p), 1);
    },

    async handleEdit(p, title) {
      const resp = await fetch(`/playlists?playlist_id=${p.id}`, {
        method: 'PUT',
        body: new URLSearchParams({
          title,
        }),
      });

      this.playlists.splice(this.playlists.indexOf(p), 1, await resp.json());
    },
  },
  mounted() {
    this.fetchPlaylists();
  },
};
