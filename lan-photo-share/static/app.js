(function(){
  try{
    const ws = new WebSocket((location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/ws');
    ws.onmessage = (e) => {
      const data = JSON.parse(e.data);
      if(data.type === 'new_photo'){
        const grid = document.querySelector('.grid');
        if(!grid) return;
        const a = document.createElement('a');
        a.className = 'card';
        a.target = '_blank';
        a.href = '/media/originals/' + data.title ? data.title : data.thumb_url.replace('/media/thumbs/','/media/originals/');
        a.innerHTML = `
          <img loading="lazy" src="${data.thumb_url}">
          <div class="meta">
            <strong>${data.title || '(無題)'}</strong>
            <small>new</small>
          </div>`;
        grid.prepend(a);
      }
    };
  }catch(e){ /* no-op */ }
})();