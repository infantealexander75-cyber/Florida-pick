const C='fpa-v1.0b40';
self.addEventListener('install',e=>{e.waitUntil(caches.open(C).then(async c=>{await Promise.allSettled(['./','index.html','sw.js','manifest.webmanifest','icon-192.png','icon-512.png'].map(u=>fetch(new Request(u,{cache:'reload'})).then(r=>{if(r.ok)return c.put(u,r);}).catch(()=>{})));}).then(()=>self.skipWaiting()));});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(k=>Promise.all(k.filter(x=>x!==C).map(x=>caches.delete(x)))).then(()=>self.clients.claim()));});
self.addEventListener('fetch',e=>{const u=new URL(e.request.url);if(e.request.method!=='GET')return;
  const page=e.request.mode==='navigate'||u.pathname.endsWith('/')||u.pathname.endsWith('index.html');
  if(page||u.pathname.endsWith('results.json')||u.hostname==='raw.githubusercontent.com'){
    e.respondWith(fetch(e.request,page?{cache:'no-cache'}:undefined).then(n=>{if(page&&n.ok&&u.origin===location.origin){const c=n.clone();caches.open(C).then(x=>x.put(e.request,c));}return n;}).catch(()=>caches.match(e.request).then(r=>r||(page?caches.match('index.html'):Response.error()))));return;}
  e.respondWith(caches.match(e.request).then(r=>r||fetch(e.request).then(n=>{if(n.ok&&u.origin===location.origin){const c=n.clone();caches.open(C).then(x=>x.put(e.request,c));}return n;})));});
