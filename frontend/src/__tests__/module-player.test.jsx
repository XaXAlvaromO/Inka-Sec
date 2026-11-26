// ModulePlayer: retomar un módulo donde quedó y volver un paso sin perder lo ya escrito.
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

vi.mock('../api', async () => (await import('../test/mockApi')).createApiMock());

import { api } from '../api';
import { ModulePlayer } from '../App';

const MODULE = {
  title: 'Contraseñas seguras', topic: 'Credenciales', behavior_objective: 'Usar una clave distinta en cada cuenta.',
  diagnostic: [{ code: 'C1', dimension: 'capacidad', statement: 'Sé crear una clave larga y distinta.' }],
  micro_lesson: 'Usa frases largas y un gestor de contraseñas aprobado.',
  capacity_questions: [{ prompt: '¿Qué haces si una tienda online sufre una filtración?', options: ['Nada', 'Cambio esa clave donde la reuse'], correct: 1, feedback: 'Cambia la clave en todos lados donde la reuses.' }],
  opportunity_question: '¿Qué te dificulta usar un gestor de contraseñas?',
  motivation_question: '¿Qué pasaría si filtran tu clave del correo?',
  real_action: 'Cambia hoy la clave de tu correo por una única.',
  reinforcement_days: [7, 30, 90],
  saved_reflections: {},
  saved_diagnostic: {},
  resume_step: 0,
};

function play(overrides = {}) {
  api.worker.module.mockResolvedValueOnce({ ...MODULE, ...overrides });
  const onBack = vi.fn(); const onChanged = vi.fn();
  render(<ModulePlayer moduleId={1} onBack={onBack} onChanged={onChanged}/>);
  return { onBack, onChanged };
}

describe('retomar un módulo ya empezado', () => {
  it('abre en el paso que el backend indica y con lo ya guardado', async () => {
    play({
      saved_diagnostic: { C1: 4 },
      saved_reflections: { oportunidad: 'No sé cuál usar' },
      resume_step: 3,
    });
    expect(await screen.findByText('Identifica tus barreras')).toBeInTheDocument();   // paso 3: oportunidad
    expect(screen.getByDisplayValue('No sé cuál usar')).toBeInTheDocument();           // su respuesta anterior sigue ahí
  });

  it('empieza desde el diagnóstico la primera vez', async () => {
    play();
    expect(await screen.findByText('¿Qué tan seguro te sientes hoy?')).toBeInTheDocument();
  });
});

describe('botón de paso anterior', () => {
  it('no aparece en el primer paso', async () => {
    play();
    await screen.findByText('¿Qué tan seguro te sientes hoy?');
    expect(screen.queryByRole('button', { name: '← Paso anterior' })).not.toBeInTheDocument();
  });

  it('vuelve un paso sin perder lo que ya se había guardado', async () => {
    play({ saved_diagnostic: { C1: 4 }, resume_step: 1 });
    expect(await screen.findByText('Aprende lo esencial')).toBeInTheDocument();   // paso 1: microlección

    await userEvent.click(screen.getByRole('button', { name: '← Paso anterior' }));
    expect(screen.getByText('¿Qué tan seguro te sientes hoy?')).toBeInTheDocument();   // de vuelta al diagnóstico
    expect(screen.getByRole('radio', { name: /De acuerdo/ })).toBeChecked();           // su respuesta se mantuvo
  });

  it('no aparece una vez completado el módulo', async () => {
    play({ resume_step: 6 });
    expect(await screen.findByText('Módulo completado')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '← Paso anterior' })).not.toBeInTheDocument();
  });
});
