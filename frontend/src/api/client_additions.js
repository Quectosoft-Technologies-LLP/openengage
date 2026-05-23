
// Add to src/api/client.js

// Contact import
export const uploadCSV     = (formData)    => api.post('/contacts/import', formData, {headers: {'Content-Type': 'multipart/form-data'}});
export const pollImportJob = (jobId)       => api.get(`/contacts/import/${jobId}`);
export const getContacts   = (params = {}) => api.get('/contacts', { params });
export const triggerCRMSync = (crm)        => api.post(`/integrations/sync/${crm}`);
