<script setup>
  import { ref, onMounted } from 'vue'
  import {
    BBreadcrumb, BBreadcrumbItem,
    BListGroup, BListGroupItem,
  } from 'bootstrap-vue-next'

  import { api } from '@/api'
  import ListGroupItem from '@/components/ListGroupItem.vue'
  import ValueForm from '@/components/ValueForm.vue'

  const playlists = ref([])
  const errorString = ref('')

  onMounted(async () => {
    try {
      playlists.value = await api.playlists.list()
    } catch (err) {
      console.error(err)
    }
  })

  async function handleCreate(title, reset) {
    try {
      playlists.value.unshift(
        await api.playlists.create({ title })
      )
      reset()
    } catch (err) {
      console.error(err)
      errorString.value = err.toString()
    }
  }

  async function handleDelete(p) {
    try {
      await api.playlists.delete(p.id)
      playlists.value.splice(playlists.value.indexOf(p), 1)
    } catch (err) {
      console.error(err)
    }
  }

  async function handleUpdate(p) {
    try {
      await api.playlists.update(p.id, p)
    } catch (err) {
      console.error(err)
    }
  }
</script>

<template>
  <h1>Playlists</h1>
  <BBreadcrumb class="mt-3">
    <BBreadcrumbItem active>
      <i class="bi bi-house-fill"></i> Playlists
    </BBreadcrumbItem>
  </BBreadcrumb>
  <ValueForm
    :errorString="errorString"
    placeholder="Playlist name or URL"
    @submit="handleCreate"
  />
  <BListGroup numbered flush>
    <BListGroupItem class="px-0">
      <router-link class="mx-1 fw-bold" :to="{name: 'items'}">
        Added
      </router-link>
    </BListGroupItem>
    <ListGroupItem
      v-for="p in playlists"
      :key="p.id"
      v-model="p.title"
      @delete="() => handleDelete(p)"
      @update="() => handleUpdate(p)"
    >
      <router-link
        v-if="p.type_name === 'manual'"
        class="fw-bold"
        :to="{ name: 'items', params: { id: p.id } }"
      >
        {{ p.title }}
      </router-link>
      <a
        v-else-if="p.data.url"
        class="fw-bold"
        :href="p.data.url" target="_blank"
      >
        {{ p.title }}
      </a>
    </ListGroupItem>
  </BListGroup>
</template>