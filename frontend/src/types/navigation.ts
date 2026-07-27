import type { Component } from "vue";

export interface NavigationItem {
  id: string;
  label: string;
  path: string;
  icon: Component;
}

export interface NavigationGroup {
  id: string;
  label: string;
  icon: Component;
  children: NavigationItem[];
}

export type NavigationEntry = NavigationItem | NavigationGroup;

export function isNavigationGroup(entry: NavigationEntry): entry is NavigationGroup {
  return "children" in entry;
}
