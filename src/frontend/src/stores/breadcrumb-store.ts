import { create } from 'zustand';

export interface BreadcrumbSegment {
  label: string;
  path?: string; // Optional path for navigation
}

export interface BreadcrumbState {
  staticSegments: BreadcrumbSegment[];
  dynamicTitle: string | null; // Restored: for the last dynamic part (e.g., item name)
  setStaticSegments: (segments: BreadcrumbSegment[]) => void;
  setDynamicTitle: (title: string | null) => void; // Restored
}

const useBreadcrumbStore = create<BreadcrumbState>((set) => ({
  staticSegments: [],
  dynamicTitle: null,
  setStaticSegments: (segments) => set({ staticSegments: segments }),
  setDynamicTitle: (title) => set({ dynamicTitle: title }),
}));

export default useBreadcrumbStore; 