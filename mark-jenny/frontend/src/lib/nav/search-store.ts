"use client";

import { useSyncExternalStore } from "react";

let isOpen = false;
const listeners = new Set<() => void>();

function subscribe(callback: () => void) {
  listeners.add(callback);
  return () => {
    listeners.delete(callback);
  };
}

function getSnapshot() {
  return isOpen;
}

export function setSearchOpen(open: boolean) {
  if (isOpen === open) return;
  isOpen = open;
  listeners.forEach((listener) => listener());
}

export function useSearchOpen() {
  return useSyncExternalStore(subscribe, getSnapshot);
}