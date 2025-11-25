<script setup>
  import { ApiError, ValidationError } from 'api-call-simplifier/exceptions'
  import { defineProps, ref, onMounted } from 'vue'
  import {
    BAlert,
    BButton, BForm, BFormInput, BFormInvalidFeedback,
    BRow, BCol,
  } from 'bootstrap-vue-next'

  import { api } from '@/api'

  const form = ref({})
  const errors = ref({})
  const errorString = ref('')
  const accessDenied = ref(true)

  onMounted(async () => {
    try {
      const response = await api.security.list()
      Object.assign(form.value, response.data)
      accessDenied.value = false
    } catch (err) {
      accessDenied.value = true
      errorString.value = err instanceof ApiError ? err.response.data.message : err
    }
  })

  async function onSubmit() {
    try {
      errorString.value = ''
      await api.security.update(form.value)
    } catch (err) {
      if (err instanceof ValidationError) {
        errors.value = err.errors
      } else {
        errorString.value = err instanceof ApiError ? err.response.data.message : err
      }
    }
  }

  function clearError(e) {
    delete errors.value[e.target.id]
  }
</script>

<template>
  <h2 class="mb-3">Security</h2>
  <BAlert variant="danger" :model-value="!!errorString">{{ errorString }}</BAlert>

  <BForm v-if="!accessDenied" @submit.prevent.trim="onSubmit">
    <BRow class="mb-3">
      <BCol sm="3">
        <label class="mb-2" for="youtube_apikey">YouTube API key</label>
      </BCol>
      <BCol>
        <BFormInput
          id="youtube_apikey"
          v-model.trim="form.youtube_apikey"
          :state="!errors.youtube_apikey && null"
          @focus="clearError"
        />
        <BFormInvalidFeedback>{{ errors.youtube_apikey }}</BFormInvalidFeedback>
      </BCol>
    </BRow>
    <BRow class="mb-3">
      <BCol sm="3">
        <label class="mb-2" for="youtube_client_id">YouTube client ID</label>
      </BCol>
      <BCol>
        <BFormInput
          id="youtube_client_id"
          v-model.trim="form.youtube_client_id"
          :state="!errors.youtube_client_id && null"
          @focus="clearError"
        />
        <BFormInvalidFeedback>{{ errors.youtube_client_id }}</BFormInvalidFeedback>
      </BCol>
    </BRow>
    <BRow class="mb-3">
      <BCol sm="3">
        <label class="mb-2" for="youtube_secret_key">YouTube secret key</label>
      </BCol>
      <BCol>
        <BFormInput
          id="youtube_secret_key"
          v-model.trim="form.youtube_secret_key"
          :state="!errors.youtube_secret_key && null"
          @focus="clearError"
        />
        <BFormInvalidFeedback>{{ errors.youtube_secret_key }}</BFormInvalidFeedback>
      </BCol>
    </BRow>
    <div class="d-flex">
      <BButton class="ms-auto rounded-end" variant="secondary" type="submit">
        Save
      </BButton>
    </div>
  </BForm>
</template>