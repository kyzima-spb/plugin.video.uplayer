<script setup>
  import {
    defineProps,
    ref, computed, onMounted,
  } from 'vue'
  import {
    BBreadcrumb, BBreadcrumbItem,
    BListGroup,
  } from 'bootstrap-vue-next'

  import { api } from '@/api'
  import ListGroupItem from '@/components/ListGroupItem.vue'
  import ValueForm from '@/components/ValueForm.vue'

  const { id } = defineProps({
    id: String,
  })

  const errorString = ref('')
  const playlist = ref()
  const items = ref([])
  const title = computed(() => playlist.value?.title ?? 'Added')

  onMounted(async () => {
    try {
      const response = await api.items.list(id)
      playlist.value = response.playlist
      items.value = response.items
    } catch (err) {
      console.error(err)
    }
  })

  async function handleCreate(url, reset) {
    try {
      items.value.unshift(
        await api.items.create(playlist.value?.id, { url })
      )
      reset()
    } catch (err) {
      console.error(err)
      errorString.value = err.toString()
    }
  }

  async function handleDelete(item) {
    try {
      await api.items.delete(item.id)
      items.value.splice(items.value.indexOf(item), 1)
    } catch (err) {
      console.error(err)
    }
  }

  async function handleUpdate(item) {
    try {
      await api.playlists.update(item.id, item)
    } catch (err) {
      console.error(err)
    }
  }
</script>

<template>
  <h1>{{ title }}</h1>
  <BBreadcrumb class="mt-3">
    <BBreadcrumbItem to="/">
      <i class="bi bi-house-fill"></i> Playlists
    </BBreadcrumbItem>
    <BBreadcrumbItem active>
      {{ title }}
    </BBreadcrumbItem>
  </BBreadcrumb>
  <ValueForm
    :errorString="errorString"
    placeholder="Video URL"
    @submit="handleCreate"
  />
  <BListGroup numbered flush>
    <ListGroupItem
      v-for="item in items"
      :key="item.id"
      v-model="item.url"
      @delete="() => handleDelete(item)"
      @update="() => handleUpdate(item)"
    >
      <a :href="item.url" target="_blank">{{ item.title }}</a>
    </ListGroupItem>
  </BListGroup>
</template>