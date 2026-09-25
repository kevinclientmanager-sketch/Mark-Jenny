import { api } from "./client";

export const coreLawsApi = {
  status: () => api.get("/core-laws/status"),
  unlock: (password: string) => api.post("/core-laws/unlock", { password }),
  setup: (password: string, laws: Array<{ plain_text: string; code?: string; category?: string }>) =>
    api.post("/core-laws/setup", { password, laws }),
  update: (lawId: string, plainText: string, code: string, password: string) =>
    api.post(`/core-laws/update?password=${encodeURIComponent(password)}`, { law_id: lawId, plain_text: plainText, code }),
  add: (plainText: string, code: string, category: string, password: string) =>
    api.post(`/core-laws/add?password=${encodeURIComponent(password)}`, { plain_text: plainText, code, category }),
  delete: (lawId: string, password: string) =>
    api.delete(`/core-laws/${lawId}?password=${encodeURIComponent(password)}`),
  enforce: () => api.get("/core-laws/enforce"),
  verify: () => api.post("/core-laws/verify", {}),
  changePassword: (currentPassword: string, newPassword: string) =>
    api.post("/core-laws/change-password", { current_password: currentPassword, new_password: newPassword }),
};
