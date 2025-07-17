<script setup>
  import {
    defineEmits, defineModel,
    nextTick, useTemplateRef,
    ref, watch,
  } from 'vue'
  import {
    BButton, BButtonGroup,
    BForm, BInputGroup, BFormInput,
    BListGroupItem,
  } from 'bootstrap-vue-next'

  const model = defineModel()
  const emit = defineEmits(['delete', 'update'])

  const tempValue = ref(model.value)
  const editMode = ref(false)

  const inputRef = useTemplateRef('input')

  watch(editMode, enabled => {
    if (enabled) {
      tempValue.value = model.value
      nextTick(() => inputRef.value?.focus())
    }
  })

  const handleCancel = () => editMode.value = false

  function handleDelete() {
    if (confirm('Are you sure you want to delete the playlist?')) {
      emit('delete')
    }
  }

  function handleSave() {
    model.value = tempValue.value
    emit('update')
    editMode.value = false
  }
</script>

<template>
  <BListGroupItem
    class="d-flex justify-content-between align-items-center px-0"
  >
    <BForm class="w-100 ms-2" v-if="editMode" @submit.prevent="handleSave">
      <BInputGroup>
        <slot name="form-control">
          <BFormInput
            required
            ref="input"
            v-model="tempValue"
            @blur="handleCancel"
            @keydown.enter.prevent="handleSave"
            @keydown.esc.prevent="handleCancel"
          />
        </slot>
        <BButton variant="primary" type="submit">Save</BButton>
      </BInputGroup>
    </BForm>
    <div class="mx-2 me-auto" v-else>
      <slot>{{ model }}</slot>
    </div>
    <BButtonGroup v-if="!editMode">
      <BButton variant="primary" @click="editMode = true">
        <i class="bi bi-pencil-fill" />
      </BButton>
      <BButton variant="danger" @click="handleDelete">
        <i class="bi bi-trash3-fill" />
      </BButton>
    </BButtonGroup>
  </BListGroupItem>
</template>