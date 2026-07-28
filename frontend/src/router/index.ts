import { createRouter, createWebHistory, type RouteRecordRaw } from "vue-router";

import DefaultLayout from "@/layouts/DefaultLayout.vue";
import { useAuthStore } from "@/stores/auth";

const LoginView = () => import("@/views/login/LoginView.vue");
const DashboardView = () => import("@/views/dashboard/DashboardView.vue");
const ConversationView = () => import("@/views/customer-service/ConversationView.vue");
const KnowledgeBaseView = () => import("@/views/knowledge-base/KnowledgeBaseView.vue");
const DesignSystemView = () => import("@/views/dev/DesignSystemView.vue");
const ModulePlaceholderView = () => import("@/views/placeholder/ModulePlaceholderView.vue");
const ProductsView = () => import("@/views/commerce/ProductsView.vue");
const InventoryView = () => import("@/views/commerce/InventoryView.vue");
const OrdersView = () => import("@/views/commerce/OrdersView.vue");
const MarketDataView = () => import("@/views/commerce/MarketDataView.vue");
const SelectionWorkbenchView = () => import("@/views/selection/SelectionWorkbenchView.vue");
const ReviewAnalysisView = () => import("@/views/reviews/ReviewAnalysisView.vue");
const ProductImprovementView = () => import("@/views/reviews/ProductImprovementView.vue");

const placeholderRoutes: RouteRecordRaw[] = [
  {
    path: "/assistant",
    name: "assistant",
    component: ModulePlaceholderView,
    meta: {
      title: "AI 运营助手",
      module: "AI 运营",
      description: "统一编排运营分析、工具调用和待确认任务。",
    },
  },
  {
    path: "/market/data",
    name: "market-data",
    component: MarketDataView,
    meta: {
      title: "市场数据",
      module: "市场与选品",
      description: "查看模拟市场趋势与品类数据。",
    },
  },
  {
    path: "/market/selection",
    name: "market-selection",
    component: SelectionWorkbenchView,
    meta: {
      title: "智能选品",
      module: "市场与选品",
      description: "建立可解释的候选商品评估流程。",
    },
  },
  {
    path: "/market/reviews",
    name: "market-reviews",
    component: ReviewAnalysisView,
    meta: {
      title: "评论与产品改良",
      module: "市场与选品",
      description: "从评论信号提炼产品改良方向。",
    },
  },
  {
    path: "/market/reviews/improvement",
    name: "product-improvement",
    component: ProductImprovementView,
    meta: {
      title: "产品改良报告",
      module: "市场与选品",
      description: "审查评论证据并通过确认流程创建商品内容草稿。",
    },
  },
  {
    path: "/products",
    name: "products",
    component: ProductsView,
    meta: {
      title: "商品管理",
      module: "商品运营",
      description: "管理模拟店铺的商品资料与草稿状态。",
    },
  },
  {
    path: "/products/content",
    name: "product-content",
    component: ModulePlaceholderView,
    meta: {
      title: "内容工坊",
      module: "商品运营",
      description: "生成并校验多语言商品内容。",
    },
  },
  {
    path: "/products/listing-inventory",
    name: "listing-inventory",
    component: InventoryView,
    meta: {
      title: "上架与库存",
      module: "商品运营",
      description: "处理模拟上下架和库存待确认任务。",
    },
  },
  {
    path: "/customer-service/conversations",
    name: "conversations",
    component: ConversationView,
    meta: {
      title: "会话工作台",
      module: "智能客服",
      description: "集中处理模拟买家消息与人工接管。",
    },
  },
  {
    path: "/customer-service/knowledge",
    name: "knowledge",
    component: KnowledgeBaseView,
    meta: {
      title: "知识库",
      module: "智能客服",
      description: "维护客服知识内容与检索边界。",
    },
  },
  {
    path: "/orders",
    name: "orders",
    component: OrdersView,
    meta: {
      title: "订单与履约",
      module: "履约",
      description: "查看模拟订单、物流和履约状态。",
    },
  },
  {
    path: "/tasks",
    name: "tasks",
    component: ModulePlaceholderView,
    meta: {
      title: "任务中心",
      module: "公共任务",
      description: "追踪 Agent 任务、工具调用和待确认操作。",
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
      description: "跨境店铺运营概览",
    },
  },
  ...placeholderRoutes,
];

if (import.meta.env.DEV) {
  childRoutes.push({
    path: "dev/design-system",
    name: "design-system",
    component: DesignSystemView,
    meta: {
      title: "设计系统",
      module: "开发工具",
      description: "公共设计变量与组件用法展示。",
    },
  });
}

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
        description: "登录 SellPilot 单用户模拟店铺。",
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
        description: "SellPilot 已认证应用布局。",
        requiresAuth: true,
      },
    },
    { path: "/:pathMatch(.*)*", redirect: "/dashboard" },
  ],
  scrollBehavior: () => ({ top: 0 }),
});

router.beforeEach((to, _from, next) => {
  const authStore = useAuthStore();

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
