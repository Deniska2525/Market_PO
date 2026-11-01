<template>
  <div id="app">
    <NavBar />
    <main>
      <RouterView />
    </main>
    <ToastContainer />
    <DialogHost />
  </div>
</template>

<script setup>
import { RouterView } from 'vue-router'
import NavBar from './components/NavBar.vue'
import ToastContainer from './components/ToastContainer.vue'
import DialogHost from './components/DialogHost.vue'
</script>

<style>
#app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}
main {
  flex: 1;
}
</style>