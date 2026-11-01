import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useNotificationStore } from '../stores/notifications'

const HomeView = () => import('../views/HomeView.vue')
const CatalogView = () => import('../views/CatalogView.vue')
const CardDetailView = () => import('../views/CardDetailView.vue')
const FacultiesView = () => import('../views/FacultiesView.vue')
const LoginView = () => import('../views/LoginView.vue')
const RegisterView = () => import('../views/RegisterView.vue')
const ProfileView = () => import('../views/ProfileView.vue')
const ManageCardsView = () => import('../views/ManageCardsView.vue')
const ManageCardFormView = () => import('../views/ManageCardFormView.vue')
const ManageInquiriesView = () => import('../views/ManageInquiriesView.vue')
const AdminDashboard = () => import('../views/AdminDashboard.vue')
const AdminStats = () => import('../views/AdminStats.vue')
const AdminFaculties = () => import('../views/AdminFaculties.vue')
const AdminUsers = () => import('../views/AdminUsers.vue')
const AdminTags = () => import('../views/AdminTags.vue')
const NotFoundView = () => import('../views/NotFoundView.vue')

const router = createRouter({
  history: createWebHistory(),
  scrollBehavior: (to, from, saved) => saved || { top: 0 },
  routes: [
    { path: '/', name: 'home', component: HomeView },
    { path: '/cards', name: 'cards', component: CatalogView },
    { path: '/cards/:id(\\d+)', name: 'card', component: CardDetailView },
    { path: '/faculties', name: 'faculties', component: FacultiesView },
    { path: '/login', name: 'login', component: LoginView, meta: { guest: true } },
    { path: '/register', name: 'register', component: RegisterView, meta: { guest: true } },
    { path: '/profile', name: 'profile', component: ProfileView, meta: { auth: true } },

    // Сотрудники: суперадмин и администраторы факультетов (с назначенным факультетом)
    { path: '/manage', name: 'manage', component: ManageCardsView, meta: { auth: true, staff: true } },
    { path: '/manage/cards/new', name: 'manage-card-new', component: ManageCardFormView, meta: { auth: true, staff: true } },
    { path: '/manage/cards/:id(\\d+)', name: 'manage-card-edit', component: ManageCardFormView, meta: { auth: true, staff: true } },
    { path: '/manage/inquiries', name: 'manage-inquiries', component: ManageInquiriesView, meta: { auth: true, staff: true } },

    // Администрирование вуза: только суперадмин
    {
      path: '/admin',
      component: AdminDashboard,
      meta: { auth: true, superuser: true },
      children: [
        { path: '', name: 'admin', component: AdminStats },
        { path: 'faculties', name: 'admin-faculties', component: AdminFaculties },
        { path: 'users', name: 'admin-users', component: AdminUsers },
        { path: 'tags', name: 'admin-tags', component: AdminTags }
      ]
    },

    { path: '/:pathMatch(.*)*', name: 'not-found', component: NotFoundView }
  ]
})

// Это лишь удобство: переход закрыт и на сервере (права проверяет backend по роли и факультету)
router.beforeEach((to) => {
  const auth = useAuthStore()

  if (to.meta.auth && !auth.isAuthenticated) return '/login'
  if (to.meta.guest && auth.isAuthenticated) return '/'
  if (to.meta.superuser && !auth.isSuperuser) return '/'
  if (to.meta.staff && !auth.isStaff) {
    if (auth.user?.role === 'admin') {
      useNotificationStore().push({
        type: 'warning',
        message: 'Вам не назначен факультет. Обратитесь к суперадмину вуза.'
      })
    }
    return '/'
  }
  return true
})

export default router
