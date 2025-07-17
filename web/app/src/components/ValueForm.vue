<script setup>
  import {
    defineEmits, defineProps, ref,
  } from 'vue'
  import {
    BButton, BForm, BFormInput, BFormInvalidFeedback, BInputGroup,
  } from 'bootstrap-vue-next'

  const props = defineProps({
    errorString: {
      type: String,
      default: '',
    },
    placeholder: String,
  })

  const value = ref('')
  const emit = defineEmits(['submit'])

  const reset = () => value.value = ''
  const onSubmit = () => emit('submit', value.value, reset)
</script>

<template>
  <BForm @submit.prevent.trim="onSubmit">
    <BInputGroup class="mb-3">
      <BFormInput
        v-model="value"
        :placeholder="placeholder"
        required
        :state="!errorString && null"
      />
      <BButton class="rounded-end" variant="secondary" type="submit">
        Create
      </BButton>
      <BFormInvalidFeedback>
        {{ errorString }}
      </BFormInvalidFeedback>
    </BInputGroup>
  </BForm>
</template>