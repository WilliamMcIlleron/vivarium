addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request));
});

async function handleRequest(request) {
  const url = new URL(request.url);
  const path = url.pathname;

  const routes = {
    '/': { key: 'viewer.html', type: 'text/html; charset=utf-8' },
    '/viewer': { key: 'viewer.html', type: 'text/html; charset=utf-8' },
    '/viewer/': { key: 'viewer.html', type: 'text/html; charset=utf-8' },
    '/viewer/index.html': { key: 'viewer.html', type: 'text/html; charset=utf-8' },
    '/state/world.json': { key: 'world.json', type: 'application/json' },
    '/state/changelog.md': { key: 'changelog.md', type: 'text/plain; charset=utf-8' },
    '/state/lore.md': { key: 'lore.md', type: 'text/plain; charset=utf-8' },
  };

  const entry = routes[path];
  if (!entry) return new Response('not found', { status: 404 });

  const value = await VIVARIUM_STATE.get(entry.key);
  if (value === null) return new Response('not found', { status: 404 });

  return new Response(value, {
    headers: {
      'content-type': entry.type,
      'cache-control': entry.key === 'viewer.html' ? 'public, max-age=300' : 'no-store',
    },
  });
}
