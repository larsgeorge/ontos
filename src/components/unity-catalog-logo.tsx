import { cn } from '@/lib/utils';
import { useTheme } from "@/components/theme/theme-provider";
import { getAssetPath } from "@/utils/asset-path";

interface UnityCatalogLogoProps {
  className?: string;
}

export function UnityCatalogLogo({ className }: UnityCatalogLogoProps) {
  const { theme } = useTheme();
  
  return (
    <img
      className={cn('h-10 w-10 mr-2', className)}
      src={theme === 'dark' ? getAssetPath('/uc-logo-mark-reverse.svg') : getAssetPath('/uc-logo-mark.svg')}
      alt="Unity Catalog Logo"
    />
  );
} 