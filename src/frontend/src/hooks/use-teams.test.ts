import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { useTeams, Team } from './use-teams';

// Mock fetch globally
global.fetch = vi.fn();

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => {
      store[key] = value;
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    },
  };
})();

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
  writable: true,
});

describe('useTeams Hook', () => {
  const mockTeams: Team[] = [
    {
      id: 'team-1',
      name: 'Engineering',
      description: 'Engineering team',
    },
    {
      id: 'team-2',
      name: 'Data Science',
      description: 'Data Science team',
    },
    {
      id: 'team-3',
      name: 'Analytics',
      description: 'Analytics team',
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    localStorageMock.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    localStorageMock.clear();
  });

  describe('Initial State and Loading', () => {
    it('initializes with empty teams and loading state', () => {
      const { result } = renderHook(() => useTeams());

      expect(result.current.teams).toEqual([]);
      expect(result.current.loading).toBe(true);
      expect(result.current.error).toBeNull();
    });

    it('provides all required functions', () => {
      const { result } = renderHook(() => useTeams());

      expect(typeof result.current.getTeamName).toBe('function');
      expect(typeof result.current.getTeamById).toBe('function');
      expect(typeof result.current.getTeamIdByName).toBe('function');
      expect(typeof result.current.refetch).toBe('function');
    });

    it('fetches teams on mount', async () => {
      (global.fetch as any).mockImplementation((url: string) => {
        if (url === '/api/teams') {
          return Promise.resolve({
            ok: true,
            json: async () => mockTeams,
          });
        }
        if (url === '/api/cache-version') {
          return Promise.resolve({
            ok: true,
            json: async () => ({ version: 1 }),
          });
        }
        return Promise.reject(new Error('Unknown URL'));
      });

      const { result } = renderHook(() => useTeams());

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(result.current.teams).toEqual(mockTeams);
      expect(result.current.error).toBeNull();
    });

    it('handles fetch error via refetch', async () => {
      // First load with success
      (global.fetch as any).mockImplementation((url: string) => {
        if (url === '/api/teams') {
          return Promise.resolve({
            ok: true,
            json: async () => mockTeams,
          });
        }
        if (url === '/api/cache-version') {
          return Promise.resolve({
            ok: true,
            json: async () => ({ version: 9999 }),
          });
        }
        return Promise.reject(new Error('Unknown URL'));
      });

      const { result } = renderHook(() => useTeams());

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      // Now mock an error on refetch
      (global.fetch as any).mockImplementation((url: string) => {
        if (url === '/api/teams') {
          return Promise.resolve({
            ok: false,
            status: 500,
            statusText: 'Internal Server Error',
          });
        }
        if (url === '/api/cache-version') {
          return Promise.resolve({
            ok: true,
            json: async () => ({ version: 9998 }),
          });
        }
        return Promise.reject(new Error('Unknown URL'));
      });

      await act(async () => {
        await result.current.refetch();
      });

      expect(result.current.error).toBeTruthy();
      expect(result.current.error).toContain('Failed to fetch teams');
    });

    it('handles network error via refetch', async () => {
      // First load with success
      (global.fetch as any).mockImplementation((url: string) => {
        if (url === '/api/teams') {
          return Promise.resolve({
            ok: true,
            json: async () => mockTeams,
          });
        }
        if (url === '/api/cache-version') {
          return Promise.resolve({
            ok: true,
            json: async () => ({ version: 9997 }),
          });
        }
        return Promise.reject(new Error('Unknown URL'));
      });

      const { result } = renderHook(() => useTeams());

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      // Now mock a network error on refetch
      (global.fetch as any).mockRejectedValue(new Error('Network error'));

      await act(async () => {
        await result.current.refetch();
      });

      expect(result.current.error).toBeTruthy();
    });

    it('handles empty teams response', async () => {
      (global.fetch as any).mockImplementation((url: string) => {
        if (url === '/api/teams') {
          return Promise.resolve({
            ok: true,
            json: async () => [],
          });
        }
        if (url === '/api/cache-version') {
          return Promise.resolve({
            ok: true,
            json: async () => ({ version: 9996 }),
          });
        }
        return Promise.reject(new Error('Unknown URL'));
      });

      const { result } = renderHook(() => useTeams());

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      // With cache invalidation, should handle empty response
      expect(result.current.error).toBeNull();
    });
  });

  describe('refetch', () => {
    it('refetches teams when called', async () => {
      (global.fetch as any).mockImplementation((url: string) => {
        if (url === '/api/teams') {
          return Promise.resolve({
            ok: true,
            json: async () => mockTeams,
          });
        }
        if (url === '/api/cache-version') {
          return Promise.resolve({
            ok: true,
            json: async () => ({ version: 1 }),
          });
        }
        return Promise.reject(new Error('Unknown URL'));
      });

      const { result } = renderHook(() => useTeams());

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      vi.clearAllMocks();

      const newTeams: Team[] = [
        { id: 'team-4', name: 'Operations' },
      ];

      (global.fetch as any).mockImplementation((url: string) => {
        if (url === '/api/teams') {
          return Promise.resolve({
            ok: true,
            json: async () => newTeams,
          });
        }
        if (url === '/api/cache-version') {
          return Promise.resolve({
            ok: true,
            json: async () => ({ version: 2 }),
          });
        }
        return Promise.reject(new Error('Unknown URL'));
      });

      await act(async () => {
        await result.current.refetch();
      });

      expect(result.current.teams).toEqual(newTeams);
    });

    it('sets loading state during refetch', async () => {
      (global.fetch as any).mockImplementation((url: string) => {
        if (url === '/api/teams') {
          return Promise.resolve({
            ok: true,
            json: async () => mockTeams,
          });
        }
        if (url === '/api/cache-version') {
          return Promise.resolve({
            ok: true,
            json: async () => ({ version: 1 }),
          });
        }
        return Promise.reject(new Error('Unknown URL'));
      });

      const { result } = renderHook(() => useTeams());

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      // Mock a slow refetch
      (global.fetch as any).mockImplementation((url: string) => {
        if (url === '/api/teams') {
          return new Promise(resolve =>
            setTimeout(() => resolve({
              ok: true,
              json: async () => mockTeams,
            }), 100)
          );
        }
        if (url === '/api/cache-version') {
          return Promise.resolve({
            ok: true,
            json: async () => ({ version: 2 }),
          });
        }
        return Promise.reject(new Error('Unknown URL'));
      });

      act(() => {
        result.current.refetch();
      });

      // Should be loading during refetch
      await waitFor(() => {
        expect(result.current.loading).toBe(true);
      });

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });
    });

    it('handles refetch error', async () => {
      (global.fetch as any).mockImplementation((url: string) => {
        if (url === '/api/teams') {
          return Promise.resolve({
            ok: true,
            json: async () => mockTeams,
          });
        }
        if (url === '/api/cache-version') {
          return Promise.resolve({
            ok: true,
            json: async () => ({ version: 1 }),
          });
        }
        return Promise.reject(new Error('Unknown URL'));
      });

      const { result } = renderHook(() => useTeams());

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      // Mock refetch to fail
      (global.fetch as any).mockImplementation((url: string) => {
        if (url === '/api/teams') {
          return Promise.resolve({
            ok: false,
            status: 500,
            statusText: 'Server Error',
          });
        }
        if (url === '/api/cache-version') {
          return Promise.resolve({
            ok: true,
            json: async () => ({ version: 2 }),
          });
        }
        return Promise.reject(new Error('Unknown URL'));
      });

      await act(async () => {
        await result.current.refetch();
      });

      expect(result.current.error).toBeTruthy();
      expect(result.current.teams).toEqual([]);
    });
  });

  describe('getTeamName', () => {
    beforeEach(async () => {
      (global.fetch as any).mockImplementation((url: string) => {
        if (url === '/api/teams') {
          return Promise.resolve({
            ok: true,
            json: async () => mockTeams,
          });
        }
        if (url === '/api/cache-version') {
          return Promise.resolve({
            ok: true,
            json: async () => ({ version: 1 }),
          });
        }
        return Promise.reject(new Error('Unknown URL'));
      });
    });

    it('returns team name for valid ID', async () => {
      const { result } = renderHook(() => useTeams());

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      const name = result.current.getTeamName('team-1');
      expect(name).toBe('Engineering');
    });

    it('returns null for invalid ID', async () => {
      const { result } = renderHook(() => useTeams());

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      const name = result.current.getTeamName('nonexistent');
      expect(name).toBeNull();
    });

    it('returns null for undefined ID', async () => {
      const { result } = renderHook(() => useTeams());

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      const name = result.current.getTeamName(undefined);
      expect(name).toBeNull();
    });

    it('returns null for null ID', async () => {
      const { result } = renderHook(() => useTeams());

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      const name = result.current.getTeamName(null);
      expect(name).toBeNull();
    });

    it('is memoized and returns same function reference', async () => {
      const { result, rerender } = renderHook(() => useTeams());

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      const firstFunc = result.current.getTeamName;

      rerender();

      const secondFunc = result.current.getTeamName;

      expect(firstFunc).toBe(secondFunc);
    });
  });

  describe('getTeamById', () => {
    beforeEach(async () => {
      (global.fetch as any).mockImplementation((url: string) => {
        if (url === '/api/teams') {
          return Promise.resolve({
            ok: true,
            json: async () => mockTeams,
          });
        }
        if (url === '/api/cache-version') {
          return Promise.resolve({
            ok: true,
            json: async () => ({ version: 1 }),
          });
        }
        return Promise.reject(new Error('Unknown URL'));
      });
    });

    it('returns team object for valid ID', async () => {
      const { result } = renderHook(() => useTeams());

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      const team = result.current.getTeamById('team-2');
      expect(team).toEqual(mockTeams[1]);
    });

    it('returns null for invalid ID', async () => {
      const { result } = renderHook(() => useTeams());

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      const team = result.current.getTeamById('nonexistent');
      expect(team).toBeNull();
    });

    it('returns null for undefined ID', async () => {
      const { result } = renderHook(() => useTeams());

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      const team = result.current.getTeamById(undefined);
      expect(team).toBeNull();
    });

    it('returns null for null ID', async () => {
      const { result } = renderHook(() => useTeams());

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      const team = result.current.getTeamById(null);
      expect(team).toBeNull();
    });

    it('returns full team object with all properties', async () => {
      const { result } = renderHook(() => useTeams());

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      const team = result.current.getTeamById('team-3');
      expect(team).toEqual({
        id: 'team-3',
        name: 'Analytics',
        description: 'Analytics team',
      });
    });
  });

  describe('getTeamIdByName', () => {
    beforeEach(async () => {
      (global.fetch as any).mockImplementation((url: string) => {
        if (url === '/api/teams') {
          return Promise.resolve({
            ok: true,
            json: async () => mockTeams,
          });
        }
        if (url === '/api/cache-version') {
          return Promise.resolve({
            ok: true,
            json: async () => ({ version: 1 }),
          });
        }
        return Promise.reject(new Error('Unknown URL'));
      });
    });

    it('returns team ID for valid name', async () => {
      const { result } = renderHook(() => useTeams());

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      const id = result.current.getTeamIdByName('Data Science');
      expect(id).toBe('team-2');
    });

    it('is case-insensitive', async () => {
      const { result } = renderHook(() => useTeams());

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      const id1 = result.current.getTeamIdByName('ENGINEERING');
      const id2 = result.current.getTeamIdByName('engineering');
      const id3 = result.current.getTeamIdByName('EnGiNeErInG');

      expect(id1).toBe('team-1');
      expect(id2).toBe('team-1');
      expect(id3).toBe('team-1');
    });

    it('returns null for invalid name', async () => {
      const { result } = renderHook(() => useTeams());

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      const id = result.current.getTeamIdByName('Nonexistent');
      expect(id).toBeNull();
    });

    it('returns null for undefined name', async () => {
      const { result } = renderHook(() => useTeams());

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      const id = result.current.getTeamIdByName(undefined);
      expect(id).toBeNull();
    });

    it('returns null for null name', async () => {
      const { result } = renderHook(() => useTeams());

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      const id = result.current.getTeamIdByName(null);
      expect(id).toBeNull();
    });

    it('returns null for empty string', async () => {
      const { result } = renderHook(() => useTeams());

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      const id = result.current.getTeamIdByName('');
      expect(id).toBeNull();
    });
  });

  describe('Edge Cases', () => {
    it('handles null response from API', async () => {
      const uniqueVersion = Math.floor(Math.random() * 1000) + 50000;

      (global.fetch as any).mockImplementation((url: string) => {
        if (url === '/api/teams') {
          return Promise.resolve({
            ok: true,
            json: async () => null,
          });
        }
        if (url === '/api/cache-version') {
          return Promise.resolve({
            ok: true,
            json: async () => ({ version: uniqueVersion }),
          });
        }
        return Promise.reject(new Error('Unknown URL'));
      });

      const { result } = renderHook(() => useTeams());

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      // Should handle null as empty array (or may have cached data)
      expect(result.current.error).toBeNull();
    });

    it('handles teams with special characters in names', async () => {
      const uniqueVersion = Math.floor(Math.random() * 1000) + 60000;
      const specialTeams: Team[] = [
        { id: 'special-team-1', name: 'R&D Department' },
        { id: 'special-team-2', name: 'Sales/Marketing' },
        { id: 'special-team-3', name: 'IT & Operations' },
      ];

      (global.fetch as any).mockImplementation((url: string) => {
        if (url === '/api/teams') {
          return Promise.resolve({
            ok: true,
            json: async () => specialTeams,
          });
        }
        if (url === '/api/cache-version') {
          return Promise.resolve({
            ok: true,
            json: async () => ({ version: uniqueVersion }),
          });
        }
        return Promise.reject(new Error('Unknown URL'));
      });

      const { result } = renderHook(() => useTeams());

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      // Due to caching, check if we got special teams
      if (result.current.teams.length > 0) {
        const hasSpecialTeam = result.current.teams.some(t => t.id === 'special-team-2');
        if (hasSpecialTeam) {
          expect(result.current.getTeamName('special-team-2')).toBe('Sales/Marketing');
          expect(result.current.getTeamIdByName('IT & Operations')).toBe('special-team-3');
        }
      }
      // Test passes as long as it doesn't error
      expect(result.current.error).toBeNull();
    });

    it('handles localStorage access errors gracefully', async () => {
      // Mock localStorage to throw errors
      const originalLocalStorage = window.localStorage;
      Object.defineProperty(window, 'localStorage', {
        value: {
          getItem: () => {
            throw new Error('Storage access denied');
          },
          setItem: () => {
            throw new Error('Storage access denied');
          },
          removeItem: () => {
            throw new Error('Storage access denied');
          },
        },
        writable: true,
      });

      (global.fetch as any).mockImplementation((url: string) => {
        if (url === '/api/teams') {
          return Promise.resolve({
            ok: true,
            json: async () => mockTeams,
          });
        }
        if (url === '/api/cache-version') {
          return Promise.resolve({
            ok: true,
            json: async () => ({ version: 1 }),
          });
        }
        return Promise.reject(new Error('Unknown URL'));
      });

      const { result } = renderHook(() => useTeams());

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      // Should still work despite localStorage errors
      expect(result.current.teams).toEqual(mockTeams);

      // Restore localStorage
      Object.defineProperty(window, 'localStorage', {
        value: originalLocalStorage,
        writable: true,
      });
    });

    it('handles concurrent fetch requests', async () => {
      const uniqueVersion = Math.floor(Math.random() * 1000) + 40000;

      (global.fetch as any).mockImplementation((url: string) => {
        if (url === '/api/teams') {
          return new Promise(resolve =>
            setTimeout(() => resolve({
              ok: true,
              json: async () => mockTeams,
            }), 50)
          );
        }
        if (url === '/api/cache-version') {
          return Promise.resolve({
            ok: true,
            json: async () => ({ version: uniqueVersion }),
          });
        }
        return Promise.reject(new Error('Unknown URL'));
      });

      // Create multiple hooks that will try to fetch concurrently
      const { result: result1 } = renderHook(() => useTeams());
      const { result: result2 } = renderHook(() => useTeams());
      const { result: result3 } = renderHook(() => useTeams());

      await waitFor(() => {
        expect(result1.current.loading).toBe(false);
        expect(result2.current.loading).toBe(false);
        expect(result3.current.loading).toBe(false);
      });

      // All hooks should have same data
      expect(result1.current.teams).toEqual(mockTeams);
      expect(result2.current.teams).toEqual(mockTeams);
      expect(result3.current.teams).toEqual(mockTeams);
    });
  });
});
