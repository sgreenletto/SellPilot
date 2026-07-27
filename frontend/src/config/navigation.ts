import {
  BarChart3,
  Bot,
  Boxes,
  ClipboardList,
  Database,
  Headphones,
  LayoutDashboard,
  Library,
  MessageSquareText,
  PackageSearch,
  PanelsTopLeft,
  PenTool,
  ShoppingBag,
  Sparkles,
  Star,
  Truck,
} from "@lucide/vue";

import type { NavigationEntry } from "@/types/navigation";

export const navigationEntries: NavigationEntry[] = [
  { id: "dashboard", label: "经营看板", path: "/dashboard", icon: LayoutDashboard },
  { id: "assistant", label: "AI 运营助手", path: "/assistant", icon: Bot },
  {
    id: "market",
    label: "市场与选品",
    icon: PackageSearch,
    children: [
      { id: "market-data", label: "市场数据", path: "/market/data", icon: BarChart3 },
      { id: "selection", label: "智能选品", path: "/market/selection", icon: Sparkles },
      { id: "reviews", label: "评论与产品改良", path: "/market/reviews", icon: Star },
    ],
  },
  {
    id: "products-group",
    label: "商品运营",
    icon: Boxes,
    children: [
      { id: "products", label: "商品管理", path: "/products", icon: ShoppingBag },
      { id: "content", label: "内容工坊", path: "/products/content", icon: PenTool },
      {
        id: "listing",
        label: "上架与库存",
        path: "/products/listing-inventory",
        icon: PanelsTopLeft,
      },
    ],
  },
  {
    id: "service",
    label: "智能客服",
    icon: Headphones,
    children: [
      {
        id: "conversations",
        label: "会话工作台",
        path: "/customer-service/conversations",
        icon: MessageSquareText,
      },
      {
        id: "knowledge",
        label: "知识库",
        path: "/customer-service/knowledge",
        icon: Library,
      },
    ],
  },
  { id: "orders", label: "订单与履约", path: "/orders", icon: Truck },
  { id: "tasks", label: "任务中心", path: "/tasks", icon: ClipboardList },
];

export const developmentNavigationEntry: NavigationEntry = {
  id: "design-system",
  label: "设计系统",
  path: "/dev/design-system",
  icon: Database,
};
