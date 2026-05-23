// src/components/Dashboard/Dashboard.jsx
import React, { useEffect, useState } from 'react';
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Mail, Users, TrendingUp, Zap, ArrowUpRight, Bot } from 'lucide-react';
import { getCampaigns, getAISuggestions } from '../../api/client';

const StatCard = ({ label, value, change, icon: Icon, color }) => (
  <div className="card flex items-center gap-4">
    <div className={`p-3 rounded-2xl ${color}`}>
      <Icon className="w-5 h-5" />
    </div>
    <div className="flex-1">
      <p className="text-xs text-gray-400 uppercase tracking-wide">{label}</p>
      <p className="text-2xl font-bold text-gray-100 mt-0.5">{value}</p>
    </div>
    {change && (
      <div className="flex items-center gap-1 text-emerald-400 text-xs font-medium">
        <ArrowUpRight className="w-3.5 h-3.5" />
        {change}
      </div>
    )}
  </div>
);

const mockOpenRates = [
  {week:'W1',rate:22},{week:'W2',rate:28},{week:'W3',rate:25},
  {week:'W4',rate:31},{week:'W5',rate:35},{week:'W6',rate:33},
];
const mockCampaigns = [
  {name:'SaaS Nurture',sent:1200,opens:384,clicks:96},
  {name:'Demo Invite', sent:800, opens:320,clicks:144},
  {name:'Re-engage',   sent:500, opens:100,clicks:30},
  {name:'Onboarding',  sent:300, opens:198,clicks:90},
];

export default function Dashboard() {
  const [suggestions, setSuggestions] = useState([]);
  const [loading,     setLoading]     = useState(true);

  useEffect(() => {
    getAISuggestions(5)
      .then(r => setSuggestions(r.data.suggestions || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold text-gray-100">Dashboard</h1>

      {/* KPI Cards */}
      <div className="grid grid-cols-4 gap-4">
        <StatCard label="Active Campaigns" value="12"    change="+3 this week"  icon={Zap}        color="text-brand-400  bg-brand-400/10"  />
        <StatCard label="Total Contacts"   value="8,412" change="+124 today"    icon={Users}      color="text-emerald-400 bg-emerald-400/10" />
        <StatCard label="Avg Open Rate"    value="31.4%" change="+2.1%"         icon={Mail}       color="text-sky-400   bg-sky-400/10"     />
        <StatCard label="MQLs This Month"  value="234"   change="+18%"          icon={TrendingUp} color="text-violet-400 bg-violet-400/10"  />
      </div>

      <div className="grid grid-cols-5 gap-6">
        {/* Open rate trend */}
        <div className="col-span-3 card">
          <h3 className="font-semibold text-gray-200 mb-4">Email Open Rate Trend (6 Weeks)</h3>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={mockOpenRates}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
              <XAxis dataKey="week" tick={{fill:'#6b7280',fontSize:12}} />
              <YAxis tick={{fill:'#6b7280',fontSize:12}} unit="%" />
              <Tooltip contentStyle={{background:'#111827',border:'1px solid #374151',borderRadius:'12px'}} />
              <Line type="monotone" dataKey="rate" stroke="#6366f1" strokeWidth={2.5} dot={{fill:'#6366f1',r:4}} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* AI Suggestions panel */}
        <div className="col-span-2 card">
          <h3 className="font-semibold text-gray-200 mb-3 flex items-center gap-2">
            <Bot className="w-4 h-4 text-brand-400" /> AI Suggestions
          </h3>
          {loading ? (
            <div className="space-y-2">
              {[...Array(3)].map((_,i) => (
                <div key={i} className="h-12 bg-gray-800 rounded-xl animate-pulse" />
              ))}
            </div>
          ) : suggestions.length === 0 ? (
            <div className="text-center py-8 text-gray-500 text-sm">
              <Bot className="w-8 h-8 mx-auto mb-2 opacity-30" />
              Weekly AI suggestions appear here.<br/>
              First run every Monday at 8am.
            </div>
          ) : (
            <div className="space-y-2 max-h-52 overflow-y-auto">
              {suggestions.map(s => (
                <div key={s.id} className="p-3 bg-gray-800 rounded-xl text-xs text-gray-300 leading-relaxed border border-gray-700/50">
                  {s.content.slice(0, 200)}{s.content.length > 200 ? '...' : ''}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Campaign table */}
      <div className="card">
        <h3 className="font-semibold text-gray-200 mb-4">Campaign Performance</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-gray-400 border-b border-gray-800">
                {['Campaign','Sent','Opens','Clicks','Open Rate','Click Rate'].map(h => (
                  <th key={h} className="text-left py-2 px-3 font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {mockCampaigns.map(c => (
                <tr key={c.name} className="border-b border-gray-800/50 hover:bg-gray-800/30 transition-colors">
                  <td className="py-3 px-3 font-medium text-gray-200">{c.name}</td>
                  <td className="py-3 px-3 text-gray-400">{c.sent.toLocaleString()}</td>
                  <td className="py-3 px-3 text-gray-400">{c.opens.toLocaleString()}</td>
                  <td className="py-3 px-3 text-gray-400">{c.clicks.toLocaleString()}</td>
                  <td className="py-3 px-3">
                    <span className="badge bg-emerald-400/10 text-emerald-300">
                      {((c.opens/c.sent)*100).toFixed(1)}%
                    </span>
                  </td>
                  <td className="py-3 px-3">
                    <span className="badge bg-sky-400/10 text-sky-300">
                      {((c.clicks/c.sent)*100).toFixed(1)}%
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
