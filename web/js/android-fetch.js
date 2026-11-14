/* Android app: there is no server. Requests that send data (POST) go straight to the app's own Python engine
   through the bridge; pages and pictures (GET) are answered by the app directly as well. */
(() => {
  const AND = window.SeforimAndroid; if (!AND || !AND.request) return;
  const wait = {}; let n = 0;
  const b64 = buf => { let s = ""; const u = new Uint8Array(buf); for (let i = 0; i < u.length; i += 0x8000) s += String.fromCharCode.apply(null, u.subarray(i, i + 0x8000)); return btoa(s); };
  const unb64 = s => { const b = atob(s || ""); const u = new Uint8Array(b.length); for (let i = 0; i < b.length; i++) u[i] = b.charCodeAt(i); return u; };
  window.__andDone = (id, status, headers, body) => {
    const w = wait[id]; if (!w) return; delete wait[id];
    if (status === 0) return w.reject(new TypeError("The app's engine did not answer: " + headers));
    w.resolve(new Response(status === 204 ? null : unb64(body), { status, headers: JSON.parse(headers || "{}") }));
  };
  const native = window.fetch.bind(window);
  window.fetch = async (input, init = {}) => {
    const req = input instanceof Request ? input : null;
    const method = (init.method || (req && req.method) || "GET").toUpperCase();
    const url = new URL(req ? req.url : String(input), location.href);
    if (method === "GET" || url.origin !== location.origin) return native(input, init);
    const h = {}; new Headers(init.headers || (req && req.headers) || {}).forEach((v, k) => h[k] = v);
    let body = init.body ?? (req ? await req.arrayBuffer() : null);
    if (body == null) body = new ArrayBuffer(0);
    else if (typeof body === "string") { body = new TextEncoder().encode(body).buffer; h["content-type"] = h["content-type"] || "text/plain;charset=UTF-8"; }
    else if (body instanceof Blob) body = await body.arrayBuffer();
    else if (ArrayBuffer.isView(body)) body = body.buffer.slice(body.byteOffset, body.byteOffset + body.byteLength);
    else if (body instanceof URLSearchParams) body = new TextEncoder().encode(body.toString()).buffer;
    const id = ++n;
    return new Promise((resolve, reject) => { wait[id] = { resolve, reject }; AND.request(id, method, url.pathname + url.search, JSON.stringify(h), b64(body)); });
  };
})();
