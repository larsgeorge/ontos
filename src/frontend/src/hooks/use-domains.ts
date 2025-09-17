import { useState, useEffect, useCallback, useMemo } from 'react'

export interface DataDomain {
  id: string
  name: string
  description?: string
}

interface DomainsState {
  domains: DataDomain[]
  loading: boolean
  error: string | null
}

let globalDomainsCache: DataDomain[] | null = null
let globalCachePromise: Promise<DataDomain[]> | null = null
let cachedServerVersion: number | null = null

const checkCacheVersion = async (): Promise<boolean> => {
  try {
    const response = await fetch('/api/cache-version')
    if (!response.ok) {
      // If we can't get cache version, assume cache is valid to avoid unnecessary refetches
      return true
    }
    const data = await response.json()
    const serverVersion = data.version

    if (cachedServerVersion === null) {
      cachedServerVersion = serverVersion
      return true
    }

    return cachedServerVersion === serverVersion
  } catch (error) {
    // If cache version check fails, assume cache is valid
    return true
  }
}

const invalidateCache = () => {
  globalDomainsCache = null
  cachedServerVersion = null
}

export const useDomains = () => {
  const [state, setState] = useState<DomainsState>({
    domains: globalDomainsCache || [],
    loading: globalDomainsCache === null,
    error: null,
  })

  const fetchDomains = useCallback(async (): Promise<DataDomain[]> => {
    // Return existing promise if fetch is already in progress
    if (globalCachePromise) {
      return globalCachePromise
    }

    // Check cache version before using cached data
    if (globalDomainsCache) {
      const isCacheValid = await checkCacheVersion()
      if (isCacheValid) {
        return globalDomainsCache
      } else {
        // Cache is stale, invalidate it
        invalidateCache()
      }
    }

    // Create new fetch promise
    globalCachePromise = (async () => {
      try {
        const response = await fetch('/api/data-domains')
        if (!response.ok) {
          throw new Error(`Failed to fetch domains: ${response.status} ${response.statusText}`)
        }
        const data = await response.json()
        const domains = data || []

        // Cache the result and update cache version
        globalDomainsCache = domains

        // Update cached server version
        try {
          const versionResponse = await fetch('/api/cache-version')
          if (versionResponse.ok) {
            const versionData = await versionResponse.json()
            cachedServerVersion = versionData.version
          }
        } catch (error) {
          // If cache version update fails, continue without it
        }

        return domains
      } catch (error) {
        // Clear the promise on error so next call can retry
        globalCachePromise = null
        throw error
      } finally {
        // Clear the promise when done
        globalCachePromise = null
      }
    })()

    return globalCachePromise
  }, [])

  const loadDomains = useCallback(async () => {
    if (globalDomainsCache) {
      // Check cache version before using cached data
      const isCacheValid = await checkCacheVersion()
      if (isCacheValid) {
        // Use cached data immediately
        setState({
          domains: globalDomainsCache,
          loading: false,
          error: null,
        })
        return
      } else {
        // Cache is stale, invalidate and refetch
        invalidateCache()
      }
    }

    setState(prev => ({ ...prev, loading: true, error: null }))

    try {
      const domains = await fetchDomains()
      setState({
        domains,
        loading: false,
        error: null,
      })
    } catch (error) {
      setState({
        domains: [],
        loading: false,
        error: error instanceof Error ? error.message : 'Failed to fetch domains',
      })
    }
  }, [fetchDomains])

  // Load domains on first use
  useEffect(() => {
    if (!globalDomainsCache) {
      loadDomains()
    }
  }, [loadDomains])

  // Memoized domain lookup function
  const getDomainName = useMemo(() => {
    const domainMap = new Map(state.domains.map(domain => [domain.id, domain.name]))
    
    return (domainId: string | undefined | null): string | null => {
      if (!domainId) return null
      return domainMap.get(domainId) || null
    }
  }, [state.domains])

  // Memoized domain lookup by name function
  const getDomainById = useMemo(() => {
    const domainMap = new Map(state.domains.map(domain => [domain.id, domain]))

    return (domainId: string | undefined | null): DataDomain | null => {
      if (!domainId) return null
      return domainMap.get(domainId) || null
    }
  }, [state.domains])

  // Memoized domain ID lookup by name function
  const getDomainIdByName = useMemo(() => {
    const domainNameMap = new Map(state.domains.map(domain => [domain.name, domain.id]))

    return (domainName: string | undefined | null): string | null => {
      if (!domainName) return null
      return domainNameMap.get(domainName) || null
    }
  }, [state.domains])

  return {
    domains: state.domains,
    loading: state.loading,
    error: state.error,
    getDomainName,
    getDomainById,
    getDomainIdByName,
    refetch: loadDomains,
  }
}