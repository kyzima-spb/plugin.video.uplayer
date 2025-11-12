<script setup>
  import { defineProps, ref, onMounted, watch } from 'vue'
  import {
    BBreadcrumb, BBreadcrumbItem,
    BListGroup,
  } from 'bootstrap-vue-next'

  import { api } from '@/api'
  import ListGroupItem from '@/components/ListGroupItem.vue'
  import ValueForm from '@/components/ValueForm.vue'

  const { id } = defineProps({
    id: {type: Number, default: null},
  })

  const items = ref([])
  const errorString = ref('')

  watch(
    () => id,
    async (newId, oldId) => {
      try {
        items.value = await api.items.list(newId)
      } catch (err) {
        console.error(err)
      }
    }
  )

  onMounted(async () => {
    try {
      items.value = await api.items.list(id)
    } catch (err) {
      console.error(err)
    }
  })

  async function handleCreate(title, reset) {
    try {
      items.value.unshift(
        await api.items.create(id, { title })
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
      await api.items.update(item.id, item)
    } catch (err) {
      console.error(err)
    }
  }
</script>

<template>
  <h1>Home</h1>
  <BBreadcrumb class="mt-3">
    <BBreadcrumbItem active>
      <i class="bi bi-house-fill"></i> Home
    </BBreadcrumbItem>
  </BBreadcrumb>
  <ValueForm
    :errorString="errorString"
    placeholder="Folder name or URL"
    @submit="handleCreate"
  />
  <BListGroup numbered flush>
    <ListGroupItem
      v-for="i in items"
      :key="i.id"
      v-model="i.title"
      @delete="() => handleDelete(i)"
      @update="() => handleUpdate(i)"
    >
      <router-link
        v-if="i.item_type === 'folder'"
        class="fw-bold"
        :to="{ name: 'index', params: { id: i.id } }"
      >
        {{ i.title }}
      </router-link>
      <a
        v-else-if="i.url"
        class="fw-bold"
        :href="i.url" target="_blank"
      >
        {{ i.title }}
      </a>
      <span v-else>
        {{ i.title }}
      </span>
    </ListGroupItem>
  </BListGroup>
</template>