import { useState, useEffect, useCallback, useMemo } from 'react'

export interface Team {
  id: string
  name: string
  description?: string
}

interface TeamsState {
  teams: Team[]
  loading: boolean
  error: string | null
}

let globalTeamsCache: Team[] | null = null
let globalCachePromise: Promise<Team[]> | null = null
let cachedServerVersion: number | null = null

// Persist server and team cache versions to survive HMR/frontend reloads
const SERVER_VERSION_KEY = 'ucapp_server_cache_version'
const TEAMS_VERSION_KEY = 'ucapp_teams_cache_version'

// Hydrate cachedServerVersion from localStorage on module load
try {
  const stored = typeof window !== 'undefined' ? window.localStorage.getItem(SERVER_VERSION_KEY) : null
  if (stored != null) {
    const parsed = Number(stored)
    if (!Number.isNaN(parsed)) {
      cachedServerVersion = parsed
    }
  }
} catch {
  // Ignore storage access errors
}

const checkCacheVersion = async (): Promise<boolean> => {
  try {
    const response = await fetch('/api/cache-version')
    if (!response.ok) {
      // If we can't get cache version, treat existing in-memory cache as stale to be safe
      return false
    }
    const data = await response.json()
    const serverVersion = data.version

    // Persist latest seen server version
    cachedServerVersion = serverVersion
    try {
      if (typeof window !== 'undefined') {
        window.localStorage.setItem(SERVER_VERSION_KEY, String(serverVersion))
      }
    } catch {
      // Ignore storage access errors
    }

    // Compare the teams cache version with server version
    let storedTeamsVersion: number | null = null
    try {
      const stored = typeof window !== 'undefined' ? window.localStorage.getItem(TEAMS_VERSION_KEY) : null
      if (stored != null) {
        const parsed = Number(stored)
        if (!Number.isNaN(parsed)) {
          storedTeamsVersion = parsed
        }
      }
    } catch {
      // Ignore storage access errors
    }

    // If we have a teams cache in memory but no stored version, treat as stale
    if (globalTeamsCache && storedTeamsVersion === null) {
      return false
    }

    // Otherwise, valid only if versions match
    return storedTeamsVersion === serverVersion
  } catch (error) {
    // If cache version check fails, be conservative: mark as stale
    return false
  }
}

const invalidateCache = () => {
  globalTeamsCache = null
  cachedServerVersion = null
  try {
    if (typeof window !== 'undefined') {
      window.localStorage.removeItem(TEAMS_VERSION_KEY)
      // Do not remove server version; it reflects last seen server boot
    }
  } catch {
    // Ignore storage access errors
  }
}

export const useTeams = () => {
  const [state, setState] = useState<TeamsState>({
    teams: globalTeamsCache || [],
    loading: globalTeamsCache === null,
    error: null,
  })

  const fetchTeams = useCallback(async (): Promise<Team[]> => {
    // Return existing promise if fetch is already in progress
    if (globalCachePromise) {
      return globalCachePromise
    }

    // Check cache version before using cached data
    if (globalTeamsCache) {
      const isCacheValid = await checkCacheVersion()
      if (isCacheValid) {
        return globalTeamsCache
      } else {
        // Cache is stale, invalidate it
        invalidateCache()
      }
    }

    // Create new fetch promise
    globalCachePromise = (async () => {
      try {
        const response = await fetch('/api/teams')
        if (!response.ok) {
          throw new Error(`Failed to fetch teams: ${response.status} ${response.statusText}`)
        }
        const data = await response.json()
        const teams = data || []

        // Cache the result and update cache version
        globalTeamsCache = teams

        // Update cached server version
        try {
          const versionResponse = await fetch('/api/cache-version')
          if (versionResponse.ok) {
            const versionData = await versionResponse.json()
            cachedServerVersion = versionData.version
            // Persist both server version and teams cache version
            try {
              if (typeof window !== 'undefined') {
                window.localStorage.setItem(SERVER_VERSION_KEY, String(cachedServerVersion))
                window.localStorage.setItem(TEAMS_VERSION_KEY, String(cachedServerVersion))
              }
            } catch {
              // Ignore storage access errors
            }
          }
        } catch (error) {
          // If cache version update fails, continue without it
        }

        return teams
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

  const loadTeams = useCallback(async () => {
    if (globalTeamsCache) {
      // Check cache version before using cached data
      const isCacheValid = await checkCacheVersion()
      if (isCacheValid) {
        // Use cached data immediately
        setState({
          teams: globalTeamsCache,
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
      const teams = await fetchTeams()
      setState({
        teams,
        loading: false,
        error: null,
      })
    } catch (error) {
      setState({
        teams: [],
        loading: false,
        error: error instanceof Error ? error.message : 'Failed to fetch teams',
      })
    }
  }, [fetchTeams])

  // Load teams on first use
  useEffect(() => {
    if (!globalTeamsCache) {
      loadTeams()
    }
  }, [loadTeams])

  // Memoized team lookup function
  const getTeamName = useMemo(() => {
    const teamMap = new Map(state.teams.map(team => [team.id, team.name]))

    return (teamId: string | undefined | null): string | null => {
      if (!teamId) return null
      return teamMap.get(teamId) || null
    }
  }, [state.teams])

  // Memoized team lookup by ID function
  const getTeamById = useMemo(() => {
    const teamMap = new Map(state.teams.map(team => [team.id, team]))

    return (teamId: string | undefined | null): Team | null => {
      if (!teamId) return null
      return teamMap.get(teamId) || null
    }
  }, [state.teams])

  // Memoized team ID lookup by name function
  const getTeamIdByName = useMemo(() => {
    const teamNameMap = new Map(state.teams.map(team => [team.name.toLowerCase(), team.id]))

    return (teamName: string | undefined | null): string | null => {
      if (!teamName) return null
      return teamNameMap.get(teamName.toLowerCase()) || null
    }
  }, [state.teams])

  return {
    teams: state.teams,
    loading: state.loading,
    error: state.error,
    getTeamName,
    getTeamById,
    getTeamIdByName,
    refetch: loadTeams,
  }
}
