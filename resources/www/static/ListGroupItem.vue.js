const ListGroupItem = {
  template: `
    <form class="w-100 ms-2" v-if="editMode" @submit.prevent="handleSave">
      <div class="input-group">
        <slot name="form-control">
          <input type="text" class="form-control" required v-model="value">
        </slot>
        <button class="btn btn-primary" type="submit">Save</button>
      </div>
    </form>
    <div class="mx-2 me-auto" v-else>
      <slot>{{ value }}</slot>
    </div>
    <div class="btn-group" role="group" v-if="!editMode">
      <button type="button" class="btn btn-primary" @click="onClickEdit">
        <i class="bi bi-pencil-fill"></i>
      </button>
      <button type="button" class="btn btn-danger" @click="onClickDelete">
        <i class="bi bi-trash3-fill"></i>
      </button>
    </div>
  `,
  emits: ['delete', 'edit'],
  props: {
    obj: {
      type: Object,
      required: true,
    },
    defaultValue: {
      type: String,
    },
    editCallback: {
      type: Function,
      required: true,
    },
  },
  data() {
    return {
      editMode: false,
      value: '',
    };
  },
  methods: {
    async handleSave(e) {
      try {
        await this.editCallback(this.obj, this.value);
        this.editMode = false;
      } catch (err) {
        console.error(err);
      }
    },

    onClickDelete(e) {
      if (confirm('Are you sure you want to delete the playlist?')) {
        this.$emit('delete', this.obj);
      }
    },

    onClickEdit() {
      this.editMode = true;
    },
  },
  created() {
    this.value = this.defaultValue;
  },
};