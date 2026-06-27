import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import Dashboard from './views/Dashboard.vue'
import StudentDetail from './views/StudentDetail.vue'

const routes = [
  { path: '/', component: Dashboard },
  { path: '/student/:id', component: StudentDetail, props: true },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

createApp(App).use(router).mount('#app')
