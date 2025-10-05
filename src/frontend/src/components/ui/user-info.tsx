import { useState, useEffect, useRef } from 'react';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
  DropdownMenuGroup,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
} from '@/components/ui/dropdown-menu';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { LogOut, User as UserIcon, FlaskConical, Beaker, Users as UsersIcon } from 'lucide-react';
import { Switch } from '@/components/ui/switch';
import { useFeatureVisibilityStore } from '@/stores/feature-visibility-store';
import { usePermissions } from '@/stores/permissions-store';
import { FeatureAccessLevel, AppRole } from '@/types/settings';
import { ACCESS_LEVEL_ORDER } from '../../lib/permissions';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useNavigate } from 'react-router-dom';

interface UserInfoData {
  email: string | null;
  username: string | null;
  user: string | null;
  ip: string | null;
  groups: string[] | null;
}

// Helper function to get a display name for the highest access level
const getHighestAccessLevelName = (userPermissions: Record<string, FeatureAccessLevel>): string => {
    let maxLevel = FeatureAccessLevel.NONE;
    let maxLevelOrder = ACCESS_LEVEL_ORDER[maxLevel];

    for (const featureId in userPermissions) {
        const level = userPermissions[featureId];
        const levelOrder = ACCESS_LEVEL_ORDER[level];
        if (levelOrder > maxLevelOrder) {
            maxLevel = level;
            maxLevelOrder = levelOrder;
        }
    }

    switch (maxLevel) {
        case FeatureAccessLevel.ADMIN: return 'Admin Access';
        case FeatureAccessLevel.READ_WRITE: return 'Read/Write Access';
        case FeatureAccessLevel.READ_ONLY: return 'Read-Only Access';
        case FeatureAccessLevel.NONE: return 'No Access';
        default: return 'Unknown Access';
    }
};

// Map calculated level names to expected canonical role names
// Adjust these names if your actual default roles are named differently
const CANONICAL_ROLE_NAMES: Record<string, string | null> = {
    'Admin Access': 'Admin',
    'Read/Write Access': 'Read Write', // Or 'Editor'?
    'Read-Only Access': 'Read Only',  // Or 'Viewer'?
    'No Access': null, // No specific role name for no access
    'Unknown Access': null, // No specific role name for unknown
};

export default function UserInfo() {
  const [userInfo, setUserInfo] = useState<UserInfoData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const hasFetched = useRef(false);
  const { showBeta, showAlpha, actions: visibilityActions } = useFeatureVisibilityStore();
  const {
      permissions,
      isLoading: permissionsLoading,
      availableRoles,
      appliedRoleId,
      setRoleOverride,
      initializeStore,
  } = usePermissions();
  
  // Use a string state for the radio group value, mapping null to 'actual'
  const [radioValue, setRadioValue] = useState<string>(appliedRoleId || 'actual');

  // Get navigate function
  const navigate = useNavigate();

  useEffect(() => {
    // Update radioValue if appliedRoleId changes externally
    setRadioValue(appliedRoleId || 'actual');
  }, [appliedRoleId]);

  useEffect(() => {
    if (hasFetched.current) return;
    
    async function fetchUserDetails() {
      try {
        const response = await fetch('/api/user/details');
        if (!response.ok) {
          // Throw an error to trigger the fallback
          throw new Error(`Details fetch failed: ${response.status}`); 
        }
        const data: UserInfoData = await response.json();
        setUserInfo(data);
        setError(null); // Clear previous errors if successful
      } catch (detailsError: any) {
        console.warn('Failed to fetch user details from SDK, falling back to headers:', detailsError.message);
        // Fallback to fetching basic info from headers
        try {
            const fallbackResponse = await fetch('/api/user/info');
            if (!fallbackResponse.ok) {
                throw new Error(`Fallback fetch failed: ${fallbackResponse.status}`);
            }
            const fallbackData: UserInfoData = await fallbackResponse.json();
            setUserInfo(fallbackData);
            setError(null); // Clear previous errors if fallback successful
        } catch (fallbackError: any) {
            console.error('Failed to load user information from both endpoints:', fallbackError);
            setError(fallbackError.message || 'Failed to load user information');
            setUserInfo(null); // Ensure userInfo is null on final failure
        }
      }
    }
    
    fetchUserDetails();
    hasFetched.current = true;
  }, []);

  // Ensure we refresh permissions/roles on mount (and when switching back to page)
  useEffect(() => {
    // On mount, ensure the permissions store is initialized (will also pull persisted override)
    initializeStore();
  }, [initializeStore]);

  // Load canonical actual role name (role inferred from groups) for the user
  const [canonicalActualRoleName, setCanonicalActualRoleName] = useState<string | null>(null);
  useEffect(() => {
    (async () => {
      try {
        const res = await fetch('/api/user/actual-role', { cache: 'no-store' });
        if (res.ok) {
          const data = await res.json();
          const roleName = data?.role?.name ?? null;
          setCanonicalActualRoleName(roleName);
        }
      } catch { /* ignore */ }
    })();
  }, []);

  // Determine if user can switch roles (use ACTUAL permissions, not overridden)
  const isLocalDev = userInfo?.username === 'localdev';
  const actualSettingsLevel = permissions['settings'] ?? FeatureAccessLevel.NONE;
  const isAdminActual = ACCESS_LEVEL_ORDER[actualSettingsLevel] >= ACCESS_LEVEL_ORDER[FeatureAccessLevel.ADMIN];
  const canSwitchRoles = !permissionsLoading && (isLocalDev || isAdminActual);

  const displayName = userInfo?.user || userInfo?.username || userInfo?.email || 'Loading...';
  const initials = displayName === 'Loading...' ? '?' : displayName.charAt(0).toUpperCase();
  const userEmail = userInfo?.email;

  let displayRoleName = 'Loading...';
  let highestActualLevelName = 'Loading...'; // Store the display name for the actual level
  let highestActualCanonicalRoleName: string | null = null; // Store the canonical name

  if (!permissionsLoading) {
      highestActualLevelName = getHighestAccessLevelName(permissions);
      highestActualCanonicalRoleName = CANONICAL_ROLE_NAMES[highestActualLevelName]; // Get canonical name

      if (appliedRoleId) {
          const appliedRole = availableRoles.find(role => role.id === appliedRoleId);
          displayRoleName = appliedRole?.name || 'Unknown Role';
      } else {
          // When no override is applied, show canonical role if available
          displayRoleName = canonicalActualRoleName || highestActualLevelName;
      }
  }

  // Filter available roles to exclude the one matching the highest actual canonical name
  // Hide the canonical actual role from the override list to avoid duplication with the "Actual" entry
  const filteredRolesForOverride = availableRoles.filter((role) => role.name !== (canonicalActualRoleName || ''));

  // Handle RadioGroup changes
  const handleRoleChange = (value: string) => {
      setRadioValue(value); // Update local state for the radio button
      if (value === 'actual') {
          setRoleOverride(null);
      } else {
          setRoleOverride(value); // value is the role.id for overrides
      }
      // Soft refresh: navigate home to trigger view queries without full reload
      navigate('/');
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" className="relative h-8 w-8 rounded-full">
          <Avatar className="h-8 w-8">
            <AvatarFallback>{initials}</AvatarFallback>
          </Avatar>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-64">
        <DropdownMenuLabel className="font-normal">
          <div className="flex flex-col space-y-1">
            <p className="text-sm font-medium leading-none">{displayName}</p>
            {userEmail && userEmail !== displayName && (
              <p className="text-xs leading-none text-muted-foreground">{userEmail}</p>
            )}
            <p className="text-xs leading-none text-muted-foreground pt-1">
              Role: {displayRoleName}
              {appliedRoleId && ' (Override)'}
            </p>
            {!userInfo && !error && <p className="text-xs text-muted-foreground">Loading info...</p>}
            {error && (
              <p className="text-xs text-destructive">Error: {error}</p>
            )}
          </div>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuGroup>
            <DropdownMenuItem disabled>
                <UserIcon className="mr-2 h-4 w-4" />
                <span>Profile</span>
            </DropdownMenuItem>
        </DropdownMenuGroup>
        <DropdownMenuSeparator />
        {canSwitchRoles && (
            <>
            <DropdownMenuGroup>
                <DropdownMenuLabel className="text-xs font-semibold text-muted-foreground px-2 py-1.5 flex items-center">
                    <UsersIcon className="mr-1.5 h-3.5 w-3.5" /> Apply Role Override
                </DropdownMenuLabel>
                <ScrollArea className="max-h-[150px] overflow-y-auto">
                    <DropdownMenuRadioGroup value={radioValue} onValueChange={handleRoleChange}>
                        <DropdownMenuRadioItem value="actual">
                            <UserIcon className="mr-1.5 h-3.5 w-3.5" />
                            {(canonicalActualRoleName || highestActualLevelName)} (Actual)
                        </DropdownMenuRadioItem>
                        {filteredRolesForOverride.map((role: AppRole) => (
                            <DropdownMenuRadioItem
                                key={role.id}
                                value={role.id}
                                className="flex items-center"
                            >
                                <UsersIcon className="mr-1.5 h-3.5 w-3.5" />
                                {role.name}
                            </DropdownMenuRadioItem>
                        ))}
                    </DropdownMenuRadioGroup>
                </ScrollArea>
            </DropdownMenuGroup>
            <DropdownMenuSeparator />
            </>
        )}
        <DropdownMenuGroup>
            <DropdownMenuLabel className="text-xs font-semibold text-muted-foreground px-2 py-1.5">Feature Previews</DropdownMenuLabel>
             <DropdownMenuItem
                className="flex items-center justify-between"
                onSelect={(e) => e.preventDefault()}
             >
                <div className="flex items-center">
                    <FlaskConical className="mr-2 h-4 w-4" />
                    <span>Show Beta Features</span>
                </div>
                <Switch
                    checked={showBeta}
                    onCheckedChange={visibilityActions.toggleBeta}
                    className="scale-75"
                 />
            </DropdownMenuItem>
             <DropdownMenuItem
                className="flex items-center justify-between"
                onSelect={(e) => e.preventDefault()}
             >
                 <div className="flex items-center">
                    <Beaker className="mr-2 h-4 w-4" />
                    <span>Show Alpha Features</span>
                </div>
                <Switch
                    checked={showAlpha}
                    onCheckedChange={visibilityActions.toggleAlpha}
                    className="scale-75"
                />
            </DropdownMenuItem>
        </DropdownMenuGroup>
        <DropdownMenuSeparator />
        <DropdownMenuItem disabled>
          <LogOut className="mr-2 h-4 w-4" />
          <span>Log out</span>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}


