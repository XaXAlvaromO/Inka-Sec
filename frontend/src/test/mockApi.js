// La API de mentira que usan las pruebas: cada prueba decide qué responde cada llamada.
import { vi } from 'vitest';

export class ApiError extends Error {
  constructor(message, status = 0) { super(message); this.status = status; }
}

export function createApiMock() {
  return {
    ApiError,
    api: {
      auth: { me: vi.fn(), login: vi.fn(), verify2FA: vi.fn(), logout: vi.fn() },
      worker: {
        dashboard: vi.fn(), module: vi.fn(), saveComb: vi.fn(), gradeCapacity: vi.fn(), saveReflections: vi.fn(),
        completeModule: vi.fn(), answerChallenge: vi.fn(), checkStep: vi.fn(), certificates: vi.fn(),
        renewalQuiz: vi.fn(), renew: vi.fn(), certificatePdf: vi.fn(),
      },
      certificates: { verify: vi.fn() },
      manager: {
        dashboard: vi.fn(), topics: vi.fn(), getModule: vi.fn(), createModule: vi.fn(), updateModule: vi.fn(),
        getChallenge: vi.fn(), createChallenge: vi.fn(), updateChallenge: vi.fn(), assignable: vi.fn(),
        assignments: vi.fn(), createAssignment: vi.fn(), deleteAssignment: vi.fn(), stats: vi.fn(),
      },
      admin: {
        dashboard: vi.fn(), users: vi.fn(), areas: vi.fn(), createArea: vi.fn(), audit: vi.fn(), reportSummary: vi.fn(),
        createUser: vi.fn(), updateUser: vi.fn(), deleteUser: vi.fn(), exportReport: vi.fn(),
      },
      superadmin: {
        companies: vi.fn(), createCompany: vi.fn(), companyUsers: vi.fn(), updateUser: vi.fn(), deleteUser: vi.fn(),
      },
    },
  };
}
