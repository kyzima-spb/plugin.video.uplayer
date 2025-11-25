<script setup>
  import {
    BContainer,
    BNavbar, BNavbarBrand, BNavbarNav, BNavItem,
  } from 'bootstrap-vue-next'
  import { RouterView } from 'vue-router'
</script>

<template>
  <BNavbar variant="light" container="">
    <BNavbarBrand :to="{ name: 'index' }">UPlayer WebUI</BNavbarBrand>
    <BNavbarNav class="ms-auto">
      <BNavItem :to="{ name: 'security' }">
        <i class="bi bi-gear-fill"></i>
      </BNavItem>
    </BNavbarNav>
  </BNavbar>

  <BContainer class="py-3">
    <RouterView />
  </BContainer>
</template>
