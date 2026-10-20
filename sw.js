const C='fpa-v0.9.30';
self.addEventListener('install',e=>{e.waitUntil(caches.open(C).then(c=>c.addAll(['./','index.html','manifest.webmanifest','icon-192.png','icon-512.png'])).then(()=>self.skipWaiting()));});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(k=>Promise.all(k.filter(x=>x!==C).map(x=>caches.delete(x)))).then(()=>self.clients.claim()));});
self.addEventListener('fetch',e=>{const u=new URL(e.request.url);if(e.request.method!=='GET')return;
  const page=e.request.mode==='navigate'||u.pathname.endsWith('/')||u.pathname.endsWith('index.html');
  if(page||u.pathname.endsWith('results.json')||u.hostname==='raw.githubusercontent.com'){
    e.respondWith(fetch(e.request).then(n=>{if(page&&u.origin===location.origin){const c=n.clone();caches.open(C).then(x=>x.put(e.request,c));}return n;}).catch(()=>caches.match(e.request).then(r=>r||caches.match('index.html'))));return;}
  e.respondWith(caches.match(e.request).then(r=>r||fetch(e.request).then(n=>{if(u.origin===location.origin){const c=n.clone();caches.open(C).then(x=>x.put(e.request,c));}return n;})));});
