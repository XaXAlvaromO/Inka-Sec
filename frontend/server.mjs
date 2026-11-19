import { fileURLToPath } from 'node:url';
import express from 'express';
import { createProxyMiddleware } from 'http-proxy-middleware';

const backendUrl = process.env.BACKEND_URL;
if (!backendUrl) {
  throw new Error('BACKEND_URL debe contener el origen de la API');
}

const dist = fileURLToPath(new URL('./dist/', import.meta.url));
const app = express();
app.disable('x-powered-by');

app.use(createProxyMiddleware({
  pathFilter: (pathname) => pathname === '/api' || pathname.startsWith('/api/'),
  target: backendUrl,
  changeOrigin: true,
}));

app.use(express.static(dist));
app.get(/.*/, (_request, response) => {
  response.sendFile('index.html', { root: dist });
});

const port = Number(process.env.PORT ?? 3000);
app.listen(port, '0.0.0.0', () => {
  console.log(`Frontend escuchando en el puerto ${port}`);
});
