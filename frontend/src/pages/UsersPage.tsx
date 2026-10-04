import Alert from '@mui/material/Alert'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Dialog from '@mui/material/Dialog'
import DialogActions from '@mui/material/DialogActions'
import DialogContent from '@mui/material/DialogContent'
import DialogTitle from '@mui/material/DialogTitle'
import FormControl from '@mui/material/FormControl'
import FormControlLabel from '@mui/material/FormControlLabel'
import InputLabel from '@mui/material/InputLabel'
import MenuItem from '@mui/material/MenuItem'
import Select from '@mui/material/Select'
import Stack from '@mui/material/Stack'
import Switch from '@mui/material/Switch'
import TextField from '@mui/material/TextField'
import Typography from '@mui/material/Typography'
import { DataGrid } from '@mui/x-data-grid'
import type { GridColDef, GridPaginationModel, GridSortModel } from '@mui/x-data-grid'
import { useCallback, useEffect, useMemo, useState } from 'react'

import { api } from '../api/client'
import type { Role, User, UserWrite } from '../api/types'
import { ConfirmDialog } from '../components/ConfirmDialog'
import { StatusChip } from '../components/StatusChip'
import { ROLE_CLINICAL_ADMIN, ROLE_FIELD_TECHNICIAN, ROLES } from '../constants'
import { useAuth } from '../auth/AuthContext'
import { useLookups } from '../hooks/useLookups'

const EMPTY: UserWrite = {
  email: '',
  full_name: '',
  role: 'field_technician',
  password: '',
  facility_id: null,
  reports_to_id: null,
  is_active: true,
}

export function UsersPage() {
  const { user } = useAuth()
  const canWrite = user?.role === ROLE_CLINICAL_ADMIN
  const { hospitals, hospitalName, userName, reload, users } = useLookups()
  const [rows, setRows] = useState<User[]>([])
  const [total, setTotal] = useState(0)
  const [search, setSearch] = useState('')
  const [role, setRole] = useState('')
  const [paginationModel, setPaginationModel] = useState<GridPaginationModel>({ page: 0, pageSize: 20 })
  const [sortModel, setSortModel] = useState<GridSortModel>([{ field: 'id', sort: 'asc' }])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [dialog, setDialog] = useState<User | 'create' | null>(null)
  const [form, setForm] = useState<UserWrite>(EMPTY)
  const [deactivateId, setDeactivateId] = useState<number | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const sort = sortModel[0]
      const result = await api.users.list({
        page: paginationModel.page + 1,
        page_size: paginationModel.pageSize,
        search,
        role: role || undefined,
        sort_by: sort?.field,
        sort_dir: sort?.sort ?? 'asc',
      })
      setRows(result.items)
      setTotal(result.total)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load users')
    } finally {
      setLoading(false)
    }
  }, [paginationModel, sortModel, search, role])

  useEffect(() => {
    void load()
  }, [load])

  const columns = useMemo<GridColDef<User>[]>(
    () => [
      { field: 'id', headerName: 'ID', width: 70 },
      { field: 'full_name', headerName: 'Name', flex: 1, minWidth: 160 },
      { field: 'email', headerName: 'Email', flex: 1.2, minWidth: 200 },
      {
        field: 'role',
        headerName: 'Role',
        width: 160,
        renderCell: (params) => <StatusChip value={params.value} />,
      },
      {
        field: 'facility_id',
        headerName: 'Hospital',
        flex: 1,
        minWidth: 140,
        valueGetter: (_value, row) => hospitalName(row.facility_id),
      },
      {
        field: 'reports_to_id',
        headerName: 'Reports to',
        flex: 1,
        minWidth: 140,
        valueGetter: (_value, row) => userName(row.reports_to_id),
      },
      {
        field: 'is_active',
        headerName: 'Active',
        width: 100,
        valueGetter: (_value, row) => (row.is_active ? 'yes' : 'no'),
      },
      {
        field: 'actions',
        headerName: '',
        sortable: false,
        width: 180,
        renderCell: (params) =>
          canWrite ? (
            <Stack direction="row" spacing={1}>
              <Button size="small" onClick={() => openEdit(params.row)}>
                Edit
              </Button>
              <Button size="small" color="error" onClick={() => setDeactivateId(params.row.id)}>
                Deactivate
              </Button>
            </Stack>
          ) : null,
      },
    ],
    [canWrite, hospitalName, userName],
  )

  function openCreate() {
    setForm({ ...EMPTY, facility_id: hospitals[0]?.id ?? null })
    setDialog('create')
  }

  function openEdit(row: User) {
    setForm({
      email: row.email,
      full_name: row.full_name,
      role: row.role,
      password: '',
      facility_id: row.facility_id,
      reports_to_id: row.reports_to_id,
      is_active: row.is_active,
    })
    setDialog(row)
  }

  async function save() {
    try {
      const payload: Partial<UserWrite> = { ...form }
      if (!payload.password) delete payload.password
      if (dialog === 'create') {
        if (!form.password) throw new Error('Password is required')
        await api.users.create(form)
      } else if (dialog) {
        await api.users.update(dialog.id, payload)
      }
      setDialog(null)
      await Promise.all([load(), reload()])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Save failed')
    }
  }

  async function confirmDeactivate() {
    if (deactivateId == null) return
    try {
      await api.users.deactivate(deactivateId)
      setDeactivateId(null)
      await Promise.all([load(), reload()])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Deactivate failed')
      setDeactivateId(null)
    }
  }

  return (
    <Box>
      <Stack direction="row" sx={{ justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h5">Users</Typography>
        {canWrite ? (
          <Button variant="contained" onClick={openCreate}>
            Add user
          </Button>
        ) : null}
      </Stack>
      {error ? (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      ) : null}
      <Stack direction={{ xs: 'column', md: 'row' }} spacing={2} sx={{ mb: 2 }}>
        <TextField
          label="Search name or email"
          size="small"
          value={search}
          onChange={(event) => {
            setSearch(event.target.value)
            setPaginationModel((model) => ({ ...model, page: 0 }))
          }}
        />
        <FormControl size="small" sx={{ minWidth: 180 }}>
          <InputLabel>Role</InputLabel>
          <Select
            label="Role"
            value={role}
            onChange={(event) => {
              setRole(event.target.value)
              setPaginationModel((model) => ({ ...model, page: 0 }))
            }}
          >
            <MenuItem value="">All</MenuItem>
            {ROLES.map((value) => (
              <MenuItem key={value} value={value}>
                {value.replaceAll('_', ' ')}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      </Stack>
      <DataGrid
        rows={rows}
        columns={columns}
        rowCount={total}
        loading={loading}
        paginationMode="server"
        sortingMode="server"
        paginationModel={paginationModel}
        onPaginationModelChange={setPaginationModel}
        sortModel={sortModel}
        onSortModelChange={setSortModel}
        pageSizeOptions={[10, 20, 50]}
        disableRowSelectionOnClick
        autoHeight
      />
      <Dialog open={dialog !== null} onClose={() => setDialog(null)} fullWidth maxWidth="sm">
        <DialogTitle>{dialog === 'create' ? 'Add user' : 'Edit user'}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField
              label="Full name"
              value={form.full_name}
              onChange={(event) => setForm({ ...form, full_name: event.target.value })}
            />
            <TextField
              label="Email"
              type="email"
              value={form.email}
              onChange={(event) => setForm({ ...form, email: event.target.value })}
            />
            <TextField
              label={dialog === 'create' ? 'Password' : 'New password (optional)'}
              type="password"
              value={form.password ?? ''}
              onChange={(event) => setForm({ ...form, password: event.target.value })}
            />
            <FormControl>
              <InputLabel>Role</InputLabel>
              <Select
                label="Role"
                value={form.role}
                onChange={(event) => setForm({ ...form, role: event.target.value as Role })}
              >
                {ROLES.map((value) => (
                  <MenuItem key={value} value={value}>
                    {value.replaceAll('_', ' ')}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <FormControl>
              <InputLabel>Hospital</InputLabel>
              <Select
                label="Hospital"
                value={form.facility_id ?? ''}
                onChange={(event) => {
                  const next = String(event.target.value)
                  setForm({
                    ...form,
                    facility_id: next === '' ? null : Number(next),
                  })
                }}
              >
                {form.role === ROLE_FIELD_TECHNICIAN ? null : <MenuItem value="">None</MenuItem>}
                {hospitals.map((row) => (
                  <MenuItem key={row.id} value={row.id}>
                    {row.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <FormControl>
              <InputLabel>Reports to</InputLabel>
              <Select
                label="Reports to"
                value={form.reports_to_id ?? ''}
                onChange={(event) => {
                  const next = String(event.target.value)
                  setForm({
                    ...form,
                    reports_to_id: next === '' ? null : Number(next),
                  })
                }}
              >
                <MenuItem value="">None</MenuItem>
                {users
                  .filter((row) => row.role === ROLE_CLINICAL_ADMIN)
                  .map((row) => (
                    <MenuItem key={row.id} value={row.id}>
                      {row.full_name}
                    </MenuItem>
                  ))}
              </Select>
            </FormControl>
            <FormControlLabel
              control={
                <Switch
                  checked={form.is_active}
                  onChange={(event) => setForm({ ...form, is_active: event.target.checked })}
                />
              }
              label="Active"
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialog(null)}>Cancel</Button>
          <Button variant="contained" onClick={() => void save()}>
            Save
          </Button>
        </DialogActions>
      </Dialog>
      <ConfirmDialog
        open={deactivateId !== null}
        title="Deactivate user"
        message="This account will no longer be able to sign in."
        onClose={() => setDeactivateId(null)}
        onConfirm={() => void confirmDeactivate()}
      />
    </Box>
  )
}
