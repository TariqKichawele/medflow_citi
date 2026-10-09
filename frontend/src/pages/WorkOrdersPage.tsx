import Alert from '@mui/material/Alert'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Dialog from '@mui/material/Dialog'
import DialogActions from '@mui/material/DialogActions'
import DialogContent from '@mui/material/DialogContent'
import DialogTitle from '@mui/material/DialogTitle'
import Drawer from '@mui/material/Drawer'
import FormControl from '@mui/material/FormControl'
import InputLabel from '@mui/material/InputLabel'
import Link from '@mui/material/Link'
import MenuItem from '@mui/material/MenuItem'
import Select from '@mui/material/Select'
import Stack from '@mui/material/Stack'
import TextField from '@mui/material/TextField'
import Typography from '@mui/material/Typography'
import { DataGrid } from '@mui/x-data-grid'
import type { GridColDef, GridPaginationModel, GridSortModel } from '@mui/x-data-grid'
import { useCallback, useEffect, useMemo, useState } from 'react'

import { api, fetchAll, resolveFileUrl } from '../api/client'
import type {
  Equipment,
  Priority,
  ServiceReport,
  WorkOrder,
  WorkOrderStatus,
  WorkOrderWrite,
} from '../api/types'
import { ConfirmDialog } from '../components/ConfirmDialog'
import { StatusChip } from '../components/StatusChip'
import { PRIORITIES, ROLE_FIELD_TECHNICIAN, WORK_ORDER_STATUSES } from '../constants'
import { useAuth } from '../auth/AuthContext'
import { Permission } from '../permissions'
import { useDebouncedValue } from '../hooks/useDebouncedValue'
import { useLookups } from '../hooks/useLookups'

const EMPTY: WorkOrderWrite = {
  title: '',
  priority: 'medium',
  status: 'pending',
  equipment_id: 0,
  technician_id: 0,
}

function nextStatuses(current: WorkOrderStatus): WorkOrderStatus[] {
  if (current === 'pending') return ['in_progress']
  if (current === 'in_progress') return ['completed', 'failed']
  return []
}

export function WorkOrdersPage() {
  const { user, can } = useAuth()
  const canWrite = can(Permission.workOrderWrite)
  const canChangeStatus = can(Permission.workOrderStatus) && !canWrite
  const canReadAllOrders = can(Permission.workOrderRead)
  const canUploadReports = can(Permission.reportUpload)
  const { users, hospitals, userName, hospitalName } = useLookups()
  const [equipment, setEquipment] = useState<Equipment[]>([])
  const [rows, setRows] = useState<WorkOrder[]>([])
  const [total, setTotal] = useState(0)
  const [search, setSearch] = useState('')
  const debouncedSearch = useDebouncedValue(search)
  const [status, setStatus] = useState('')
  const [facilityId, setFacilityId] = useState<number | ''>('')
  const [paginationModel, setPaginationModel] = useState<GridPaginationModel>({ page: 0, pageSize: 20 })
  const [sortModel, setSortModel] = useState<GridSortModel>([{ field: 'id', sort: 'asc' }])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [dialog, setDialog] = useState<WorkOrder | 'create' | null>(null)
  const [form, setForm] = useState<WorkOrderWrite>(EMPTY)
  const [deleteId, setDeleteId] = useState<number | null>(null)
  const [selected, setSelected] = useState<WorkOrder | null>(null)
  const [reports, setReports] = useState<ServiceReport[]>([])
  const [notes, setNotes] = useState('')
  const [file, setFile] = useState<File | null>(null)

  const technicians = useMemo(
    () => users.filter((row) => row.role === ROLE_FIELD_TECHNICIAN || row.id === form.technician_id),
    [users, form.technician_id],
  )

  const loadEquipment = useCallback(async () => {
    setEquipment(await fetchAll(api.equipment.list))
  }, [])

  useEffect(() => {
    void loadEquipment()
  }, [loadEquipment])

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const sort = sortModel[0]
      const result = await api.workOrders.list({
        page: paginationModel.page + 1,
        page_size: paginationModel.pageSize,
        search: debouncedSearch,
        status: status || undefined,
        facility_id: facilityId === '' ? undefined : facilityId,
        sort_by: sort?.field,
        sort_dir: sort?.sort ?? 'asc',
      })
      setRows(result.items)
      setTotal(result.total)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load work orders')
    } finally {
      setLoading(false)
    }
  }, [paginationModel, sortModel, debouncedSearch, status, facilityId])

  useEffect(() => {
    void load()
  }, [load])

  const loadReports = useCallback(async (order: WorkOrder) => {
    const result = await api.workOrders.reports(order.id)
    setReports(result.items)
  }, [])

  async function openReports(order: WorkOrder) {
    setSelected(order)
    setNotes('')
    setFile(null)
    await loadReports(order)
  }

  async function advance(order: WorkOrder, next: WorkOrderStatus) {
    try {
      await api.workOrders.update(order.id, { status: next })
      await load()
      if (selected?.id === order.id) {
        const updated = { ...order, status: next }
        setSelected(updated)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Status update failed')
    }
  }

  async function upload() {
    if (!selected || !file) return
    try {
      await api.workOrders.uploadReport(selected.id, file, notes)
      setFile(null)
      setNotes('')
      await loadReports(selected)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed')
    }
  }

  const columns = useMemo<GridColDef<WorkOrder>[]>(
    () => [
      { field: 'id', headerName: 'ID', width: 70 },
      { field: 'title', headerName: 'Title', flex: 1.4, minWidth: 180 },
      {
        field: 'priority',
        headerName: 'Priority',
        width: 120,
        renderCell: (params) => <StatusChip value={params.value} />,
      },
      {
        field: 'status',
        headerName: 'Status',
        width: 140,
        renderCell: (params) => <StatusChip value={params.value} />,
      },
      {
        field: 'equipment_id',
        headerName: 'Device',
        flex: 1,
        minWidth: 140,
        valueGetter: (_value, row) => {
          const device = equipment.find((item) => item.id === row.equipment_id)
          return device ? `${device.serial_number} (${hospitalName(device.facility_id)})` : `#${row.equipment_id}`
        },
      },
      {
        field: 'technician_id',
        headerName: 'Technician',
        flex: 1,
        minWidth: 140,
        valueGetter: (_value, row) => userName(row.technician_id),
      },
      {
        field: 'actions',
        headerName: '',
        sortable: false,
        width: 280,
        renderCell: (params) => (
          <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap' }}>
            {can(Permission.reportRead) ? (
              <Button size="small" onClick={() => void openReports(params.row)}>
                Reports
              </Button>
            ) : null}
            {canWrite ? (
              <>
                <Button size="small" onClick={() => openEdit(params.row)}>
                  Edit
                </Button>
                <Button size="small" color="error" onClick={() => setDeleteId(params.row.id)}>
                  Delete
                </Button>
              </>
            ) : null}
            {canChangeStatus && (canReadAllOrders || params.row.technician_id === user?.id)
              ? nextStatuses(params.row.status).map((next) => (
                  <Button key={next} size="small" variant="outlined" onClick={() => void advance(params.row, next)}>
                    {next.replaceAll('_', ' ')}
                  </Button>
                ))
              : null}
          </Stack>
        ),
      },
    ],
    [can, canWrite, canChangeStatus, canReadAllOrders, user, equipment, hospitalName, userName],
  )

  function openCreate() {
    setForm({
      ...EMPTY,
      equipment_id: equipment[0]?.id ?? 0,
      technician_id: technicians[0]?.id ?? 0,
    })
    setDialog('create')
  }

  function openEdit(row: WorkOrder) {
    setForm({
      title: row.title,
      priority: row.priority,
      status: row.status,
      equipment_id: row.equipment_id,
      technician_id: row.technician_id,
    })
    setDialog(row)
  }

  async function save() {
    try {
      if (dialog === 'create') await api.workOrders.create(form)
      else if (dialog) await api.workOrders.update(dialog.id, form)
      setDialog(null)
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Save failed')
    }
  }

  async function confirmDelete() {
    if (deleteId == null) return
    try {
      await api.workOrders.remove(deleteId)
      setDeleteId(null)
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Delete failed')
      setDeleteId(null)
    }
  }

  const canUpload = Boolean(
    selected &&
      user &&
      canUploadReports &&
      (canReadAllOrders || selected.technician_id === user.id),
  )

  return (
    <Box>
      <Stack direction="row" sx={{ justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h5">Work orders</Typography>
        {canWrite ? (
          <Button variant="contained" onClick={openCreate}>
            Create order
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
          label="Search title, serial, or model"
          size="small"
          value={search}
          onChange={(event) => {
            setSearch(event.target.value)
            setPaginationModel((model) => (model.page === 0 ? model : { ...model, page: 0 }))
          }}
        />
        <FormControl size="small" sx={{ minWidth: 180 }}>
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
            {WORK_ORDER_STATUSES.map((value) => (
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
              setPaginationModel((model) => (model.page === 0 ? model : { ...model, page: 0 }))
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
        filterMode="server"
        paginationModel={paginationModel}
        onPaginationModelChange={setPaginationModel}
        sortModel={sortModel}
        onSortModelChange={setSortModel}
        pageSizeOptions={[10, 20, 50]}
        disableRowSelectionOnClick
        autoHeight
      />
      <Dialog open={dialog !== null} onClose={() => setDialog(null)} fullWidth maxWidth="sm">
        <DialogTitle>{dialog === 'create' ? 'Create work order' : 'Edit work order'}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField
              label="Title"
              value={form.title}
              onChange={(event) => setForm({ ...form, title: event.target.value })}
            />
            <FormControl>
              <InputLabel>Priority</InputLabel>
              <Select
                label="Priority"
                value={form.priority}
                onChange={(event) => setForm({ ...form, priority: event.target.value as Priority })}
              >
                {PRIORITIES.map((value) => (
                  <MenuItem key={value} value={value}>
                    {value}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <FormControl>
              <InputLabel>Status</InputLabel>
              <Select
                label="Status"
                value={form.status}
                onChange={(event) => setForm({ ...form, status: event.target.value as WorkOrderStatus })}
              >
                {WORK_ORDER_STATUSES.map((value) => (
                  <MenuItem key={value} value={value}>
                    {value.replaceAll('_', ' ')}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <FormControl>
              <InputLabel>Equipment</InputLabel>
              <Select
                label="Equipment"
                value={form.equipment_id || ''}
                onChange={(event) => setForm({ ...form, equipment_id: Number(event.target.value) })}
              >
                {equipment.map((row) => (
                  <MenuItem key={row.id} value={row.id}>
                    {row.serial_number} · {hospitalName(row.facility_id)}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <FormControl>
              <InputLabel>Technician</InputLabel>
              <Select
                label="Technician"
                value={form.technician_id || ''}
                onChange={(event) => setForm({ ...form, technician_id: Number(event.target.value) })}
              >
                {technicians.map((row) => (
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
      <Drawer anchor="right" open={selected !== null} onClose={() => setSelected(null)}>
        <Box sx={{ width: { xs: 320, sm: 420 }, p: 3 }}>
          <Typography variant="h6">{selected?.title}</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Service reports
          </Typography>
          {reports.length === 0 ? (
            <Typography variant="body2">No reports yet.</Typography>
          ) : (
            reports.map((report) => (
              <Box key={report.id} sx={{ mb: 1.5 }}>
                <Link href={resolveFileUrl(report.file_url)} target="_blank" rel="noreferrer">
                  {decodeURIComponent((report.file_url.split('/').pop() ?? 'report').split('?')[0])}
                </Link>
                <Typography variant="caption" sx={{ display: 'block' }}>
                  {new Date(report.created_at).toLocaleString()} {report.notes ? `· ${report.notes}` : ''}
                </Typography>
              </Box>
            ))
          )}
          {canUpload ? (
            <Stack spacing={2} sx={{ mt: 3 }}>
              <Button variant="outlined" component="label">
                Choose file
                <input
                  hidden
                  type="file"
                  accept=".txt,.pdf,.png,.jpg,.jpeg,.gif,.webp"
                  onChange={(event) => setFile(event.target.files?.[0] ?? null)}
                />
              </Button>
              <Typography variant="body2">{file ? file.name : 'PDF, images, or .txt'}</Typography>
              <TextField
                label="Notes"
                multiline
                minRows={2}
                value={notes}
                onChange={(event) => setNotes(event.target.value)}
              />
              <Button variant="contained" disabled={!file} onClick={() => void upload()}>
                Upload report
              </Button>
            </Stack>
          ) : null}
        </Box>
      </Drawer>
      <ConfirmDialog
        open={deleteId !== null}
        title="Delete work order"
        message="This order will be removed if it has no service reports."
        onClose={() => setDeleteId(null)}
        onConfirm={() => void confirmDelete()}
      />
    </Box>
  )
}
