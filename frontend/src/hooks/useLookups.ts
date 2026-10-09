import { useCallback, useEffect, useState } from 'react'

import { api, fetchAll } from '../api/client'
import type { Hospital, User } from '../api/types'
import { Permission } from '../permissions'
import { useAuth } from '../auth/AuthContext'

export function useLookups() {
  const { user, can } = useAuth()
  const [hospitals, setHospitals] = useState<Hospital[]>([])
  const [users, setUsers] = useState<User[]>([])

  const reload = useCallback(async () => {
    const hospitalRows = await fetchAll(api.hospitals.list)
    setHospitals(hospitalRows)
    if (can(Permission.userRead)) {
      setUsers(await fetchAll(api.users.list))
    } else if (user) {
      setUsers([user])
    }
  }, [user, can])

  useEffect(() => {
    void reload()
  }, [reload])

  const hospitalName = (id: number | null | undefined) => {
    if (id == null) return '—'
    return hospitals.find((row) => row.id === id)?.name ?? `#${id}`
  }

  const userName = (id: number | null | undefined) => {
    if (id == null) return '—'
    return users.find((row) => row.id === id)?.full_name ?? `#${id}`
  }

  return { hospitals, users, hospitalName, userName, reload }
}
