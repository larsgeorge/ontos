import React, { createContext, useState, useContext, ReactNode, useMemo, useCallback } from 'react';
import { FeatureMaturity } from '@/config/features';

interface FeatureVisibilityState {
  showBeta: boolean;
  showAlpha: boolean;
  allowedMaturities: FeatureMaturity[];
}

interface FeatureVisibilityContextType extends FeatureVisibilityState {
  toggleBeta: () => void;
  toggleAlpha: () => void;
}

const FeatureVisibilityContext = createContext<FeatureVisibilityContextType | undefined>(undefined);

interface FeatureVisibilityProviderProps {
  children: ReactNode;
}

export const FeatureVisibilityProvider: React.FC<FeatureVisibilityProviderProps> = ({ children }) => {
  const [showBeta, setShowBeta] = useState<boolean>(false); // Beta features off by default
  const [showAlpha, setShowAlpha] = useState<boolean>(false); // Alpha features off by default

  const toggleBeta = useCallback(() => setShowBeta((prev) => !prev), []);
  const toggleAlpha = useCallback(() => setShowAlpha((prev) => !prev), []);

  const allowedMaturities = useMemo((): FeatureMaturity[] => {
    const maturities: FeatureMaturity[] = ['ga'];
    if (showBeta) maturities.push('beta');
    if (showAlpha) maturities.push('alpha');
    return maturities;
  }, [showBeta, showAlpha]);

  const value = useMemo(() => ({
    showBeta,
    showAlpha,
    allowedMaturities,
    toggleBeta,
    toggleAlpha,
  }), [showBeta, showAlpha, allowedMaturities, toggleBeta, toggleAlpha]);

  return (
    <FeatureVisibilityContext.Provider value={value}>
      {children}
    </FeatureVisibilityContext.Provider>
  );
};

export const useFeatureVisibility = (): FeatureVisibilityContextType => {
  const context = useContext(FeatureVisibilityContext);
  if (context === undefined) {
    throw new Error('useFeatureVisibility must be used within a FeatureVisibilityProvider');
  }
  return context;
};