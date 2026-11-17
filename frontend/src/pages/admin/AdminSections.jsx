import { useCallback, useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { RefreshCw, Check, X, Eye, Plus, Bell, Search } from 'lucide-react'
import api from '../../services/api'

const configs = {
  applications: {
    title: 'Rental Applications',
    endpoint: '/applications',
    key: 'applications',
    columns: [
      ['applicant_name', 'Applicant'],
      ['property_name', 'Property'],
      ['property_location', 'Location'],
      ['monthly_rent', 'Monthly rent'],
      ['application_date', 'Date'],
      ['application_status', 'Status'],
    ],
  },
  tenancies: {
    title: 'Tenancy Management',
    endpoint: '/tenancies',
    key: 'tenancies',
    columns: [
      ['tenant_name', 'Tenant'],
      ['property_name', 'Property'],
      ['property_location', 'Location'],
      ['start_date', 'Start date'],
      ['end_date', 'End date'],
      ['monthly_rent', 'Monthly rent'],
      ['tenancy_status', 'Status'],
    ],
  },
  payments: {
    title: 'Payment Management',
    endpoint: '/payments',
    key: 'payments',
    columns: [
      ['tenant_name', 'Tenant'],
      ['property_name', 'Property'],
      ['amount_due', 'Amount due'],
      ['amount_paid', 'Amount paid'],
      ['balance', 'Balance'],
      ['payment_date', 'Date'],
      ['payment_status', 'Status'],
    ],
  },
  maintenance: {
    title: 'Maintenance Requests',
    endpoint: '/maintenance',
    key: 'maintenance_requests',
    columns: [
      ['property_name', 'Property'],
      ['tenant_name', 'Tenant'],
      ['description', 'Issue'],
      ['priority', 'Priority'],
      ['request_date', 'Date'],
      ['request_status', 'Status'],
    ],
  },
  notifications: {
    title: 'Notifications',
    endpoint: '/notifications',
    key: 'notifications',
    columns: [
      ['message', 'Message'],
      ['notification_type', 'Type'],
      ['created_at', 'Date'],
      ['read_status', 'Read status'],
    ],
  },
}

const money = value =>
  value == null ? '—' : `KES ${Number(value).toLocaleString('en-KE')}`

const date = value =>
  value ? new Date(value).toLocaleDateString() : '—'

function Status({ value }) {
  const status = String(value ?? 'unknown').toLowerCase()
  const color =
    ['approved', 'paid', 'active', 'resolved'].includes(status) ? '#23845b' :
    ['rejected', 'terminated', 'overdue'].includes(status) ? '#b94b4b' :
    '#a47731'

  return (
    <span style={{
      color,
      background: `${color}16`,
      borderRadius: 20,
      padding: '5px 10px',
      fontSize: 12,
      fontWeight: 700,
      textTransform: 'capitalize',
      whiteSpace: 'nowrap',
    }}>
      {String(value ?? 'Unknown').replaceAll('_', ' ')}
    </span>
  )
}

export default function AdminSections() {
  const { section } = useParams()
  const config = configs[section]
  const [rows, setRows] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState('all')
  const [busy, setBusy] = useState(false)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({
    tenancy_id: '',
    amount_paid: '',
    amount_due: '',
    payment_method: 'M-Pesa',
    transaction_reference: '',
    payment_date: new Date().toISOString().slice(0, 10),
    application_id: '',
    start_date: new Date().toISOString().slice(0, 10),
    end_date: '',
    monthly_rent: '',
  })

  const loadData = useCallback(async () => {
    if (!config) return
    setLoading(true)
    setError('')
    try {
      const response = await api.get(config.endpoint)
      setRows(response.data[config.key] || [])
    } catch (err) {
      setError(err.response?.data?.message || 'Unable to load records. Please try again.')
    } finally {
      setLoading(false)
    }
  }, [config])

  useEffect(() => {
    loadData()
  }, [loadData])

  if (!config) {
    return <div className="content-panel"><h2>Section not found</h2></div>
  }

  const updateForm = event =>
    setForm(previous => ({ ...previous, [event.target.name]: event.target.value }))

  const act = async (callback, successMessage) => {
    setBusy(true)
    setError('')
    try {
      await callback()
      await loadData()
      setShowForm(false)
      window.alert(successMessage)
    } catch (err) {
      setError(err.response?.data?.message || 'The action could not be completed.')
    } finally {
      setBusy(false)
    }
  }

  const reviewApplication = (item, status) => {
    const comments = window.prompt(`Review comments for this ${status} application:`, '')
    if (comments === null) return

    act(
      () => api.patch(`/applications/${item.application_id}/review`, {
        application_status: status,
        review_comments: comments,
      }),
      `Application ${status}.`
    )
  }

  const createTenancy = item => {
    setForm(previous => ({
      ...previous,
      application_id: String(item.application_id),
      monthly_rent: String(item.monthly_rent || ''),
    }))
    setShowForm(true)
  }

  const submitTenancy = event => {
    event.preventDefault()
    act(
      () => api.post('/tenancies', {
        application_id: Number(form.application_id),
        start_date: form.start_date,
        end_date: form.end_date || null,
        monthly_rent: Number(form.monthly_rent),
      }),
      'Tenancy created successfully.'
    )
  }

  const submitPayment = event => {
    event.preventDefault()
    act(
      () => api.post('/payments', {
        tenancy_id: Number(form.tenancy_id),
        amount_due: form.amount_due ? Number(form.amount_due) : undefined,
        amount_paid: Number(form.amount_paid),
        payment_method: form.payment_method,
        transaction_reference: form.transaction_reference,
        payment_date: form.payment_date,
      }),
      'Payment recorded successfully.'
    )
  }

  const updateMaintenance = item => {
    const status = window.prompt(
      'Enter status: pending, in_progress, resolved or rejected',
      item.request_status
    )
    if (!status) return

    const priority = window.prompt(
      'Enter priority: low, normal, high or urgent',
      item.priority
    )
    if (!priority) return

    const resolution = status === 'resolved'
      ? window.prompt('Enter resolution details:')
      : item.resolution_details || ''

    if (status === 'resolved' && !resolution) return

    act(
      () => api.patch(`/maintenance/${item.request_id}`, {
        request_status: status,
        priority,
        resolution_details: resolution,
      }),
      'Maintenance request updated.'
    )
  }

  const markRead = item =>
    act(
      () => api.patch(`/notifications/${item.notification_id}/read`),
      'Notification marked as read.'
    )

  const markAllRead = () =>
    act(
      () => api.patch('/notifications/read-all'),
      'All notifications marked as read.'
    )

  const filtered = rows.filter(item => {
    const query = search.toLowerCase()
    const matchesSearch = Object.values(item).some(value =>
      String(value ?? '').toLowerCase().includes(query)
    )
    const status = String(
      item.application_status ||
      item.tenancy_status ||
      item.payment_status ||
      item.request_status ||
      item.read_status || ''
    ).toLowerCase()
    return matchesSearch && (filter === 'all' || status === filter)
  })

  const unread = rows.filter(item =>
    item.read_status === false || item.read_status === 'unread'
  ).length

  const stats = [
    { label: 'Total records', value: rows.length },
    { label: 'Showing', value: filtered.length },
    ...(section === 'notifications'
      ? [{ label: 'Unread', value: unread }]
      : []),
    ...(section === 'applications'
      ? [{ label: 'Pending', value: rows.filter(x => x.application_status === 'pending').length }]
      : []),
    ...(section === 'tenancies'
      ? [{ label: 'Active', value: rows.filter(x => x.tenancy_status === 'active').length }]
      : []),
    ...(section === 'payments'
      ? [{ label: 'Outstanding', value: money(rows.reduce((sum, x) => sum + Number(x.balance || 0), 0)) }]
      : []),
    ...(section === 'maintenance'
      ? [{ label: 'Pending', value: rows.filter(x => x.request_status === 'pending').length }]
      : []),
  ]

  const renderValue = (item, key) => {
    const value = item[key]
    if (value == null || value === '') return '—'
    if (key.includes('date')) return date(value)
    if (['monthly_rent', 'amount_due', 'amount_paid', 'balance'].includes(key)) return money(value)
    if (key.endsWith('_status') || key === 'priority') return <Status value={value} />
    if (key === 'read_status') return <Status value={value === true ? 'Read' : value === false ? 'Unread' : value} />
    return String(value)
  }

  return (
    <main style={{ padding: '28px', maxWidth: 1500, margin: '0 auto' }}>
      <div style={{
        display: 'flex', justifyContent: 'space-between',
        alignItems: 'center', flexWrap: 'wrap', gap: 16, marginBottom: 25
      }}>
        <div>
          <p className="eyebrow">RENTWISE MANAGEMENT</p>
          <h1 style={{ margin: '5px 0', color: '#17263f' }}>{config.title}</h1>
          <p style={{ color: '#777', margin: 0 }}>Manage and monitor your rental operations.</p>
        </div>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          {section === 'notifications' && (
            <button className="gold-button" onClick={markAllRead} disabled={!unread || busy}>
              <Check size={16} /> Mark all read
            </button>
          )}
          {['payments', 'tenancies'].includes(section) && (
            <button className="gold-button" onClick={() => setShowForm(true)}>
              <Plus size={16} /> {section === 'payments' ? 'Record payment' : 'Create tenancy'}
            </button>
          )}
          <button className="secondary-button" onClick={loadData}>
            <RefreshCw size={16} /> Refresh
          </button>
        </div>
      </div>

      <div style={{
        display: 'grid',
        gridTemplateColumns: `repeat(${stats.length}, minmax(0, 1fr))`,
        gap: 14,
        marginBottom: 24,
      }}>
        {stats.map(stat => (
          <div key={stat.label} className="content-panel">
            <p style={{ color: '#777', margin: 0, fontSize: 13 }}>{stat.label}</p>
            <h2 style={{ color: '#17263f', margin: '8px 0 0', fontSize: 23 }}>{stat.value}</h2>
          </div>
        ))}
      </div>

      {error && (
        <div role="alert" style={{
          padding: 14, background: '#fff0ed', color: '#a33',
          borderRadius: 8, marginBottom: 18
        }}>
          {error}
        </div>
      )}

      <div className="content-panel">
        <div style={{
          display: 'flex', gap: 12, flexWrap: 'wrap',
          justifyContent: 'space-between', marginBottom: 20
        }}>
          <div style={{ position: 'relative', flex: '1 1 240px', maxWidth: 420 }}>
            <Search size={17} style={{ position: 'absolute', left: 12, top: 13, color: '#888' }} />
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search records..."
              style={{ width: '100%', padding: '11px 12px 11px 38px', border: '1px solid #ddd', borderRadius: 7 }}
            />
          </div>
          <select
            value={filter}
            onChange={e => setFilter(e.target.value)}
            style={{ padding: '10px 14px', border: '1px solid #ddd', borderRadius: 7 }}
          >
            <option value="all">All statuses</option>
            {['pending', 'approved', 'rejected', 'active', 'completed', 'terminated', 'paid', 'partial', 'in_progress', 'resolved', 'unread', 'read'].map(value => (
              <option key={value} value={value}>{value.replaceAll('_', ' ')}</option>
            ))}
          </select>
        </div>

        {loading ? (
          <p>Loading records...</p>
        ) : filtered.length === 0 ? (
          <div style={{ textAlign: 'center', padding: 45, color: '#777' }}>
            <Bell size={28} />
            <h3>No records found</h3>
            <p>There are currently no records matching your search.</p>
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 750 }}>
              <thead>
                <tr>
                  {config.columns.map(([, label]) => (
                    <th key={label} style={{
                      textAlign: 'left', padding: 13, color: '#777',
                      fontSize: 12, borderBottom: '1px solid #eee',
                      textTransform: 'uppercase', whiteSpace: 'nowrap'
                    }}>{label}</th>
                  ))}
                  {section !== 'reports' && <th style={{ padding: 13, textAlign: 'left' }}>Actions</th>}
                </tr>
              </thead>
              <tbody>
                {filtered.map((item, index) => (
                  <tr key={item.application_id || item.tenancy_id || item.payment_id || item.request_id || item.notification_id || index}>
                    {config.columns.map(([key]) => (
                      <td key={key} style={{
                        padding: 13, borderBottom: '1px solid #eee',
                        color: '#344054', fontSize: 13, maxWidth: 260
                      }}>{renderValue(item, key)}</td>
                    ))}
                    <td style={{ padding: 13, borderBottom: '1px solid #eee' }}>
                      <div style={{ display: 'flex', gap: 7, flexWrap: 'wrap' }}>
                        {section === 'applications' && item.application_status === 'pending' && <>
                          <button title="Approve" onClick={() => reviewApplication(item, 'approved')} disabled={busy} style={{ border: 0, background: '#e6f4ec', color: '#23845b', padding: 8, borderRadius: 6, cursor: 'pointer' }}><Check size={17} /></button>
                          <button title="Reject" onClick={() => reviewApplication(item, 'rejected')} disabled={busy} style={{ border: 0, background: '#fff0ed', color: '#b94b4b', padding: 8, borderRadius: 6, cursor: 'pointer' }}><X size={17} /></button>
                        </>}
                        {section === 'applications' && item.application_status === 'approved' && (
                          <button className="gold-button" onClick={() => createTenancy(item)}>Create tenancy</button>
                        )}
                        {section === 'maintenance' && (
                          <button className="secondary-button" onClick={() => updateMaintenance(item)}>Update</button>
                        )}
                        {section === 'notifications' && item.read_status !== true && item.read_status !== 'read' && (
                          <button className="secondary-button" onClick={() => markRead(item)}>Mark read</button>
                        )}
                        {section === 'tenancies' && item.tenancy_status === 'active' && (
                          <button className="secondary-button" onClick={() => {
                            const status = window.prompt('Enter new status: completed or terminated')
                            if (['completed', 'terminated'].includes(status)) {
                              act(() => api.patch(`/tenancies/${item.tenancy_id}`, { tenancy_status: status }), `Tenancy ${status}.`)
                            }
                          }}>Update status</button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {showForm && (
        <div style={{
          position: 'fixed', inset: 0, background: '#10182899',
          display: 'grid', placeItems: 'center', zIndex: 1000, padding: 18
        }}>
          <form
            onSubmit={section === 'payments' ? submitPayment : submitTenancy}
            style={{
              width: 'min(100%, 500px)', maxHeight: '90vh', overflowY: 'auto',
              background: '#fff', padding: 25, borderRadius: 12,
              display: 'grid', gap: 13
            }}
          >
            <h2 style={{ color: '#17263f', margin: 0 }}>
              {section === 'payments' ? 'Record a payment' : 'Create a tenancy'}
            </h2>
            {(section === 'payments'
              ? [
                ['tenancy_id', 'Tenancy ID', 'number'],
                ['amount_due', 'Amount due (optional)', 'number'],
                ['amount_paid', 'Amount paid', 'number'],
                ['payment_method', 'Payment method', 'text'],
                ['transaction_reference', 'Transaction reference', 'text'],
                ['payment_date', 'Payment date', 'date'],
              ]
              : [
                ['application_id', 'Approved application ID', 'number'],
                ['start_date', 'Start date', 'date'],
                ['end_date', 'End date (optional)', 'date'],
                ['monthly_rent', 'Monthly rent (KES)', 'number'],
              ]
            ).map(([name, label, type]) => (
              <label key={name} style={{ display: 'grid', gap: 6, color: '#555', fontSize: 13 }}>
                {label}
                <input
                  required={['tenancy_id', 'amount_paid', 'application_id', 'start_date', 'monthly_rent'].includes(name)}
                  type={type}
                  name={name}
                  value={form[name]}
                  onChange={updateForm}
                  style={{ padding: 11, border: '1px solid #ddd', borderRadius: 7 }}
                />
              </label>
            ))}
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 8 }}>
              <button type="button" className="secondary-button" onClick={() => setShowForm(false)}>Cancel</button>
              <button className="gold-button" type="submit" disabled={busy}>
                {busy ? 'Saving...' : 'Save'}
              </button>
            </div>
          </form>
        </div>
      )}
    </main>
  )
}
