// Certificados: página del trabajador, descarga, renovación, tarjeta del inicio y verificación pública.
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../api', async () => (await import('../test/mockApi')).createApiMock());

import { api, ApiError } from '../api';
import { CertificateHomeCard, CertificatesPage, VerifyCertificatePage, verifyUrl } from '../certificates';

const CERT = {
  id: 5, topic: 'Phishing', code: 'INKA-7KQ2-M9XP-4HTR', status: 'active', status_label: 'Vigente', issued_at: '2026-11-22T10:00:00Z',
  expires_at: '2027-11-22T10:00:00Z', days_left: 365, modules: ['Phishing y enlaces'], renewed: false, can_renew: false,
};
const EXPIRING = { ...CERT, id: 6, topic: 'Contraseñas', code: 'INKA-AAAA-BBBB-CCCC', status: 'expiring', status_label: 'Por vencer', days_left: 12, can_renew: true };

function overview(extra = {}) {
  return {
    pass_percent: 80, validity_days: 365, warning_days: 30, new: [], history: [],
    topics: [
      { topic: 'Phishing', passed: 1, total: 1, certificate: CERT, modules: [] },
      { topic: 'Contraseñas', passed: 1, total: 1, certificate: EXPIRING, modules: [] },
      { topic: 'Wi-Fi', passed: 1, total: 3, certificate: null, modules: [
        { id: 11, title: 'Redes abiertas', completed: true, passed: true, needs_review: false },
        { id: 12, title: 'VPN', completed: true, passed: false, needs_review: true },
        { id: 13, title: 'Datos móviles', completed: false, passed: false, needs_review: false },
      ] },
    ],
    ...extra,
  };
}

beforeEach(() => { api.worker.certificates.mockResolvedValue(overview()); });

describe('Mis certificados', () => {
  it('separa obtenidos y en progreso, y dice qué falta en cada módulo', async () => {
    const onOpenModule = vi.fn();
    render(<CertificatesPage onOpenModule={onOpenModule}/>);
    expect(await screen.findByRole('heading', { name: 'Obtenidos' })).toBeInTheDocument();
    expect(screen.getByText('INKA-7KQ2-M9XP-4HTR')).toBeInTheDocument();
    expect(screen.getByText('Vigente')).toBeInTheDocument();
    expect(screen.getByText(/faltan 12 días/)).toBeInTheDocument();
    expect(screen.getByText('En progreso · 1 de 3')).toBeInTheDocument();
    expect(screen.getByText('Aprobado')).toBeInTheDocument();
    expect(screen.getByText(/repite la práctica hasta llegar a 80 %/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Repasar' }));
    await userEvent.click(screen.getByRole('button', { name: 'Abrir' }));
    expect(onOpenModule.mock.calls).toEqual([[12], [13]]);
    // Solo el que está por vencer se puede renovar.
    expect(screen.getAllByRole('button', { name: 'Renovar con un repaso' })).toHaveLength(1);
  });

  it('avisa del certificado nuevo, muestra el historial y el estado vacío', async () => {
    api.worker.certificates.mockResolvedValueOnce(overview({ new: ['Phishing'], history: [{ ...CERT, id: 1, code: 'INKA-OLD0-OLD0-OLD0', status: 'superseded' }] }));
    const { unmount } = render(<CertificatesPage onOpenModule={vi.fn()}/>);
    expect(await screen.findByText('Obtuviste el certificado de Phishing.')).toBeInTheDocument();
    expect(screen.getByText(/INKA-OLD0-OLD0-OLD0/)).toBeInTheDocument();
    unmount();
    api.worker.certificates.mockResolvedValueOnce(overview({ topics: [] }));
    render(<CertificatesPage onOpenModule={vi.fn()}/>);
    expect(await screen.findByText('Aún no tienes módulos asignados')).toBeInTheDocument();
  });

  it('muestra el error si no carga', async () => {
    api.worker.certificates.mockRejectedValueOnce(new ApiError('Sin conexión', 0));
    render(<CertificatesPage onOpenModule={vi.fn()}/>);
    expect(await screen.findByText('Sin conexión')).toBeInTheDocument();
  });

  it('descarga el PDF y copia el enlace de verificación', async () => {
    api.worker.certificatePdf.mockResolvedValueOnce(new Blob(['%PDF'], { type: 'application/pdf' }));
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});
    const user = userEvent.setup();
    const writeText = vi.spyOn(navigator.clipboard, 'writeText').mockResolvedValue();
    render(<CertificatesPage onOpenModule={vi.fn()}/>);
    const card = (await screen.findByText('INKA-7KQ2-M9XP-4HTR')).closest('article');
    await user.click(within(card).getByRole('button', { name: 'Descargar PDF' }));
    expect(api.worker.certificatePdf).toHaveBeenCalledWith(5);
    expect(click).toHaveBeenCalled();
    await user.click(within(card).getByRole('button', { name: 'Copiar enlace de verificación' }));
    expect(writeText).toHaveBeenCalledWith(verifyUrl('INKA-7KQ2-M9XP-4HTR'));
    expect(within(card).getByRole('status')).toHaveTextContent('Enlace de verificación copiado.');
  });

  it('muestra el error si falla la descarga', async () => {
    api.worker.certificatePdf.mockRejectedValueOnce(new ApiError('No se pudo descargar el certificado.', 500));
    render(<CertificatesPage onOpenModule={vi.fn()}/>);
    const card = (await screen.findByText('INKA-7KQ2-M9XP-4HTR')).closest('article');
    await userEvent.click(within(card).getByRole('button', { name: 'Descargar PDF' }));
    expect(await within(card).findByRole('status')).toHaveTextContent('No se pudo descargar el certificado.');
  });
});

describe('renovación', () => {
  const quiz = { pass_percent: 80, certificate: EXPIRING, questions: [
    { key: '1:0', prompt: '¿Reutilizas claves?', options: ['Sí', 'No'] },
    { key: '1:1', prompt: '¿Usas gestor?', options: ['Sí', 'No'] },
  ] };

  async function openRenewal() {
    api.worker.renewalQuiz.mockResolvedValue(quiz);
    const onChanged = vi.fn();
    render(<CertificatesPage onOpenModule={vi.fn()} onChanged={onChanged}/>);
    await userEvent.click(await screen.findByRole('button', { name: 'Renovar con un repaso' }));
    expect(await screen.findByRole('heading', { name: 'Repaso de Contraseñas' })).toBeInTheDocument();
    return onChanged;
  }

  async function answer(choices) {
    for (const [i, choice] of choices.entries()) {
      await userEvent.click(within(screen.getAllByRole('radiogroup')[i]).getByRole('radio', { name: choice }));
    }
    await userEvent.click(screen.getByRole('button', { name: 'Enviar repaso' }));
  }

  it('sin 80 % deja reintentar y con 80 % renueva', async () => {
    api.worker.renew
      .mockResolvedValueOnce({ passed: false, correct: 1, total: 2, percent: 50, certificate: null, results: [
        { key: '1:0', is_correct: true, correct_index: 1, feedback: 'Bien.' }, { key: '1:1', is_correct: false, correct_index: 0, feedback: 'Usa un gestor.' }] })
      .mockResolvedValueOnce({ passed: true, correct: 2, total: 2, percent: 100, certificate: { ...EXPIRING, code: 'INKA-NEW0-NEW0-NEW0' }, results: [] });
    const onChanged = await openRenewal();
    expect(screen.getByRole('button', { name: 'Enviar repaso' })).toBeDisabled();
    await answer(['No', 'No']);
    expect(await screen.findByText('Aún no llegas al 80 %')).toBeInTheDocument();
    expect(screen.getByText('Usa un gestor.')).toBeInTheDocument();
    expect(api.worker.renew).toHaveBeenCalledWith(6, { answers: [{ key: '1:0', choice: 1 }, { key: '1:1', choice: 1 }] });

    await userEvent.click(screen.getByRole('button', { name: 'Intentar de nuevo' }));
    await answer(['No', 'Sí']);
    expect(await screen.findByText('Certificado renovado')).toBeInTheDocument();
    expect(screen.getByText(/INKA-NEW0-NEW0-NEW0/)).toBeInTheDocument();
    expect(onChanged).toHaveBeenCalled();
    await userEvent.click(screen.getByRole('button', { name: 'Ver mis certificados' }));
    expect(await screen.findByRole('heading', { name: 'Mis certificados' })).toBeInTheDocument();
  });

  it('muestra por qué no se puede renovar todavía', async () => {
    api.worker.renewalQuiz.mockRejectedValueOnce(new ApiError('Podrás renovarlo desde 30 días antes de que venza', 409));
    render(<CertificatesPage onOpenModule={vi.fn()}/>);
    await userEvent.click(await screen.findByRole('button', { name: 'Renovar con un repaso' }));
    expect(await screen.findByText('Podrás renovarlo desde 30 días antes de que venza')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Volver' }));
    expect(await screen.findByRole('heading', { name: 'Mis certificados' })).toBeInTheDocument();
  });
});

describe('tarjeta del inicio', () => {
  it.each([
    [{ active: 0, topics: 2, expiring: [], expired: [], next: { topic: 'Phishing', remaining: 2 } }, 'Te faltan 2 módulos para el certificado de Phishing.'],
    [{ active: 1, topics: 2, expiring: [EXPIRING], expired: [], next: null }, 'Tu certificado de Contraseñas vence en 12 días.'],
    [{ active: 0, topics: 1, expiring: [], expired: [{ ...CERT, status: 'expired' }], next: null }, 'Tu certificado de Phishing venció. Renuévalo con un repaso corto.'],
    [undefined, /Completa los módulos de un tema/],
  ])('muestra el mensaje según el estado', (summary, text) => {
    const setView = vi.fn();
    render(<CertificateHomeCard summary={summary} setView={setView}/>);
    expect(screen.getByText(text)).toBeInTheDocument();
  });

  it('lleva a la sección de certificados', async () => {
    const setView = vi.fn();
    render(<CertificateHomeCard summary={{ active: 2, topics: 3, expiring: [], expired: [], next: null }} setView={setView}/>);
    expect(screen.getByRole('heading', { name: '2 de 3 temas certificados' })).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Ver mis certificados' }));
    expect(setView).toHaveBeenCalledWith('certificados');
  });
});

describe('verificación pública', () => {
  const valid = { valid: true, status: 'active', status_label: 'Vigente', holder: 'María López', company: 'InkaSec Demo',
    topic: 'Phishing', issued_at: CERT.issued_at, expires_at: CERT.expires_at, code: CERT.code };

  it('verifica el código que viene en la dirección', async () => {
    api.certificates.verify.mockResolvedValueOnce(valid);
    render(<VerifyCertificatePage code="inka-7kq2-m9xp-4htr"/>);
    expect(await screen.findByText('Certificado válido')).toBeInTheDocument();
    expect(api.certificates.verify).toHaveBeenCalledWith('INKA-7KQ2-M9XP-4HTR');
    expect(screen.getByText('María López')).toBeInTheDocument();
  });

  it('avisa si el código no existe', async () => {
    api.certificates.verify.mockRejectedValueOnce(new ApiError('No existe', 404));
    render(<VerifyCertificatePage code="INKA-AAAA-AAAA-AAAA"/>);
    expect(await screen.findByText(/No existe un certificado con ese código/)).toBeInTheDocument();
  });

  it('permite escribir un código y explica si fue reemplazado', async () => {
    api.certificates.verify.mockResolvedValueOnce({ ...valid, valid: false, status: 'superseded', status_label: 'Reemplazado' });
    render(<VerifyCertificatePage code=""/>);
    const button = screen.getByRole('button', { name: 'Verificar' });
    expect(button).toBeDisabled();
    await userEvent.type(screen.getByLabelText('Código del certificado'), ' inka-old0-old0-old0 ');
    await userEvent.click(button);
    expect(api.certificates.verify).toHaveBeenCalledWith('INKA-OLD0-OLD0-OLD0');
    expect(await screen.findByText('Certificado reemplazado')).toBeInTheDocument();
    expect(screen.getByText(/reemplazado por una renovación/)).toBeInTheDocument();
    expect(window.location.pathname).toBe('/verificar/INKA-OLD0-OLD0-OLD0');
  });

  it('muestra errores de red tal cual', async () => {
    api.certificates.verify.mockRejectedValueOnce(new ApiError('Demasiadas consultas. Intenta en un minuto.', 429));
    render(<VerifyCertificatePage code="INKA-AAAA-AAAA-AAAA"/>);
    expect(await screen.findByText('Demasiadas consultas. Intenta en un minuto.')).toBeInTheDocument();
  });
});
