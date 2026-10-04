import Alert from '@mui/material/Alert'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Dialog from '@mui/material/Dialog'
import DialogActions from '@mui/material/DialogActions'
import DialogContent from '@mui/material/DialogContent'
import DialogTitle from '@mui/material/DialogTitle'
import FormControl from '@mui/material/FormControl'
import InputLabel from '@mui/material/InputLabel'
import MenuItem from '@mui/material/MenuItem'
import Select from '@mui/material/Select'
import Stack from '@mui/material/Stack'
import TextField from '@mui/material/TextField'
import Typography from '@mui/material/Typography'
import { DataGrid } from '@mui/x-data-grid'
import type { GridColDef, GridPaginationModel, GridSortModel } from '@mui/x-data-grid'
import { useCallback, useEffect, useMemo, useState } from 'react'

import { api } from '../api/client'
import type { Hospital, HospitalWrite } from '../api/types'
import { ConfirmDialog } from '../components/ConfirmDialog'
import { ROLE_CLINICAL_ADMIN } from '../constants'
import { useAuth } from '../auth/AuthContext'
import { useLookups } from '../hooks/useLookups'

const EMPTY: HospitalWrite = {
  name: '',
  location_region: '',
  capacity: 50,
  supervisor_id: null,
}

export function HospitalsPage() {
  const { user } = useAuth()
  const canWrite = user?.role === ROLE_CLINICAL_ADMIN
  const { users, userName, reload } = useLookups()
  const [rows, setRows] = useState<Hospital[]>([])
  const [total, setTotal] = useState(0)
  const [search, setSearch] = useState('')
  const [paginationModel, setPaginationModel] = useState<GridPaginationModel>({ page: 0, pageSize: 20 })
  const [sortModel, setSortModel] = useState<GridSortModel>([{ field: 'id', sort: 'asc' }])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [dialog, setDialog] = useState<Hospital | 'create' | null>(null)
  const [form, setForm] = useState<HospitalWrite>(EMPTY)
  const [deleteId, setDeleteId] = useState<number | null>(null)

  const supervisors = users.filter((row) => row.role === ROLE_CLINICAL_ADMIN)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const sort = sortModel[0]
      const result = await api.hospitals.list({
        page: paginationModel.page + 1,
        page_size: paginationModel.pageSize,
        search,
        sort_by: sort?.field,
        sort_dir: sort?.sort ?? 'asc',
      })
      setRows(result.items)
      setTotal(result.total)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load hospitals')
    } finally {
      setLoading(false)
    }
  }, [paginationModel, sortModel, search])

  useEffect(() => {
    void load()
  }, [load])

  const columns = useMemo<GridColDef<Hospital>[]>(
    () => [
      { field: 'id', headerName: 'ID', width: 70 },
      { field: 'name', headerName: 'Name', flex: 1, minWidth: 180 },
      { field: 'location_region', headerName: 'Region', flex: 1, minWidth: 140 },
      { field: 'capacity', headerName: 'Capacity', width: 120 },
      {
        field: 'supervisor_id',
        headerName: 'Supervisor',
        flex: 1,
        minWidth: 160,
        valueGetter: (_value, row) => userName(row.supervisor_id),
      },
      {
        field: 'actions',
        headerName: '',
        sortable: false,
        width: 160,
        renderCell: (params) =>
          canWrite ? (
            <Stack direction="row" spacing={1}>
              <Button size="small" onClick={() => openEdit(params.row)}>
                Edit
              </Button>
              <Button size="small" color="error" onClick={() => setDeleteId(params.row.id)}>
                Delete
              </Button>
            </Stack>
          ) : null,
      },
    ],
    [canWrite, userName],
  )

  function openCreate() {
    setForm(EMPTY)
    setDialog('create')
  }

  function openEdit(row: Hospital) {
    setForm({
      name: row.name,
      location_region: row.location_region,
      capacity: row.capacity,
      supervisor_id: row.supervisor_id,
    })
    setDialog(row)
  }

  async function save() {
    try {
      if (dialog === 'create') await api.hospitals.create(form)
      else if (dialog) await api.hospitals.update(dialog.id, form)
      setDialog(null)
      await Promise.all([load(), reload()])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Save failed')
    }
  }

  async function confirmDelete() {
    if (deleteId == null) return
    try {
      await api.hospitals.remove(deleteId)
      setDeleteId(null)
      await Promise.all([load(), reload()])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Delete failed')
      setDeleteId(null)
    }
  }

  return (
    <Box>
      <Stack direction="row" sx={{ justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h5">Hospitals</Typography>
        {canWrite ? (
          <Button variant="contained" onClick={openCreate}>
            Add hospital
          </Button>
        ) : null}
      </Stack>
      {error ? (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      ) : null}
      <TextField
        label="Search name"
        size="small"
        value={search}
        sx={{ mb: 2 }}
        onChange={(event) => {
          setSearch(event.target.value)
          setPaginationModel((model) => ({ ...model, page: 0 }))
        }}
      />
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
        <DialogTitle>{dialog === 'create' ? 'Add hospital' : 'Edit hospital'}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField
              label="Name"
              value={form.name}
              onChange={(event) => setForm({ ...form, name: event.target.value })}
            />
            <TextField
              label="Region"
              value={form.location_region}
              onChange={(event) => setForm({ ...form, location_region: event.target.value })}
            />
            <TextField
              label="Capacity"
              type="number"
              value={form.capacity}
              onChange={(event) => setForm({ ...form, capacity: Number(event.target.value) })}
            />
            <FormControl>
              <InputLabel>Supervisor</InputLabel>
              <Select
                label="Supervisor"
                value={form.supervisor_id ?? ''}
                onChange={(event) => {
                  const next = String(event.target.value)
                  setForm({
                    ...form,
                    supervisor_id: next === '' ? null : Number(next),
                  })
                }}
              >
                <MenuItem value="">None</MenuItem>
                {supervisors.map((row) => (
                  <MenuItem key={row.id} value={row.id}>
                    {row.full_name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
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
        open={deleteId !== null}
        title="Delete hospital"
        message="This site will be removed if it has no equipment or staff."
        onClose={() => setDeleteId(null)}
        onConfirm={() => void confirmDelete()}
      />
    </Box>
  )
}
