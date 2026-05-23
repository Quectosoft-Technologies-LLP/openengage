// src/api/client.js — Axios wrapper for OpenEngage AI Gateway
import axios from 'axios';

const BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export const api = axios.create({
  baseURL: BASE,
  headers: { 'Content-Type': 'application/json' },
});

// Campaigns
export const getCampaigns   = ()             => api.get('/api/campaigns');
export const createCampaign = (data)         => api.post('/api/campaigns', data);
export const launchCampaign = (id)           => api.post(`/api/campaigns/${id}/launch`);

// Contacts
export const getContacts    = (params)       => api.get('/api/contacts', { params });
export const getContact     = (id)           => api.get(`/api/contacts/${id}`);

// AI Agents
export const chatWithAgent  = (session, msg, ctx) =>
  api.post('/api/agents/chat', { session_id: session, message: msg, context: ctx || {} });
export const suggestCampaign = (data)        => api.post('/api/agents/suggest-campaign', data);
export const generateEmail  = (session, msg, ctx) =>
  api.post('/api/agents/generate-email', { session_id: session, message: msg, context: ctx });
export const getAISuggestions = (limit=10)   => api.get(`/api/agents/suggestions?limit=${limit}`);

// Scoring
export const getLeadScore   = (contactId)    => api.get(`/api/scoring/${contactId}`);

// Analytics
export const getAnalytics   = (campaignId)   => api.get(`/api/analytics/${campaignId}`);
