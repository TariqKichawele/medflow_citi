import Alert from '@mui/material/Alert'
import Box from '@mui/material/Box'
import Card from '@mui/material/Card'
import CardContent from '@mui/material/CardContent'
import FormControl from '@mui/material/FormControl'
import Grid from '@mui/material/Grid'
import InputLabel from '@mui/material/InputLabel'
import MenuItem from '@mui/material/MenuItem'
import Select from '@mui/material/Select'
import Table from '@mui/material/Table'
import TableBody from '@mui/material/TableBody'
import TableCell from '@mui/material/TableCell'
import TableHead from '@mui/material/TableHead'
import TableRow from '@mui/material/TableRow'
import Typography from '@mui/material/Typography'
import { useEffect, useMemo, useState, type ReactNode } from 'react'

import { api } from '../api/client'
import type { AnalyticsSummary, ReportingLineItem } from '../api/types'
import { useLookups } from '../hooks/useLookups'
import { ROLE_CLINICAL_ADMIN } from '../constants'

function pct(value: number) {
  return `${Math.round(value * 1000) / 10}%`
}

export function DashboardPage() {
  const { users } = useLookups()
  const [data, setData] = useState<AnalyticsSummary | null>(null)
  const [lines, setLines] = useState<ReportingLineItem[]>([])
  const [supervisorId, setSupervisorId] = useState<number | ''>('')
  const [error, setError] = useState<string | null>(null)

  const supervisors = useMemo(
    () => users.filter((row) => row.role === ROLE_CLINICAL_ADMIN),
    [users],
  )

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const summary = await api.analytics.summary()
        if (!cancelled) {
          setData(summary)
          setLines(summary.reporting_lines)
          setError(null)
        }
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Failed to load analytics')
      }
    }
    void load()
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    if (supervisorId === '') {
      if (data) setLines(data.reporting_lines)
      return
    }
    let cancelled = false
    api.analytics
      .reportingLines(supervisorId)
      .then((response) => {
        if (!cancelled) setLines(response.items)
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Failed to load reporting lines')
      })
    return () => {
      cancelled = true
    }
  }, [supervisorId, data])

  if (error) return <Alert severity="error">{error}</Alert>
  if (!data) return <Typography>Loading dashboard…</Typography>

  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        Clinical operations dashboard
      </Typography>
      <Grid container spacing={2}>
        <Grid size={{ xs: 12, md: 6, lg: 4 }}>
          <MetricCard
            title="Low charge alert"
            value={String(data.low_charge.length)}
            caption="Available or in-use devices below 20%"
          >
            <SimpleTable
              headers={['Serial', 'Hospital', 'Charge']}
              rows={data.low_charge.slice(0, 6).map((row) => [
                row.serial_number,
                row.hospital_name,
                `${row.charge_level}%`,
              ])}
            />
          </MetricCard>
        </Grid>
        <Grid size={{ xs: 12, md: 6, lg: 4 }}>
          <MetricCard
            title="Co-location discrepancies"
            value={String(data.colocation_discrepancies.count)}
            caption="Active orders where technician is at a different hospital"
          >
            <SimpleTable
              headers={['Device', 'Hospital', 'Technician']}
              rows={data.colocation_discrepancies.items.slice(0, 6).map((row) => [
                row.serial_number,
                row.equipment_hospital,
                row.technician_name,
              ])}
            />
          </MetricCard>
        </Grid>
        <Grid size={{ xs: 12, md: 6, lg: 4 }}>
          <MetricCard
            title="Maintenance flags"
            value={String(data.maintenance_flags.length)}
            caption="Hospitals with more than 30% of devices in maintenance"
          >
            <SimpleTable
              headers={['Hospital', 'Ratio']}
              rows={data.maintenance_flags.map((row) => [row.hospital_name, pct(row.maintenance_ratio)])}
            />
          </MetricCard>
        </Grid>
        <Grid size={{ xs: 12, md: 6 }}>
          <MetricCard title="Reliability by model" value="" caption="Completed vs failed work orders">
            <SimpleTable
              headers={['Model', 'Completed', 'Failed', 'Rate']}
              rows={data.reliability.map((row) => [
                row.model,
                String(row.completed),
                String(row.failed),
                pct(row.completion_rate),
              ])}
            />
          </MetricCard>
        </Grid>
        <Grid size={{ xs: 12, md: 6 }}>
          <MetricCard
            title="Reporting lines"
            value={String(lines.reduce((sum, row) => sum + row.technicians_with_active_orders, 0))}
            caption="Technicians with active work orders, by supervisor"
          >
            <FormControl size="small" fullWidth sx={{ mb: 1 }}>
              <InputLabel>Supervisor</InputLabel>
              <Select
                label="Supervisor"
                value={supervisorId}
                onChange={(event) => {
                  const next = String(event.target.value)
                  setSupervisorId(next === '' ? '' : Number(next))
                }}
              >
                <MenuItem value="">All supervisors</MenuItem>
                {supervisors.map((row) => (
                  <MenuItem key={row.id} value={row.id}>
                    {row.full_name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <SimpleTable
              headers={['Supervisor', 'Techs with active orders']}
              rows={lines.map((row) => [row.supervisor_name, String(row.technicians_with_active_orders)])}
            />
          </MetricCard>
        </Grid>
      </Grid>
    </Box>
  )
}

function MetricCard({
  title,
  value,
  caption,
  children,
}: {
  title: string
  value: string
  caption: string
  children: ReactNode
}) {
  return (
    <Card>
      <CardContent>
        <Typography variant="subtitle2" color="text.secondary">
          {title}
        </Typography>
        {value ? (
          <Typography variant="h4" sx={{ my: 0.5 }}>
            {value}
          </Typography>
        ) : null}
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
          {caption}
        </Typography>
        {children}
      </CardContent>
    </Card>
  )
}

function SimpleTable({ headers, rows }: { headers: string[]; rows: string[][] }) {
  if (rows.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary">
        No rows
      </Typography>
    )
  }
  return (
    <Table size="small">
      <TableHead>
        <TableRow>
          {headers.map((header) => (
            <TableCell key={header}>{header}</TableCell>
          ))}
        </TableRow>
      </TableHead>
      <TableBody>
        {rows.map((row, index) => (
          <TableRow key={index}>
            {row.map((cell, cellIndex) => (
              <TableCell key={cellIndex}>{cell}</TableCell>
            ))}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}
