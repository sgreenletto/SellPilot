import { createRouter, createWebHistory, type RouteRecordRaw } from "vue-router";

import DefaultLayout from "@/layouts/DefaultLayout.vue";
import { rememberReviewModuleRoute, resolveReviewModuleEntry } from "@/router/review-route-memory";
import { useAuthStore } from "@/stores/auth";

export const APP_TITLE = "SellPilot";
document.title = APP_TITLE;

const LoginView = () => import("@/views/login/LoginView.vue");
const DashboardView = () => import("@/views/dashboard/DashboardView.vue");
const AssistantView = () => import("@/views/assistant/AssistantView.vue");
const ConversationView = () => import("@/views/customer-service/ConversationView.vue");
const KnowledgeBaseView = () => import("@/views/knowledge-base/KnowledgeBaseView.vue");
const ProductsView = () => import("@/views/commerce/ProductsView.vue");
const InventoryView = () => import("@/views/commerce/InventoryView.vue");
const OrdersView = () => import("@/views/commerce/OrdersView.vue");
const MarketDataView = () => import("@/views/commerce/MarketDataView.vue");
const SelectionWorkbenchView = () => import("@/views/selection/SelectionWorkbenchView.vue");
const ReviewAnalysisView = () => import("@/views/reviews/ReviewAnalysisView.vue");
const ProductImprovementView = () => import("@/views/reviews/ProductImprovementView.vue");
const ContentWorkshopView = () => import("@/views/content/ContentWorkshopView.vue");
const TaskCenterView = () => import("@/views/tasks/TaskCenterView.vue");

const placeholderRoutes: RouteRecordRaw[] = [
  {
    path: "/assistant",
    name: "assistant",
    component: AssistantView,
    meta: {
      title: "AI 运营助手",
      module: "AI 运营",
    },
  },
  {
    path: "/market/data",
    name: "market-data",
    component: MarketDataView,
    meta: {
      title: "市场数据",
      module: "市场与选品",
    },
  },
  {
    path: "/market/selection",
    name: "market-selection",
    component: SelectionWorkbenchView,
    meta: {
      title: "智能选品",
      module: "市场与选品",
      keepAlive: true,
    },
  },
  {
    path: "/market/reviews",
    name: "market-reviews",
    component: ReviewAnalysisView,
    meta: {
      title: "评论与产品改良",
      module: "市场与选品",
      keepAlive: true,
    },
  },
  {
    path: "/market/reviews/improvement",
    name: "product-improvement",
    component: ProductImprovementView,
    meta: {
      title: "产品改良报告",
      module: "市场与选品",
      keepAlive: true,
    },
  },
  {
    path: "/products",
    name: "products",
    component: ProductsView,
    meta: {
      title: "商品管理",
      module: "商品运营",
    },
  },
  {
    path: "/products/content",
    name: "product-content",
    component: ContentWorkshopView,
    meta: {
      title: "内容工坊",
      module: "商品运营",
      keepAlive: true,
    },
  },
  {
    path: "/products/listing-inventory",
    name: "listing-inventory",
    component: InventoryView,
    meta: {
      title: "上架与库存",
      module: "商品运营",
    },
  },
  {
    path: "/customer-service/conversations",
    name: "conversations",
    component: ConversationView,
    meta: {
      title: "会话工作台",
      module: "智能客服",
    },
  },
  {
    path: "/customer-service/knowledge",
    name: "knowledge",
    component: KnowledgeBaseView,
    meta: {
      title: "知识库",
      module: "智能客服",
    },
  },
  {
    path: "/orders",
    name: "orders",
    component: OrdersView,
    meta: {
      title: "订单与履约",
      module: "履约",
    },
  },
  {
    path: "/tasks",
    name: "tasks",
    component: TaskCenterView,
    meta: {
      title: "任务中心",
      module: "公共任务",
    },
  },
];

const childRoutes: RouteRecordRaw[] = [
  {
    path: "dashboard",
    name: "dashboard",
    component: DashboardView,
    meta: {
      title: "经营看板",
      module: "经营概览",
    },
  },
  ...placeholderRoutes,
];

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/login",
      name: "login",
      component: LoginView,
      meta: {
        title: "登录",
        module: "认证",
        requiresAuth: false,
      },
    },
    {
      path: "/",
      component: DefaultLayout,
      children: childRoutes,
      meta: {
        title: "SellPilot",
        module: "应用",
        requiresAuth: true,
      },
    },
    { path: "/:pathMatch(.*)*", redirect: "/dashboard" },
  ],
  scrollBehavior: () => ({ top: 0 }),
});

router.beforeEach(async (to, _from, next) => {
  const rememberedRoute = resolveReviewModuleEntry(
    to.path,
    _from.path,
    to.query.source === "selection",
  );
  if (rememberedRoute) return next(rememberedRoute);
  const authStore = useAuthStore();
  await authStore.restoreSession();

  if (to.meta.requiresAuth === false) {
    // 已登录用户访问登录页 → 直接进入看板
    if (authStore.isAuthenticated && to.name === "login") {
      return next("/dashboard");
    }
    return next();
  }

  if (!authStore.isAuthenticated) {
    return next("/login");
  }

  return next();
});

router.afterEach((to) => {
  document.title = APP_TITLE;
  rememberReviewModuleRoute(to.fullPath);
});
