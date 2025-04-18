import { useState, useEffect, useRef } from 'react';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
  DropdownMenuCheckboxItem,
  DropdownMenuGroup,
} from '@/components/ui/dropdown-menu';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { LogOut, User as UserIcon, FlaskConical, Beaker } from 'lucide-react';
import { useFeatureVisibilityStore } from '@/stores/feature-visibility-store';

interface UserInfoData {
  email: string | null;
  username: string | null; // Often the same as email
  user: string | null;     // Expected to hold displayName from SDK
  ip: string | null;
  groups: string[] | null;
}

export default function UserInfo() {
  const [userInfo, setUserInfo] = useState<UserInfoData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const hasFetched = useRef(false);
  const { showBeta, showAlpha, actions } = useFeatureVisibilityStore();
  
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
        console.log('Successfully fetched user details from SDK.');
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
            console.log('Successfully fetched user info from headers as fallback.');
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

  // Prioritize 'user' (displayName from SDK), then 'username', then 'email'
  const displayName = userInfo?.user || userInfo?.username || userInfo?.email || 'Loading...';
  const initials = displayName === 'Loading...' ? '?' : displayName.charAt(0).toUpperCase();
  // Use the email field directly
  const userEmail = userInfo?.email;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" className="relative h-8 w-8 rounded-full">
          <Avatar className="h-8 w-8">
            <AvatarFallback>{initials}</AvatarFallback>
          </Avatar>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuLabel className="font-normal">
          <div className="flex flex-col space-y-1">
            {/* Display name is now the primary identifier */}
            <p className="text-sm font-medium leading-none">{displayName}</p>
            {/* Show email below if available and different from displayName */}
            {userEmail && userEmail !== displayName && (
              <p className="text-xs leading-none text-muted-foreground">{userEmail}</p>
            )}
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
        <DropdownMenuGroup>
            <DropdownMenuLabel className="text-xs font-semibold text-muted-foreground px-2 py-1.5">Feature Previews</DropdownMenuLabel>
             <DropdownMenuCheckboxItem
                checked={showBeta}
                onCheckedChange={actions.toggleBeta}
                onSelect={(e) => e.preventDefault()}
            >
                <FlaskConical className="mr-2 h-4 w-4" />
                <span>Show Beta Features</span>
            </DropdownMenuCheckboxItem>
             <DropdownMenuCheckboxItem
                checked={showAlpha}
                onCheckedChange={actions.toggleAlpha}
                 onSelect={(e) => e.preventDefault()}
            >
                <Beaker className="mr-2 h-4 w-4" />
                <span>Show Alpha Features</span>
            </DropdownMenuCheckboxItem>
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


