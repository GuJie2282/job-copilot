/**
 * 路由配置
 */
import { createRouter, createWebHistory } from 'vue-router';
import type { RouteRecordRaw } from 'vue-router';
import { useUserStore } from '@/stores/user';

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: {
      title: '登录',
      requiresGuest: true
      // 登录页不设 chrome：保持沉浸式分屏，不显示全局顶栏
    }
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/views/Register.vue'),
    meta: {
      title: '注册',
      requiresGuest: true
      // 注册页同登录页，不显示顶栏
    }
  },
  {
    path: '/',
    name: 'Home',
    component: () => import('@/views/Home.vue'),
    meta: {
      title: '首页',
      requiresAuth: true,
      chrome: true
    }
  },
  {
    path: '/resume-parser',
    name: 'ResumeParser',
    component: () => import('@/views/ResumeParser.vue'),
    meta: {
      title: '简历解析',
      requiresAuth: true,
      chrome: true
    }
  },
  {
    path: '/jd-matcher',
    name: 'JdMatcher',
    component: () => import('@/views/JdMatcher.vue'),
    meta: {
      title: 'JD 匹配',
      requiresAuth: true,
      chrome: true
    }
  },
  {
    path: '/resume-optimizer',
    name: 'ResumeOptimizer',
    component: () => import('@/views/ResumeOptimizer.vue'),
    meta: {
      title: '简历优化',
      requiresAuth: true,
      chrome: true
    }
  },
  {
    path: '/resume-refine/:resumeId',
    name: 'ResumeRefine',
    component: () => import('@/views/ResumeRefine.vue'),
    meta: {
      title: '简历精修',
      requiresAuth: true,
      chrome: true
    }
  },
  {
    path: '/resume-history',
    name: 'ResumeHistory',
    component: () => import('@/views/ResumeHistory.vue'),
    meta: {
      title: '简历历史',
      requiresAuth: true,
      chrome: true
    }
  },
  {
    path: '/profile',
    name: 'Profile',
    component: () => import('@/views/Profile.vue'),
    meta: {
      title: '我的画像',
      requiresAuth: true,
      chrome: true
    }
  },
  {
    path: '/interview/setup',
    name: 'InterviewSetup',
    component: () => import('@/views/InterviewSetup.vue'),
    meta: {
      title: '模拟面试',
      requiresAuth: true,
      chrome: true
    }
  },
  {
    path: '/interview/room/:sessionId',
    name: 'InterviewRoom',
    component: () => import('@/views/InterviewRoom.vue'),
    meta: {
      title: '面试中',
      requiresAuth: true,
      chrome: true
    }
  },
  {
    path: '/interview/debrief/:sessionId',
    name: 'DebriefReport',
    component: () => import('@/views/DebriefReport.vue'),
    meta: {
      title: '面试复盘',
      requiresAuth: true,
      chrome: true
    }
  },
  {
    path: '/interview/library',
    name: 'ExperienceLibrary',
    component: () => import('@/views/ExperienceLibrary.vue'),
    meta: {
      title: '面经库',
      requiresAuth: true,
      chrome: true
    }
  },
  {
    path: '/interview/history',
    name: 'InterviewHistory',
    component: () => import('@/views/InterviewHistory.vue'),
    meta: {
      title: '面试历史',
      requiresAuth: true,
      chrome: true
    }
  }
];

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes
});

// 路由守卫
router.beforeEach((to, _from, next) => {
  const userStore = useUserStore();
  const isLoggedIn = userStore.isLoggedIn;

  // 设置页面标题
  if (to.meta['title']) {
    document.title = `${to.meta['title']} - 求职 Copilot`;
  }

  // 需要登录的路由
  if (to.meta['requiresAuth'] && !isLoggedIn) {
    next({ name: 'Login', query: { redirect: to.fullPath } });
    return;
  }

  // 已登录用户访问访客路由（如登录页）
  if (to.meta['requiresGuest'] && isLoggedIn) {
    next({ name: 'Home' });
    return;
  }

  next();
});

export default router;
