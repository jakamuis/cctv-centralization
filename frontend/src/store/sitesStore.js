import { create } from "zustand";

export const useSitesStore = create((set) => ({
  sites: [],
  selectedSite: null,
  selectedNvr: null,
  selectedCamera: null,
  previewState: {
    isPreviewing: false,
    streamUrl: null,
  },

  setSites: (sites) => set({ sites }),

  setSelectedSite: (site) => set({ selectedSite: site }),

  setSelectedNvr: (nvr) => set({ selectedNvr: nvr }),

  setSelectedCamera: (camera) => set({ selectedCamera: camera }),

  setPreviewState: (previewState) => set({ previewState }),
}));

// ============================================
// Auth Store for token persistence and hydration
// ============================================

export const useAuthStore = create((set) => ({
  token: localStorage.getItem('auth_token') || null,
  user: null,
  authInitialized: false,
  setToken: (token) => {
    if (token) {
      localStorage.setItem('auth_token', token);
    } else {
      localStorage.removeItem('auth_token');
    }
    set({ token });
  },
  setUser: (user) => set({ user }),
  setAuthInitialized: (initialized) => set({ authInitialized: initialized }),
  clearAuth: () => {
    localStorage.removeItem('auth_token');
    set({ token: null, user: null, authInitialized: true });
  },
  isAuthenticated: () => !!localStorage.getItem('auth_token'),
}));
