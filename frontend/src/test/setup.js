// Preparación común de las pruebas del frontend (Vitest + Testing Library + jsdom).
import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterEach, vi } from 'vitest';

// El fondo animado usa canvas, que jsdom no dibuja: en las pruebas no aporta nada.
vi.mock('../ParticleNetwork', () => ({ default: () => null }));

afterEach(() => {
  cleanup();
  window.history.replaceState(null, '', '/');
});

// jsdom no trae estas APIs del navegador.
if (!URL.createObjectURL) URL.createObjectURL = () => 'blob:prueba';
if (!URL.revokeObjectURL) URL.revokeObjectURL = () => {};
