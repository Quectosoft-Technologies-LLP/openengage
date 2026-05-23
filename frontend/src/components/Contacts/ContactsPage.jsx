// src/components/Contacts/ContactsPage.jsx
import React, { useState, useEffect, useRef } from 'react';
import { Upload, RefreshCw, Users, CheckCircle2, AlertCircle, Loader2,
         CloudUpload, Database, ArrowUpDown, Filter, Search, ChevronDown } from 'lucide-react';
import { uploadCSV, pollImportJob, triggerCRMSync, getContacts } from '../../api/client';
import clsx from 'clsx';

// ── Stat Card ─────────────────────────────────────────────────
const StatCard = ({ label, value, sub, color, icon: Icon }) => (
  <div className="card flex items-center gap-4">
    <div className={`p-3 rounded-2xl ${color}`}><Icon className="w-5 h-5" /></div>
    <div>
      <p className="text-xs text-gray-400 uppercase tracking-wide">{label}</p>
      <p className="text-2xl font-bold text-gray-100">{value ?? '—'}</p>
      {sub && <p className="text-xs text-gray-500 mt-0.5">{sub}</p>}
    </div>
  </div>
);

// ── Import Result Badge ───────────────────────────────────────
const Badge = ({ label, value, color }) => (
  <div className={`flex flex-col items-center px-4 py-3 rounded-xl ${color}`}>
    <span className="text-xl font-bold">{value}</span>
    <span className="text-xs opacity-80 mt-0.5">{label}</span>
  </div>
);

// ── CSV Upload Modal ─────────────────────────────────────────
function CSVUploadModal({ onClose, onComplete }) {
  const [file,       setFile]       = useState(null);
  const [conflict,   setConflict]   = useState('update');
  const [status,     setStatus]     = useState('idle'); // idle|uploading|polling|done|error
  const [jobResult,  setJobResult]  = useState(null);
  const [dragOver,   setDragOver]   = useState(false);
  const fileRef = useRef();

  const handleDrop = (e) => {
    e.preventDefault(); setDragOver(false);
    const f = e.dataTransfer.files[0];
    if (f?.name.endsWith('.csv')) setFile(f);
  };

  const handleUpload = async () => {
    if (!file) return;
    setStatus('uploading');
    try {
      const fd = new FormData();
      fd.append('file', file);
      fd.append('on_conflict', conflict);
      const { data } = await uploadCSV(fd);
      const jobId = data.job_id;
      setStatus('polling');
      // Poll every 1.5s until complete
      const poll = setInterval(async () => {
        try {
          const { data: job } = await pollImportJob(jobId);
          if (job.status === 'completed') {
            clearInterval(poll);
            setJobResult(job);
            setStatus('done');
            onComplete?.();
          } else if (job.status === 'failed') {
            clearInterval(poll);
            setStatus('error');
          }
        } catch { clearInterval(poll); setStatus('error'); }
      }, 1500);
    } catch { setStatus('error'); }
  };

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div className="bg-gray-900 border border-gray-700 rounded-3xl p-6 w-full max-w-lg shadow-2xl"
           onClick={e => e.stopPropagation()}>
        <h2 className="text-xl font-bold text-gray-100 mb-5 flex items-center gap-2">
          <Upload className="w-5 h-5 text-brand-400" /> Import Contacts from CSV
        </h2>

        {/* Drop zone */}
        {status === 'idle' && (
          <>
            <div onDrop={handleDrop} onDragOver={e => { e.preventDefault(); setDragOver(true); }}
                 onDragLeave={() => setDragOver(false)}
                 onClick={() => fileRef.current?.click()}
                 className={clsx(
                   'border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition-all',
                   dragOver ? 'border-brand-400 bg-brand-400/10' : 'border-gray-700 hover:border-gray-500 hover:bg-gray-800/30'
                 )}>
              <CloudUpload className="w-10 h-10 mx-auto mb-3 text-gray-500" />
              {file
                ? <p className="text-gray-200 font-medium">{file.name} ({(file.size/1024).toFixed(1)} KB)</p>
                : <><p className="text-gray-400">Drag & drop your CSV or click to browse</p>
                   <p className="text-xs text-gray-600 mt-1">Supports comma, semicolon, tab delimiters · Max 50 MB</p></>
              }
              <input ref={fileRef} type="file" accept=".csv" className="hidden"
                     onChange={e => setFile(e.target.files[0])} />
            </div>

            {/* Column aliases hint */}
            <div className="mt-3 p-3 bg-gray-800/50 rounded-xl text-xs text-gray-400">
              <strong className="text-gray-300">Auto-detected headers:</strong>{` `}
              email, e-mail, emailaddress · first_name, firstname, given name ·
              company, organisation · lead_score, score, points · lifecycle_stage, status, stage
            </div>

            {/* Conflict strategy */}
            <div className="mt-4">
              <label className="text-sm text-gray-400 mb-2 block">On duplicate email:</label>
              <div className="grid grid-cols-3 gap-2">
                {[
                  { v: 'update', label: 'Update', desc: 'Merge fields, keep highest score' },
                  { v: 'skip',   label: 'Skip',   desc: 'Preserve existing records' },
                  { v: 'error',  label: 'Error',  desc: 'Fail on any conflict' },
                ].map(opt => (
                  <button key={opt.v} onClick={() => setConflict(opt.v)}
                    className={clsx('p-3 rounded-xl border text-left transition-all',
                      conflict === opt.v
                        ? 'border-brand-500 bg-brand-500/10 text-brand-300'
                        : 'border-gray-700 text-gray-400 hover:border-gray-500')}>
                    <p className="font-medium text-sm">{opt.label}</p>
                    <p className="text-xs opacity-70 mt-0.5">{opt.desc}</p>
                  </button>
                ))}
              </div>
            </div>

            <button onClick={handleUpload} disabled={!file}
              className="mt-5 w-full py-3 rounded-xl bg-brand-600 hover:bg-brand-700 disabled:opacity-40
                         disabled:cursor-not-allowed text-white font-semibold transition-colors">
              Import CSV
            </button>
          </>
        )}

        {/* Uploading / polling */}
        {(status === 'uploading' || status === 'polling') && (
          <div className="py-12 text-center space-y-3">
            <Loader2 className="w-10 h-10 mx-auto text-brand-400 animate-spin" />
            <p className="text-gray-300 font-medium">
              {status === 'uploading' ? 'Uploading file...' : 'Processing and deduplicating...'}
            </p>
            <p className="text-xs text-gray-500">This may take a few seconds for large files</p>
          </div>
        )}

        {/* Result */}
        {status === 'done' && jobResult && (
          <div className="space-y-4">
            <div className="flex items-center gap-2 text-emerald-400">
              <CheckCircle2 className="w-5 h-5" />
              <span className="font-semibold">Import Complete</span>
            </div>
            <div className="grid grid-cols-3 gap-3">
              <Badge label="Inserted"    value={jobResult.inserted}          color="bg-emerald-400/10 text-emerald-300" />
              <Badge label="Updated"     value={jobResult.updated}           color="bg-sky-400/10 text-sky-300" />
              <Badge label="Skipped"     value={jobResult.invalid_rows}      color="bg-gray-700 text-gray-300" />
              <Badge label="CSV Dupes"   value={jobResult.duplicates_in_csv} color="bg-yellow-400/10 text-yellow-300" />
              <Badge label="DB Dupes"    value={jobResult.duplicates_in_db}  color="bg-orange-400/10 text-orange-300" />
              <Badge label="Total Rows"  value={jobResult.total_rows}        color="bg-violet-400/10 text-violet-300" />
            </div>
            {jobResult.sample_errors?.length > 0 && (
              <div className="p-3 bg-red-900/20 border border-red-800/50 rounded-xl">
                <p className="text-xs text-red-400 font-medium mb-1">Sample errors:</p>
                {jobResult.sample_errors.slice(0,3).map((e,i) => (
                  <p key={i} className="text-xs text-red-300">{e.error}</p>
                ))}
              </div>
            )}
            <button onClick={onClose}
              className="w-full py-3 rounded-xl bg-brand-600 hover:bg-brand-700 text-white font-semibold">
              Done
            </button>
          </div>
        )}

        {status === 'error' && (
          <div className="py-8 text-center space-y-3">
            <AlertCircle className="w-10 h-10 mx-auto text-red-400" />
            <p className="text-red-400 font-medium">Import failed</p>
            <button onClick={() => setStatus('idle')} className="text-brand-400 underline text-sm">Try again</button>
          </div>
        )}
      </div>
    </div>
  );
}

// ── CRM Sync Status Card ──────────────────────────────────────
function CRMSyncCard({ crm, logo, lastSync, recordsSynced, onSync, syncing }) {
  return (
    <div className="card flex items-center gap-4">
      <div className="w-10 h-10 rounded-xl bg-gray-800 flex items-center justify-center flex-shrink-0">
        <Database className="w-5 h-5 text-gray-400" />
      </div>
      <div className="flex-1">
        <p className="font-semibold text-gray-200">{crm}</p>
        <p className="text-xs text-gray-500">
          {lastSync ? `Last sync: ${lastSync}` : 'Never synced'}
          {recordsSynced != null && ` · ${recordsSynced.toLocaleString()} records`}
        </p>
      </div>
      <button onClick={onSync} disabled={syncing}
        className="flex items-center gap-2 px-4 py-2 rounded-xl bg-gray-800 hover:bg-gray-700
                   text-gray-300 text-sm font-medium transition-colors disabled:opacity-50">
        <RefreshCw className={clsx('w-3.5 h-3.5', syncing && 'animate-spin')} />
        {syncing ? 'Syncing...' : 'Sync Now'}
      </button>
    </div>
  );
}

// ── Main ContactsPage ─────────────────────────────────────────
export default function ContactsPage() {
  const [showUpload, setShowUpload] = useState(false);
  const [contacts,   setContacts]   = useState([]);
  const [total,      setTotal]      = useState(0);
  const [page,       setPage]       = useState(1);
  const [search,     setSearch]     = useState('');
  const [stage,      setStage]      = useState('');
  const [loading,    setLoading]    = useState(true);
  const [sfSyncing,  setSfSyncing]  = useState(false);
  const [hsSyncing,  setHsSyncing]  = useState(false);
  const [sfLast,     setSfLast]     = useState(null);
  const [hsLast,     setHsLast]     = useState(null);
  const PAGE_SIZE = 25;

  const fetchContacts = async () => {
    setLoading(true);
    try {
      const { data } = await getContacts({ page, per_page: PAGE_SIZE, search, lifecycle_stage: stage });
      setContacts(data.contacts || []);
      setTotal(data.total || 0);
    } catch {
      setContacts([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchContacts(); }, [page, search, stage]);

  const handleSFSync = async () => {
    setSfSyncing(true);
    try { await triggerCRMSync('salesforce'); setSfLast(new Date().toLocaleString()); }
    catch {}
    setSfSyncing(false);
  };

  const handleHSSync = async () => {
    setHsSyncing(true);
    try { await triggerCRMSync('hubspot'); setHsLast(new Date().toLocaleString()); }
    catch {}
    setHsSyncing(false);
  };

  const lifecycleColor = (stage) => ({
    lead:     'bg-gray-700 text-gray-300',
    mql:      'bg-sky-400/10 text-sky-300',
    sql:      'bg-violet-400/10 text-violet-300',
    customer: 'bg-emerald-400/10 text-emerald-300',
    churned:  'bg-red-400/10 text-red-300',
  }[stage] || 'bg-gray-700 text-gray-300');

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-100">Contacts</h1>
          <p className="text-sm text-gray-400 mt-0.5">{total.toLocaleString()} total contacts</p>
        </div>
        <button onClick={() => setShowUpload(true)}
          className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-brand-600 hover:bg-brand-700
                     text-white font-semibold transition-colors shadow-lg shadow-brand-600/20">
          <Upload className="w-4 h-4" /> Import CSV
        </button>
      </div>

      {/* KPI row */}
      <div className="grid grid-cols-4 gap-4">
        <StatCard label="Total Contacts" value={total.toLocaleString()} icon={Users}      color="bg-brand-400/10 text-brand-400" />
        <StatCard label="MQLs"           value="—"                       icon={ArrowUpDown} color="bg-sky-400/10 text-sky-400"   />
        <StatCard label="SQLs"           value="—"                       icon={CheckCircle2} color="bg-violet-400/10 text-violet-400" />
        <StatCard label="Customers"      value="—"                       icon={Database}   color="bg-emerald-400/10 text-emerald-400" />
      </div>

      {/* CRM sync status */}
      <div className="grid grid-cols-2 gap-4">
        <CRMSyncCard crm="Salesforce" lastSync={sfLast} onSync={handleSFSync} syncing={sfSyncing} />
        <CRMSyncCard crm="HubSpot"    lastSync={hsLast} onSync={handleHSSync} syncing={hsSyncing} />
      </div>

      {/* Filters + search */}
      <div className="flex items-center gap-3">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-2.5 w-4 h-4 text-gray-500" />
          <input
            className="w-full pl-9 pr-4 py-2 bg-gray-900 border border-gray-700 rounded-xl
                       text-gray-200 text-sm placeholder-gray-500 focus:outline-none focus:border-brand-500"
            placeholder="Search by email, name, company..."
            value={search}
            onChange={e => { setSearch(e.target.value); setPage(1); }}
          />
        </div>
        <div className="relative">
          <Filter className="absolute left-3 top-2.5 w-4 h-4 text-gray-500" />
          <select value={stage} onChange={e => { setStage(e.target.value); setPage(1); }}
            className="pl-9 pr-8 py-2 bg-gray-900 border border-gray-700 rounded-xl text-gray-200
                       text-sm focus:outline-none focus:border-brand-500 appearance-none">
            <option value="">All Stages</option>
            <option value="lead">Lead</option>
            <option value="mql">MQL</option>
            <option value="sql">SQL</option>
            <option value="customer">Customer</option>
            <option value="churned">Churned</option>
          </select>
        </div>
      </div>

      {/* Contacts table */}
      <div className="card overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-800 text-gray-400">
              {['Name', 'Email', 'Company', 'Industry', 'Stage', 'Score'].map(h => (
                <th key={h} className="text-left py-3 px-4 font-medium">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              [...Array(8)].map((_, i) => (
                <tr key={i}><td colSpan={6} className="py-3 px-4">
                  <div className="h-4 bg-gray-800 rounded animate-pulse w-full" />
                </td></tr>
              ))
            ) : contacts.length === 0 ? (
              <tr><td colSpan={6} className="py-16 text-center text-gray-500">
                <Users className="w-10 h-10 mx-auto mb-2 opacity-20" />
                <p>No contacts found. Import a CSV to get started.</p>
              </td></tr>
            ) : contacts.map(c => (
              <tr key={c.id} className="border-b border-gray-800/50 hover:bg-gray-800/30 transition-colors">
                <td className="py-3 px-4 font-medium text-gray-200">
                  {[c.first_name, c.last_name].filter(Boolean).join(' ') || '—'}
                </td>
                <td className="py-3 px-4 text-gray-400">{c.email}</td>
                <td className="py-3 px-4 text-gray-400">{c.company || '—'}</td>
                <td className="py-3 px-4 text-gray-400">{c.industry || '—'}</td>
                <td className="py-3 px-4">
                  <span className={`badge ${lifecycleColor(c.lifecycle_stage)}`}>
                    {c.lifecycle_stage || 'lead'}
                  </span>
                </td>
                <td className="py-3 px-4">
                  <div className="flex items-center gap-2">
                    <div className="w-16 h-1.5 bg-gray-800 rounded-full overflow-hidden">
                      <div className="h-full bg-brand-500 rounded-full"
                           style={{ width: `${Math.min(c.lead_score || 0, 100)}%` }} />
                    </div>
                    <span className="text-gray-400 text-xs">{c.lead_score || 0}</span>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {/* Pagination */}
        {total > PAGE_SIZE && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-gray-800">
            <p className="text-xs text-gray-500">
              Page {page} of {Math.ceil(total / PAGE_SIZE)} · {total.toLocaleString()} contacts
            </p>
            <div className="flex gap-2">
              <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}
                className="px-3 py-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-300 text-xs disabled:opacity-40">
                ← Prev
              </button>
              <button onClick={() => setPage(p => p + 1)} disabled={page >= Math.ceil(total / PAGE_SIZE)}
                className="px-3 py-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-300 text-xs disabled:opacity-40">
                Next →
              </button>
            </div>
          </div>
        )}
      </div>

      {/* CSV Upload Modal */}
      {showUpload && (
        <CSVUploadModal
          onClose={() => setShowUpload(false)}
          onComplete={() => { setShowUpload(false); fetchContacts(); }}
        />
      )}
    </div>
  );
}
