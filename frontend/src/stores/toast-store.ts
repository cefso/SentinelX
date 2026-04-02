import { create } from 'zustand'

export interface Toast {
  id: string
  title?: string
  description: string
  type: 'success' | 'error' | 'warning' | 'info'
  duration?: number
}

interface ToastState {
  toasts: Toast[]
  addToast: (toast: Omit<Toast, 'id'>) => void
  removeToast: (id: string) => void
}

export const useToastStore = create<ToastState>((set) => ({
  toasts: [],
  addToast: (toast) => {
    const id = Math.random().toString(36).slice(2)
    set((state) => ({
      toasts: [...state.toasts, { ...toast, id }],
    }))
    // auto remove after duration (default 4s)
    setTimeout(() => {
      set((state) => ({
        toasts: state.toasts.filter((t) => t.id !== id),
      }))
    }, toast.duration ?? 4000)
  },
  removeToast: (id) => {
    set((state) => ({
      toasts: state.toasts.filter((t) => t.id !== id),
    }))
  },
}))

export const toast = {
  success: (description: string, title?: string) =>
    useToastStore.getState().addToast({ type: 'success', description, title }),
  error: (description: string, title?: string) =>
    useToastStore.getState().addToast({ type: 'error', description, title }),
  warning: (description: string, title?: string) =>
    useToastStore.getState().addToast({ type: 'warning', description, title }),
  info: (description: string, title?: string) =>
    useToastStore.getState().addToast({ type: 'info', description, title }),
}
