import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { act, renderHook } from '@testing-library/react';
import useBreadcrumbStore, { BreadcrumbSegment } from './breadcrumb-store';

describe('Breadcrumb Store', () => {
  beforeEach(() => {
    // Reset store state before each test
    act(() => {
      useBreadcrumbStore.setState({
        staticSegments: [],
        dynamicTitle: null,
      });
    });
  });

  afterEach(() => {
    // Clean up
    act(() => {
      useBreadcrumbStore.setState({
        staticSegments: [],
        dynamicTitle: null,
      });
    });
  });

  describe('Initial State', () => {
    it('has correct initial state', () => {
      const { result } = renderHook(() => useBreadcrumbStore());

      expect(result.current.staticSegments).toEqual([]);
      expect(result.current.dynamicTitle).toBeNull();
    });

    it('provides setter functions', () => {
      const { result } = renderHook(() => useBreadcrumbStore());

      expect(typeof result.current.setStaticSegments).toBe('function');
      expect(typeof result.current.setDynamicTitle).toBe('function');
    });
  });

  describe('setStaticSegments', () => {
    it('sets static segments correctly', () => {
      const { result } = renderHook(() => useBreadcrumbStore());

      const segments: BreadcrumbSegment[] = [
        { label: 'Home', path: '/' },
        { label: 'Data Products', path: '/data-products' },
      ];

      act(() => {
        result.current.setStaticSegments(segments);
      });

      expect(result.current.staticSegments).toEqual(segments);
      expect(result.current.staticSegments).toHaveLength(2);
    });

    it('handles empty segments array', () => {
      const { result } = renderHook(() => useBreadcrumbStore());

      // First set some segments
      act(() => {
        result.current.setStaticSegments([
          { label: 'Home', path: '/' },
        ]);
      });

      expect(result.current.staticSegments).toHaveLength(1);

      // Then clear them
      act(() => {
        result.current.setStaticSegments([]);
      });

      expect(result.current.staticSegments).toEqual([]);
    });

    it('handles segments without paths', () => {
      const { result } = renderHook(() => useBreadcrumbStore());

      const segments: BreadcrumbSegment[] = [
        { label: 'Home' }, // No path
        { label: 'Data Products', path: '/data-products' },
        { label: 'Current Page' }, // No path
      ];

      act(() => {
        result.current.setStaticSegments(segments);
      });

      expect(result.current.staticSegments).toEqual(segments);
      expect(result.current.staticSegments[0].path).toBeUndefined();
      expect(result.current.staticSegments[1].path).toBe('/data-products');
      expect(result.current.staticSegments[2].path).toBeUndefined();
    });

    it('replaces previous segments completely', () => {
      const { result } = renderHook(() => useBreadcrumbStore());

      const firstSegments: BreadcrumbSegment[] = [
        { label: 'Home', path: '/' },
        { label: 'First', path: '/first' },
      ];

      const secondSegments: BreadcrumbSegment[] = [
        { label: 'Home', path: '/' },
        { label: 'Second', path: '/second' },
      ];

      act(() => {
        result.current.setStaticSegments(firstSegments);
      });

      expect(result.current.staticSegments).toEqual(firstSegments);

      act(() => {
        result.current.setStaticSegments(secondSegments);
      });

      expect(result.current.staticSegments).toEqual(secondSegments);
      expect(result.current.staticSegments).not.toContain(firstSegments[1]);
    });

    it('handles single segment', () => {
      const { result } = renderHook(() => useBreadcrumbStore());

      const segment: BreadcrumbSegment[] = [{ label: 'Home', path: '/' }];

      act(() => {
        result.current.setStaticSegments(segment);
      });

      expect(result.current.staticSegments).toHaveLength(1);
      expect(result.current.staticSegments[0].label).toBe('Home');
    });

    it('handles deep navigation paths', () => {
      const { result } = renderHook(() => useBreadcrumbStore());

      const deepSegments: BreadcrumbSegment[] = [
        { label: 'Home', path: '/' },
        { label: 'Data Products', path: '/data-products' },
        { label: 'Category', path: '/data-products/category' },
        { label: 'Subcategory', path: '/data-products/category/sub' },
        { label: 'Item' },
      ];

      act(() => {
        result.current.setStaticSegments(deepSegments);
      });

      expect(result.current.staticSegments).toHaveLength(5);
      expect(result.current.staticSegments[4].label).toBe('Item');
    });
  });

  describe('setDynamicTitle', () => {
    it('sets dynamic title correctly', () => {
      const { result } = renderHook(() => useBreadcrumbStore());

      act(() => {
        result.current.setDynamicTitle('Product Name');
      });

      expect(result.current.dynamicTitle).toBe('Product Name');
    });

    it('clears dynamic title when set to null', () => {
      const { result } = renderHook(() => useBreadcrumbStore());

      // First set a title
      act(() => {
        result.current.setDynamicTitle('Product Name');
      });

      expect(result.current.dynamicTitle).toBe('Product Name');

      // Then clear it
      act(() => {
        result.current.setDynamicTitle(null);
      });

      expect(result.current.dynamicTitle).toBeNull();
    });

    it('replaces previous dynamic title', () => {
      const { result } = renderHook(() => useBreadcrumbStore());

      act(() => {
        result.current.setDynamicTitle('First Title');
      });

      expect(result.current.dynamicTitle).toBe('First Title');

      act(() => {
        result.current.setDynamicTitle('Second Title');
      });

      expect(result.current.dynamicTitle).toBe('Second Title');
    });

    it('handles empty string', () => {
      const { result } = renderHook(() => useBreadcrumbStore());

      act(() => {
        result.current.setDynamicTitle('');
      });

      expect(result.current.dynamicTitle).toBe('');
    });

    it('handles special characters in title', () => {
      const { result } = renderHook(() => useBreadcrumbStore());

      const specialTitle = 'Product <Test> & "Special" \'Chars\'';

      act(() => {
        result.current.setDynamicTitle(specialTitle);
      });

      expect(result.current.dynamicTitle).toBe(specialTitle);
    });

    it('handles long titles', () => {
      const { result } = renderHook(() => useBreadcrumbStore());

      const longTitle = 'A'.repeat(200);

      act(() => {
        result.current.setDynamicTitle(longTitle);
      });

      expect(result.current.dynamicTitle).toBe(longTitle);
      expect(result.current.dynamicTitle?.length).toBe(200);
    });
  });

  describe('Combined Operations', () => {
    it('can set both static segments and dynamic title', () => {
      const { result } = renderHook(() => useBreadcrumbStore());

      const segments: BreadcrumbSegment[] = [
        { label: 'Home', path: '/' },
        { label: 'Data Products', path: '/data-products' },
      ];

      act(() => {
        result.current.setStaticSegments(segments);
        result.current.setDynamicTitle('Current Product');
      });

      expect(result.current.staticSegments).toEqual(segments);
      expect(result.current.dynamicTitle).toBe('Current Product');
    });

    it('maintains static segments when dynamic title changes', () => {
      const { result } = renderHook(() => useBreadcrumbStore());

      const segments: BreadcrumbSegment[] = [
        { label: 'Home', path: '/' },
        { label: 'Products', path: '/products' },
      ];

      act(() => {
        result.current.setStaticSegments(segments);
        result.current.setDynamicTitle('First Product');
      });

      act(() => {
        result.current.setDynamicTitle('Second Product');
      });

      expect(result.current.staticSegments).toEqual(segments);
      expect(result.current.dynamicTitle).toBe('Second Product');
    });

    it('maintains dynamic title when static segments change', () => {
      const { result } = renderHook(() => useBreadcrumbStore());

      act(() => {
        result.current.setStaticSegments([{ label: 'Home' }]);
        result.current.setDynamicTitle('Current Item');
      });

      act(() => {
        result.current.setStaticSegments([
          { label: 'Home' },
          { label: 'New Section' },
        ]);
      });

      expect(result.current.dynamicTitle).toBe('Current Item');
      expect(result.current.staticSegments).toHaveLength(2);
    });

    it('handles complete reset', () => {
      const { result } = renderHook(() => useBreadcrumbStore());

      // Set both values
      act(() => {
        result.current.setStaticSegments([
          { label: 'Home', path: '/' },
          { label: 'Section', path: '/section' },
        ]);
        result.current.setDynamicTitle('Item Name');
      });

      // Clear both
      act(() => {
        result.current.setStaticSegments([]);
        result.current.setDynamicTitle(null);
      });

      expect(result.current.staticSegments).toEqual([]);
      expect(result.current.dynamicTitle).toBeNull();
    });
  });

  describe('Store Integration', () => {
    it('updates all subscribers when state changes', () => {
      const { result: result1 } = renderHook(() => useBreadcrumbStore());
      const { result: result2 } = renderHook(() => useBreadcrumbStore());

      const segments: BreadcrumbSegment[] = [
        { label: 'Home', path: '/' },
      ];

      act(() => {
        result1.current.setStaticSegments(segments);
      });

      // Both hooks should see the update
      expect(result1.current.staticSegments).toEqual(segments);
      expect(result2.current.staticSegments).toEqual(segments);
    });

    it('shares state across multiple hook instances', () => {
      const { result: result1 } = renderHook(() => useBreadcrumbStore());
      const { result: result2 } = renderHook(() => useBreadcrumbStore());

      act(() => {
        result1.current.setDynamicTitle('Shared Title');
      });

      expect(result1.current.dynamicTitle).toBe('Shared Title');
      expect(result2.current.dynamicTitle).toBe('Shared Title');
    });
  });

  describe('Edge Cases', () => {
    it('handles rapid successive updates to static segments', () => {
      const { result } = renderHook(() => useBreadcrumbStore());

      act(() => {
        result.current.setStaticSegments([{ label: 'A' }]);
        result.current.setStaticSegments([{ label: 'B' }]);
        result.current.setStaticSegments([{ label: 'C' }]);
      });

      expect(result.current.staticSegments).toEqual([{ label: 'C' }]);
    });

    it('handles rapid successive updates to dynamic title', () => {
      const { result } = renderHook(() => useBreadcrumbStore());

      act(() => {
        result.current.setDynamicTitle('Title 1');
        result.current.setDynamicTitle('Title 2');
        result.current.setDynamicTitle('Title 3');
      });

      expect(result.current.dynamicTitle).toBe('Title 3');
    });

    it('handles unicode characters in labels', () => {
      const { result } = renderHook(() => useBreadcrumbStore());

      const segments: BreadcrumbSegment[] = [
        { label: '🏠 Home', path: '/' },
        { label: 'データ製品', path: '/products' },
        { label: 'Продукты', path: '/items' },
      ];

      act(() => {
        result.current.setStaticSegments(segments);
      });

      expect(result.current.staticSegments[0].label).toBe('🏠 Home');
      expect(result.current.staticSegments[1].label).toBe('データ製品');
      expect(result.current.staticSegments[2].label).toBe('Продукты');
    });

    it('handles segments with query parameters in paths', () => {
      const { result } = renderHook(() => useBreadcrumbStore());

      const segments: BreadcrumbSegment[] = [
        { label: 'Search', path: '/search?q=test&page=1' },
        { label: 'Results', path: '/results#top' },
      ];

      act(() => {
        result.current.setStaticSegments(segments);
      });

      expect(result.current.staticSegments[0].path).toBe('/search?q=test&page=1');
      expect(result.current.staticSegments[1].path).toBe('/results#top');
    });
  });
});
