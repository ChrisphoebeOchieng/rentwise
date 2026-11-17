import { useCallback, useEffect, useState } from 'react'
import { RefreshCw, Building2, Wallet, Wrench, TrendingUp } from 'lucide-react'
import api from '../../services/api'

const money = value =>
  `KES ${Number(value || 0).toLocaleString('en-KE')}`

function ReportCard({ label, value, icon: Icon, description }) {
  return (
    <div className="content-panel">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <p style={{ color: '#777', fontSize: 13, margin: 0 }}>{label}</p>
          <h2 style={{ color: '#17263f', fontSize: 25, margin: '10px 0' }}>{value}</h2>
          <p style={{ color: '#888', fontSize: 12, margin: 0 }}>{description}</p>
        </div>
        <Icon size={25} color="#c5a46d" />
      </div>
    </div>
  )
}

function Breakdown({ title, data }) {
  const entries = Object.entries(data || {})

  return (
    <div className="content-panel">
      <h3 style={{ color: '#17263f', marginTop: 0 }}>{title}</h3>
      {entries.length === 0 ? (
        <p style={{ color: '#888' }}>No report data available.</p>
      ) : entries.map(([label, value]) => (
        <div key={label} style={{
          display: 'flex',
          justifyContent: 'space-between',
          padding: '12px 0',
          borderBottom: '1px solid #eee',
          gap: 12
        }}>
          <span style={{ color: '#666', textTransform: 'capitalize' }}>
            {label.replaceAll('_', ' ')}
          </span>
          <strong style={{ color: '#17263f' }}>{value}</strong>
        </div>
      ))}
    </div>
  )
}

export default function AdminReports() {
  const [dashboard, setDashboard] = useState({})
  const [financial, setFinancial] = useState({})
  const [operations, setOperations] = useState({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const loadReports = useCallback(async () => {
    setLoading(true)
    setError('')

    try {
      const results = await Promise.all([
        api.get('/reports/dashboard'),
        api.get('/reports/financial'),
        api.get('/reports/operations'),
      ])

      setDashboard(results[0].data.dashboard || {})
      setFinancial(results[1].data.financial_report || {})
      setOperations(results[2].data.operations_report || {})
    } catch (err) {
      setError(err.response?.data?.message || 'Unable to load reports. Please try again.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadReports()
  }, [loadReports])

  if (loading) {
    return <main style={{ padding: 30 }}>Loading reports...</main>
  }

  return (
    <main style={{ padding: 28, maxWidth: 1500, margin: '0 auto' }}>
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: 15,
        marginBottom: 25
      }}>
        <div>
          <p className="eyebrow">RENTWISE ANALYTICS</p>
          <h1 style={{ color: '#17263f', margin: '5px 0' }}>Reports & Analytics</h1>
          <p style={{ color: '#777', margin: 0 }}>
            Overview of property, financial and operational performance.
          </p>
        </div>
        <button className="secondary-button" onClick={loadReports}>
          <RefreshCw size={16} /> Refresh reports
        </button>
      </div>

      {error && (
        <div style={{
          background: '#fff0ed',
          color: '#a33',
          padding: 14,
          borderRadius: 8,
          marginBottom: 20
        }}>
          {error}
        </div>
      )}

      <h2 style={{ color: '#17263f', fontSize: 18 }}>Property performance</h2>
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))',
        gap: 16,
        marginBottom: 28
      }}>
        <ReportCard label="Total properties" value={dashboard.total_properties ?? 0} icon={Building2} description="Registered properties" />
        <ReportCard label="Occupied properties" value={dashboard.occupied_properties ?? 0} icon={Building2} description="Currently occupied" />
        <ReportCard label="Available properties" value={dashboard.available_properties ?? 0} icon={Building2} description="Available for rent" />
        <ReportCard label="Occupancy rate" value={`${Number(dashboard.occupancy_rate || 0).toFixed(1)}%`} icon={TrendingUp} description="Property occupancy" />
        <ReportCard label="Active tenancies" value={dashboard.active_tenancies ?? 0} icon={Building2} description="Current agreements" />
        <ReportCard label="Applications" value={dashboard.total_applications ?? 0} icon={Building2} description="Rental applications" />
      </div>

      <h2 style={{ color: '#17263f', fontSize: 18 }}>Financial performance</h2>
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
        gap: 16,
        marginBottom: 20
      }}>
        <ReportCard label="Total amount due" value={money(financial.total_amount_due)} icon={Wallet} description="Recorded payment obligations" />
        <ReportCard label="Amount collected" value={money(financial.total_amount_collected)} icon={Wallet} description="Payments received" />
        <ReportCard label="Outstanding balance" value={money(financial.outstanding_balance)} icon={TrendingUp} description="Remaining payment balance" />
      </div>

      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
        gap: 18,
        marginBottom: 28
      }}>
        <Breakdown title="Application statistics" data={dashboard.application_statistics} />
        <Breakdown title="Payment statistics" data={financial.payment_statistics} />
      </div>

      <h2 style={{ color: '#17263f', fontSize: 18 }}>Operational performance</h2>
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
        gap: 16,
        marginBottom: 20
      }}>
        <ReportCard label="Maintenance requests" value={operations.total_maintenance_requests ?? 0} icon={Wrench} description="Total submitted requests" />
      </div>

      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
        gap: 18
      }}>
        <Breakdown title="Maintenance by status" data={operations.maintenance_by_status} />
        <Breakdown title="Maintenance by priority" data={operations.maintenance_by_priority} />
      </div>
    </main>
  )
}
