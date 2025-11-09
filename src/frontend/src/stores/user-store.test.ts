import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { act, renderHook, waitFor } from '@testing-library/react';
import { useUserStore } from './user-store';
import { UserInfo } from '@/types/user';

// Mock fetch globally
global.fetch = vi.fn();

describe('User Store', () => {
  beforeEach(() => {
    // Reset store state before each test
    act(() => {
      useUserStore.setState({
        userInfo: null,
        isLoading: false,
        error: null,
      });
    });

    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('Initial State', () => {
    it('has correct initial state', () => {
      const { result } = renderHook(() => useUserStore());

      expect(result.current.userInfo).toBeNull();
      expect(result.current.isLoading).toBe(false);
      expect(result.current.error).toBeNull();
    });
  });

  describe('fetchUserInfo', () => {
    const mockUserInfo: UserInfo = {
      email: 'test@example.com',
      username: 'test_user',
      user: 'test_user',
      ip: '127.0.0.1',
      groups: ['test_admins', 'developers'],
    };

    it('fetches and sets user info successfully', async () => {
      // Arrange
      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockUserInfo,
      });

      const { result } = renderHook(() => useUserStore());

      // Act
      await act(async () => {
        await result.current.fetchUserInfo();
      });

      // Assert
      expect(result.current.userInfo).toEqual(mockUserInfo);
      expect(result.current.isLoading).toBe(false);
      expect(result.current.error).toBeNull();
      expect(global.fetch).toHaveBeenCalledWith('/api/user/details');
    });

    it('sets loading state during fetch', async () => {
      // Arrange
      let resolvePromise: (value: any) => void;
      const promise = new Promise((resolve) => {
        resolvePromise = resolve;
      });

      (global.fetch as any).mockReturnValueOnce(promise);

      const { result } = renderHook(() => useUserStore());

      // Act - Start fetch without awaiting
      act(() => {
        result.current.fetchUserInfo();
      });

      // Assert - Loading state should be true
      await waitFor(() => {
        expect(result.current.isLoading).toBe(true);
      });

      // Resolve the promise
      await act(async () => {
        resolvePromise!({
          ok: true,
          json: async () => mockUserInfo,
        });
        // Wait a tick for the promise to resolve
        await new Promise(resolve => setTimeout(resolve, 0));
      });

      expect(result.current.isLoading).toBe(false);
    });

    it('handles API error (non-ok response)', async () => {
      // Arrange
      (global.fetch as any).mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
      });

      const { result } = renderHook(() => useUserStore());
      const fetchFn = result.current.fetchUserInfo;

      // Act
      await act(async () => {
        await fetchFn();
      });

      // Assert
      expect(result.current.userInfo).toBeNull();
      expect(result.current.isLoading).toBe(false);
      expect(result.current.error).toBeTruthy();
      expect(result.current.error).toContain('API Error: 500');
    });

    it('handles network error', async () => {
      // Arrange
      (global.fetch as any).mockRejectedValueOnce(new Error('Network error'));

      const { result } = renderHook(() => useUserStore());
      const fetchFn = result.current.fetchUserInfo;

      // Act
      await act(async () => {
        await fetchFn();
      });

      // Assert
      expect(result.current.userInfo).toBeNull();
      expect(result.current.isLoading).toBe(false);
      expect(result.current.error).toBe('Network error');
    });

    it('handles missing data in response', async () => {
      // Arrange - Response with no data
      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => null,
      });

      const { result } = renderHook(() => useUserStore());
      const fetchFn = result.current.fetchUserInfo;

      // Act
      await act(async () => {
        await fetchFn();
      });

      // Assert
      expect(result.current.userInfo).toBeNull();
      expect(result.current.error).toBeTruthy();
      expect(result.current.error).toContain('No data received');
    });

    it('handles 401 unauthorized error', async () => {
      // Arrange
      (global.fetch as any).mockResolvedValueOnce({
        ok: false,
        status: 401,
        statusText: 'Unauthorized',
      });

      const { result } = renderHook(() => useUserStore());
      const fetchFn = result.current.fetchUserInfo;

      // Act
      await act(async () => {
        await fetchFn();
      });

      // Assert
      expect(result.current.userInfo).toBeNull();
      expect(result.current.error).toContain('401');
    });

    it('handles 403 forbidden error', async () => {
      // Arrange
      (global.fetch as any).mockResolvedValueOnce({
        ok: false,
        status: 403,
        statusText: 'Forbidden',
      });

      const { result } = renderHook(() => useUserStore());
      const fetchFn = result.current.fetchUserInfo;

      // Act
      await act(async () => {
        await fetchFn();
      });

      // Assert
      expect(result.current.userInfo).toBeNull();
      expect(result.current.error).toContain('403');
    });

    it('prevents concurrent fetches', async () => {
      // Arrange - Slow response
      (global.fetch as any).mockImplementation(
        () => new Promise((resolve) => setTimeout(() => resolve({
          ok: true,
          json: async () => mockUserInfo,
        }), 100))
      );

      const { result } = renderHook(() => useUserStore());
      const fetchFn = result.current.fetchUserInfo;

      // Act - Call fetch multiple times concurrently
      await act(async () => {
        await Promise.all([
          fetchFn(),
          fetchFn(),
          fetchFn(),
        ]);
      });

      // Assert - Should only call fetch once
      expect(global.fetch).toHaveBeenCalledTimes(1);
    });

    it('clears previous error on successful fetch', async () => {
      // Arrange - Set initial error state
      const { result } = renderHook(() => useUserStore());

      act(() => {
        useUserStore.setState({
          error: 'Previous error',
          userInfo: null,
        });
      });

      // Mock successful response
      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockUserInfo,
      });

      const fetchFn = result.current.fetchUserInfo;

      // Act
      await act(async () => {
        await fetchFn();
      });

      // Assert
      expect(result.current.error).toBeNull();
      expect(result.current.userInfo).toEqual(mockUserInfo);
    });

    it('preserves groups array in user info', async () => {
      // Arrange
      const userWithGroups: UserInfo = {
        ...mockUserInfo,
        groups: ['admin', 'developers', 'data-engineers'],
      };

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => userWithGroups,
      });

      const { result } = renderHook(() => useUserStore());
      const fetchFn = result.current.fetchUserInfo;

      // Act
      await act(async () => {
        await fetchFn();
      });

      // Assert
      expect(result.current.userInfo?.groups).toEqual(['admin', 'developers', 'data-engineers']);
      expect(result.current.userInfo?.groups).toHaveLength(3);
    });

    it('handles user info with null groups', async () => {
      // Arrange
      const userWithNullGroups: UserInfo = {
        ...mockUserInfo,
        groups: null,
      };

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => userWithNullGroups,
      });

      const { result } = renderHook(() => useUserStore());
      const fetchFn = result.current.fetchUserInfo;

      // Act
      await act(async () => {
        await fetchFn();
      });

      // Assert
      expect(result.current.userInfo?.groups).toBeNull();
    });

    it('handles user info with empty groups array', async () => {
      // Arrange
      const userWithEmptyGroups: UserInfo = {
        ...mockUserInfo,
        groups: [],
      };

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => userWithEmptyGroups,
      });

      const { result } = renderHook(() => useUserStore());
      const fetchFn = result.current.fetchUserInfo;

      // Act
      await act(async () => {
        await fetchFn();
      });

      // Assert
      expect(result.current.userInfo?.groups).toEqual([]);
      expect(result.current.userInfo?.groups).toHaveLength(0);
    });

    it('handles user info with null fields', async () => {
      // Arrange
      const sparseUserInfo: UserInfo = {
        email: null,
        username: 'test_user',
        user: null,
        ip: null,
        groups: ['test_group'],
      };

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => sparseUserInfo,
      });

      const { result } = renderHook(() => useUserStore());
      const fetchFn = result.current.fetchUserInfo;

      // Act
      await act(async () => {
        await fetchFn();
      });

      // Assert
      expect(result.current.userInfo?.email).toBeNull();
      expect(result.current.userInfo?.username).toBe('test_user');
      expect(result.current.userInfo?.user).toBeNull();
      expect(result.current.userInfo?.ip).toBeNull();
      expect(result.current.userInfo?.groups).toEqual(['test_group']);
    });

    it('retries fetch after error', async () => {
      // Arrange
      const { result } = renderHook(() => useUserStore());
      const fetchFn = result.current.fetchUserInfo;

      // First call fails
      (global.fetch as any).mockRejectedValueOnce(new Error('Network error'));

      await act(async () => {
        await fetchFn();
      });

      expect(result.current.error).toBeTruthy();

      // Second call succeeds
      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockUserInfo,
      });

      // Act
      await act(async () => {
        await fetchFn();
      });

      // Assert
      expect(result.current.error).toBeNull();
      expect(result.current.userInfo).toEqual(mockUserInfo);
    });
  });

  describe('Store Integration', () => {
    it('can be accessed by multiple hooks', async () => {
      // Arrange
      const mockUserInfo: UserInfo = {
        email: 'test@example.com',
        username: 'test_user',
        user: 'test_user',
        ip: '127.0.0.1',
        groups: ['test_admins'],
      };

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockUserInfo,
      });

      const { result: result1 } = renderHook(() => useUserStore());
      const { result: result2 } = renderHook(() => useUserStore());
      const fetchFn = result1.current.fetchUserInfo;

      // Act - Fetch from first hook
      await act(async () => {
        await fetchFn();
      });

      // Assert - Both hooks see the same state
      expect(result1.current.userInfo).toEqual(mockUserInfo);
      expect(result2.current.userInfo).toEqual(mockUserInfo);
      expect(result1.current.userInfo).toBe(result2.current.userInfo); // Same reference
    });

    it('updates all subscribers on state change', async () => {
      // Arrange
      const { result: result1 } = renderHook(() => useUserStore());
      const { result: result2 } = renderHook(() => useUserStore());

      const mockUserInfo: UserInfo = {
        email: 'test@example.com',
        username: 'test_user',
        user: 'test_user',
        ip: '127.0.0.1',
        groups: ['test_admins'],
      };

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockUserInfo,
      });

      const fetchFn = result1.current.fetchUserInfo;

      // Act
      await act(async () => {
        await fetchFn();
      });

      // Assert - Both hooks updated
      await waitFor(() => {
        expect(result2.current.userInfo).toEqual(mockUserInfo);
      });
    });
  });

  describe('Error Scenarios', () => {
    it('handles JSON parse error', async () => {
      // Arrange
      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => {
          throw new Error('Invalid JSON');
        },
      });

      const { result } = renderHook(() => useUserStore());
      const fetchFn = result.current.fetchUserInfo;

      // Act
      await act(async () => {
        await fetchFn();
      });

      // Assert
      expect(result.current.userInfo).toBeNull();
      expect(result.current.error).toBeTruthy();
    });

    it('handles timeout scenario', async () => {
      // Arrange
      (global.fetch as any).mockRejectedValueOnce(new Error('Request timeout'));

      const { result } = renderHook(() => useUserStore());
      const fetchFn = result.current.fetchUserInfo;

      // Act
      await act(async () => {
        await fetchFn();
      });

      // Assert
      expect(result.current.error).toBe('Request timeout');
    });

    it('handles unknown error type', async () => {
      // Arrange - Mock a non-Error rejection
      (global.fetch as any).mockImplementationOnce(() =>
        Promise.reject({ toString: () => 'Unknown error' })
      );

      const { result } = renderHook(() => useUserStore());
      const fetchFn = result.current.fetchUserInfo;

      // Act
      await act(async () => {
        await fetchFn();
      });

      // Assert
      expect(result.current.error).toBe('Failed to fetch user info');
    });
  });
});
