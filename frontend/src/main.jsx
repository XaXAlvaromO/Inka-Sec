import { lazy, StrictMode, Suspense } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App.jsx';

const preview = import.meta.env.DEV && new URLSearchParams(window.location.search).get('preview') === 'admin';
const AdminPreview = import.meta.env.DEV ? lazy(() => import('./AdminPreview.jsx')) : null;

createRoot(document.getElementById('root')).render(
  <StrictMode>
    {preview ? <Suspense fallback={null}><AdminPreview /></Suspense> : <App />}
  </StrictMode>
);
