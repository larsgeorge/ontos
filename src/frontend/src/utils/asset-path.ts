export const getAssetPath = (path: string): string => {
  // In development, Vite serves from root
  // In production, FastAPI serves from /static/
  if (import.meta.env.DEV) {
    return path;
  }
  return `/static${path}`;
}; 