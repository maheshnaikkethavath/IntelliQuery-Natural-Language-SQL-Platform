import axios from "axios";

const http = axios.create({ baseURL: "/api/v1", timeout: 120000 });
http.interceptors.response.use(
  (r) => r,
  (e) => {
    const d = e.response?.data?.detail;
    const msg = typeof d === "string" ? d : Array.isArray(d) ? d.map((x) => x.msg).join("; ") : e.message;
    return Promise.reject(new Error(msg));
  }
);
const get = (u, p) => http.get(u, { params: p }).then((r) => r.data);
const post = (u, b) => http.post(u, b).then((r) => r.data);

export const api = {
  connect: (b) => post("/database/connect", b),
  status: () => get("/database/status"),
  databases: () => get("/database/list"),
  selectDb: (database) => post("/database/select", { database }),
  schema: (refresh = false) => get("/database/schema", { refresh }),
  generate: (request) => post("/ai/generate-sql", { request }),
  validate: (sql) => post("/query/validate", { sql }),
  preview: (sql) => post("/query/preview", { sql }),
  execute: (b) => post("/query/execute", b),
  history: (limit = 50) => get("/query/history", { limit }).then((d) => d.items),
  stats: () => get("/query/stats"),
};
