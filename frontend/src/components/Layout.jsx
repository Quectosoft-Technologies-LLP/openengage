// src/components/Layout.jsx
import React, { useState } from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Megaphone, Users, Mail, BarChart2, Bot, Settings, ChevronLeft, ChevronRight } from 'lucide-react';
import CopilotChat from './CopilotChat/CopilotChat';
import clsx from 'clsx';

const NAV = [
  { to: '/',          icon: LayoutDashboard, label: 'Dashboard'   },
  { to: '/campaigns', icon: Megaphone,       label: 'Campaigns'   },
  { to: '/contacts',  icon: Users,           label: 'Contacts'    },
  { to: '/emails',    icon: Mail,            label: 'Email Editor' },
  { to: '/analytics', icon: BarChart2,       label: 'Analytics'   },
  { to: '/agents',    icon: Bot,             label: 'AI Agents'   },
  { to: '/settings',  icon: Settings,        label: 'Settings'    },
];

export default function Layout({ children }) {
  const [collapsed, setCollapsed]  = useState(false);
  const [copilot,   setCopilot]    = useState(false);

  return (
    <div className="flex h-screen overflow-hidden bg-gray-950">
      {/* Sidebar */}
      <aside className={clsx(
        'flex flex-col bg-gray-900 border-r border-gray-800 transition-all duration-300 flex-shrink-0',
        collapsed ? 'w-16' : 'w-56'
      )}>
        {/* Logo */}
        <div className="flex items-center gap-3 px-4 py-5 border-b border-gray-800">
          <div className="w-8 h-8 rounded-xl bg-brand-600 flex items-center justify-center flex-shrink-0">
            <span className="text-white font-bold text-xs">OE</span>
          </div>
          {!collapsed && <span className="font-bold text-gray-100 text-sm">OpenEngage</span>}
        </div>

        {/* Nav */}
        <nav className="flex-1 py-4 px-2 space-y-1">
          {NAV.map(({ to, icon: Icon, label }) => (
            <NavLink key={to} to={to} end={to === '/'}
              className={({ isActive }) => clsx('sidebar-item', isActive && 'sidebar-active')}>
              <Icon className="w-4 h-4 flex-shrink-0" />
              {!collapsed && <span className="text-sm">{label}</span>}
            </NavLink>
          ))}
        </nav>

        {/* Collapse toggle */}
        <button onClick={() => setCollapsed(c => !c)}
          className="flex items-center justify-center p-3 border-t border-gray-800 text-gray-500 hover:text-gray-300 transition-colors">
          {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
        </button>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto">{children}</main>

      {/* Floating Copilot button */}
      {!copilot && (
        <button onClick={() => setCopilot(true)}
          className="fixed bottom-6 right-6 z-40 w-14 h-14 rounded-2xl bg-brand-600 hover:bg-brand-700 shadow-lg shadow-brand-600/30 flex items-center justify-center transition-all hover:scale-110">
          <Bot className="w-6 h-6 text-white" />
        </button>
      )}

      {copilot && (
        <CopilotChat sessionId="main" onClose={() => setCopilot(false)} />
      )}
    </div>
  );
}
