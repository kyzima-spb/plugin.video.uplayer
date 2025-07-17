const Form = {
  template: `
    <form class="w-100" @submit.prevent="handleSubmit">
      <slot></slot>
    </form>
  `,
  emits: ['submit'],
  methods: {
    handleSubmit(e) {
      const formData = new FormData(e.target);
      const data = Object.fromEntries(formData.entries());
      this.$emit('submit', data);
    },
  },
};