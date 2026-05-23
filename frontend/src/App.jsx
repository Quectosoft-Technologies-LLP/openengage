// src/App.jsx
import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './components/Dashboard/Dashboard';
import CampaignBuilder from './components/CampaignBuilder/CampaignBuilder';
import EmailEditor from './components/EmailEditor/EmailEditor';
import ContactsPage from './components/Contacts/ContactsPage';

const Analytics  = () => <div className="p-6 text-gray-300">Analytics — <a className="text-brand-400 underline" href="http://localhost:8088" target="_blank" rel="noreferrer">Open Superset →</a></div>;
const AgentPanel = () => <div className="p-6 text-gray-300">AI Agent Logs — coming in v1.1</div>;
const SettingsPage = () => <div className="p-6 text-gray-300">Settings — coming in v1.1</div>;

export default function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/"          element={<Dashboard />} />
          <Route path="/campaigns" element={<CampaignBuilder />} />
          <Route path="/contacts"  element={<ContactsPage />} />
          <Route path="/emails"    element={<EmailEditor onSave={async d => console.log('Saved', d)} />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/agents"    element={<AgentPanel />} />
          <Route path="/settings"  element={<SettingsPage />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}
