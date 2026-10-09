import Alert from '@mui/material/Alert'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Checkbox from '@mui/material/Checkbox'
import Chip from '@mui/material/Chip'
import Dialog from '@mui/material/Dialog'
import DialogActions from '@mui/material/DialogActions'
import DialogContent from '@mui/material/DialogContent'
import DialogTitle from '@mui/material/DialogTitle'
import FormControlLabel from '@mui/material/FormControlLabel'
import FormGroup from '@mui/material/FormGroup'
import Stack from '@mui/material/Stack'
import Table from '@mui/material/Table'
import TableBody from '@mui/material/TableBody'
import TableCell from '@mui/material/TableCell'
import TableHead from '@mui/material/TableHead'
import TableRow from '@mui/material/TableRow'
import TextField from '@mui/material/TextField'
import Typography from '@mui/material/Typography'
import { useCallback, useEffect, useState } from 'react'

import { api } from '../api/client'
import type { RoleRecord } from '../api/types'
import { useAuth } from '../auth/AuthContext'
import { Permission } from '../permissions'

export function RolesPage() {
  const { can } = useAuth()
  const canManage = can(Permission.roleManage)
  const [roles, setRoles] = useState<RoleRecord[]>([])
  const [catalog, setCatalog] = useState<string[]>([])
  const [error, setError] = useState<string | null>(null)
  const [open, setOpen] = useState(false)
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [selected, setSelected] = useState<string[]>([])

  const load = useCallback(async () => {
    try {
      const [roleRows, permissionCatalog] = await Promise.all([api.roles.list(), api.roles.permissions()])
      setRoles(roleRows)
      setCatalog(permissionCatalog.permissions)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load roles')
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  function toggle(permission: string) {
    setSelected((current) =>
      current.includes(permission) ? current.filter((item) => item !== permission) : [...current, permission],
    )
  }

  async function createRole() {
    try {
      await api.roles.create({ name, description, permissions: selected })
      setOpen(false)
      setName('')
      setDescription('')
      setSelected([])
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not create role')
    }
  }

  return (
    <Box>
      <Stack direction="row" sx={{ justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h5">Roles</Typography>
        {canManage ? (
          <Button variant="contained" onClick={() => setOpen(true)}>
            Add role
          </Button>
        ) : null}
      </Stack>
      {error ? (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      ) : null}
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>Role</TableCell>
            <TableCell>Description</TableCell>
            <TableCell>Permissions</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {roles.map((role) => (
            <TableRow key={role.id}>
              <TableCell sx={{ whiteSpace: 'nowrap' }}>{role.name.replaceAll('_', ' ')}</TableCell>
              <TableCell>{role.description}</TableCell>
              <TableCell>
                <Stack direction="row" spacing={0.5} useFlexGap sx={{ flexWrap: 'wrap' }}>
                  {role.permissions.map((permission) => (
                    <Chip key={permission} size="small" label={permission} />
                  ))}
                </Stack>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      <Dialog open={open} onClose={() => setOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>Add role</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField
              label="Name"
              value={name}
              helperText="Lowercase letters, numbers, and underscores"
              onChange={(event) => setName(event.target.value)}
            />
            <TextField
              label="Description"
              value={description}
              onChange={(event) => setDescription(event.target.value)}
            />
            <FormGroup>
              {catalog.map((permission) => (
                <FormControlLabel
                  key={permission}
                  control={<Checkbox checked={selected.includes(permission)} onChange={() => toggle(permission)} />}
                  label={permission}
                />
              ))}
            </FormGroup>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpen(false)}>Cancel</Button>
          <Button variant="contained" disabled={!name.trim()} onClick={() => void createRole()}>
            Save
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
