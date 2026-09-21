/* Session-only presentation choices. Never triggers a refresh or grants authority. */
(() => {
  const prefix = 'pops.navigation.v1:';
  const read = key => { try { return JSON.parse(sessionStorage.getItem(prefix + key)); } catch { return null; } };
  const save = (key, value) => { try { sessionStorage.setItem(prefix + key, JSON.stringify(value)); } catch {} };
  window.popsChoices = {read, save};
  document.addEventListener('DOMContentLoaded', () => {
    const path = location.pathname;
    if (path.startsWith('/performance/')) save(path, location.search);
    document.querySelectorAll('.product-nav a').forEach(a => {
      const target = new URL(a.href);
      if (target.origin !== location.origin || !target.pathname.startsWith('/performance/')) return;
      const query = read(target.pathname);
      if (!target.search && typeof query === 'string' && (query === '' || query.startsWith('?'))) {
        target.search = query; a.href = target.pathname + target.search;
      }
    });
    if (path !== '/season') return;
    const ids = ['seasonWeek','seasonTeam','positive','omitCompleted'];
    const stored = read('nfl-sheet') || {};
    for (const id of ids) {
      const el = document.getElementById(id); if (!el) continue;
      if (el.type === 'checkbox') el.checked = stored[id] === true;
      else if ([...el.options].some(o => o.value === stored[id])) el.value = stored[id];
      el.dispatchEvent(new Event('change'));
      el.addEventListener('change', () => {
        const state = {};
        ids.forEach(key => {const x=document.getElementById(key); if(x) state[key]=x.type==='checkbox'?x.checked:x.value;});
        save('nfl-sheet',state);
      });
    }
    const sort = read('nfl-sort');
    if (sort && Number.isInteger(sort.column)) {
      const button=document.querySelector(`th button[data-column="${sort.column}"]`);
      if(button) {
        button.click();
        if(button.closest('th').getAttribute('aria-sort') !== sort.direction) button.click();
      }
    }
    document.querySelectorAll('th button').forEach(button=>button.addEventListener('click',()=>save('nfl-sort',{
      column:Number(button.dataset.column), direction:button.closest('th').getAttribute('aria-sort')
    })));
  });
})();
