import Alert from '@mui/material/Alert'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Dialog from '@mui/material/Dialog'
import DialogActions from '@mui/material/DialogActions'
import DialogContent from '@mui/material/DialogContent'
import DialogTitle from '@mui/material/DialogTitle'
import Chip from '@mui/material/Chip'
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
import type { Equipment, EquipmentStatus, EquipmentWrite } from '../api/types'
import { ConfirmDialog } from '../components/ConfirmDialog'
import { StatusChip } from '../components/StatusChip'
import { EQUIPMENT_STATUSES, ROLE_CLINICAL_ADMIN } from '../constants'
import { useAuth } from '../auth/AuthContext'
import { useLookups } from '../hooks/useLookups'

const EMPTY: EquipmentWrite = {
  serial_number: '',
  model: '',
  status: 'available',
  charge_level: 100,
  facility_id: 0,
}

export function EquipmentPage() {
  const { user } = useAuth()
  const canWrite = user?.role === ROLE_CLINICAL_ADMIN
  const { hospitals, hospitalName } = useLookups()
  const [rows, setRows] = useState<Equipment[]>([])
  const [total, setTotal] = useState(0)
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('')
  const [facilityId, setFacilityId] = useState<number | ''>('')
  const [paginationModel, setPaginationModel] = useState<GridPaginationModel>({ page: 0, pageSize: 20 })
  const [sortModel, setSortModel] = useState<GridSortModel>([{ field: 'id', sort: 'asc' }])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [dialog, setDialog] = useState<Equipment | 'create' | null>(null)
  const [form, setForm] = useState<EquipmentWrite>(EMPTY)
  const [deleteId, setDeleteId] = useState<number | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const sort = sortModel[0]
      const result = await api.equipment.list({
        page: paginationModel.page + 1,
        page_size: paginationModel.pageSize,
        search,
        status: status || undefined,
        facility_id: facilityId === '' ? undefined : facilityId,
        sort_by: sort?.field,
        sort_dir: sort?.sort ?? 'asc',
      })
      setRows(result.items)
      setTotal(result.total)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load equipment')
    } finally {
      setLoading(false)
    }
  }, [paginationModel, sortModel, search, status, facilityId])

  useEffect(() => {
    void load()
  }, [load])

  const columns = useMemo<GridColDef<Equipment>[]>(
    () => [
      { field: 'id', headerName: 'ID', width: 70 },
      { field: 'serial_number', headerName: 'Serial', flex: 1, minWidth: 130 },
      { field: 'model', headerName: 'Model', flex: 1, minWidth: 140 },
      {
        field: 'status',
        headerName: 'Status',
        width: 140,
        renderCell: (params) => <StatusChip value={params.value} />,
      },
      {
        field: 'charge_level',
        headerName: 'Charge',
        width: 120,
        renderCell: (params) => (
          <Chip size="small" color={params.value < 20 ? 'error' : 'success'} label={`${params.value}%`} />
        ),
      },
      {
        field: 'facility_id',
        headerName: 'Hospital',
        flex: 1,
        minWidth: 160,
        valueGetter: (_value, row) => hospitalName(row.facility_id),
      },
      {
        field: 'actions',
        headerName: '',
        sortable: false,
        width: 160,
        hideable: false,
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
    [canWrite, hospitalName],
  )

  function openCreate() {
    setForm({ ...EMPTY, facility_id: hospitals[0]?.id ?? 0 })
    setDialog('create')
  }

  function openEdit(row: Equipment) {
    setForm({
      serial_number: row.serial_number,
      model: row.model,
      status: row.status,
      charge_level: row.charge_level,
      facility_id: row.facility_id,
    })
    setDialog(row)
  }

  async function save() {
    try {
      if (dialog === 'create') await api.equipment.create(form)
      else if (dialog) await api.equipment.update(dialog.id, form)
      setDialog(null)
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Save failed')
    }
  }

  async function confirmDelete() {
    if (deleteId == null) return
    try {
      await api.equipment.remove(deleteId)
      setDeleteId(null)
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Delete failed')
      setDeleteId(null)
    }
  }

  return (
    <Box>
      <Stack direction="row" sx={{ justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h5">Equipment</Typography>
        {canWrite ? (
          <Button variant="contained" onClick={openCreate}>
            Add device
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
          label="Search serial or model"
          value={search}
          onChange={(event) => {
            setSearch(event.target.value)
            setPaginationModel((model) => ({ ...model, page: 0 }))
          }}
          size="small"
        />
        <FormControl size="small" sx={{ minWidth: 160 }}>
          <InputLabel>Status</InputLabel>
          <Select
            label="Status"
            value={status}
            onChange={(event) => {
              setStatus(event.target.value)
              setPaginationModel((model) => ({ ...model, page: 0 }))
            }}
          >
            <MenuItem value="">All</MenuItem>
            {EQUIPMENT_STATUSES.map((value) => (
              <MenuItem key={value} value={value}>
                {value.replaceAll('_', ' ')}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
        <FormControl size="small" sx={{ minWidth: 200 }}>
          <InputLabel>Hospital</InputLabel>
          <Select
            label="Hospital"
            value={facilityId}
            onChange={(event) => {
              const next = String(event.target.value)
              setFacilityId(next === '' ? '' : Number(next))
              setPaginationModel((model) => ({ ...model, page: 0 }))
            }}
          >
            <MenuItem value="">All</MenuItem>
            {hospitals.map((row) => (
              <MenuItem key={row.id} value={row.id}>
                {row.name}
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
        <DialogTitle>{dialog === 'create' ? 'Add device' : 'Edit device'}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField
              label="Serial number"
              value={form.serial_number}
              onChange={(event) => setForm({ ...form, serial_number: event.target.value })}
            />
            <TextField
              label="Model"
              value={form.model}
              onChange={(event) => setForm({ ...form, model: event.target.value })}
            />
            <FormControl>
              <InputLabel>Status</InputLabel>
              <Select
                label="Status"
                value={form.status}
                onChange={(event) => setForm({ ...form, status: event.target.value as EquipmentStatus })}
              >
                {EQUIPMENT_STATUSES.map((value) => (
                  <MenuItem key={value} value={value}>
                    {value.replaceAll('_', ' ')}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <TextField
              label="Charge level"
              type="number"
              value={form.charge_level}
              onChange={(event) => setForm({ ...form, charge_level: Number(event.target.value) })}
            />
            <FormControl>
              <InputLabel>Hospital</InputLabel>
              <Select
                label="Hospital"
                value={form.facility_id || ''}
                onChange={(event) => setForm({ ...form, facility_id: Number(event.target.value) })}
              >
                {hospitals.map((row) => (
                  <MenuItem key={row.id} value={row.id}>
                    {row.name}
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
        title="Delete equipment"
        message="This device will be removed if it has no work orders."
        onClose={() => setDeleteId(null)}
        onConfirm={() => void confirmDelete()}
      />
    </Box>
  )
}
