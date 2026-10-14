// Local host adaptation. The original page, styles, navigation and tool UI remain intact.
(()=>{
  const realFetch=window.fetch.bind(window);
  window.fetch=(input,init)=>{
    if(typeof input==='string'&&input.startsWith('https://a4ai.dpdns.org/'))input=input.replace('https://a4ai.dpdns.org',location.origin);
    return realFetch(input,init);
  };
  document.addEventListener('DOMContentLoaded',()=>{
    if(window!==window.top)return;
    const explainLogin=()=>{
      for(const view of document.querySelectorAll('#view-login,.kat-box')){
        if(!view.querySelector('form')||view.querySelector('[data-local-login]'))continue;
        const message=document.createElement('p');message.dataset.localLogin='true';message.className='ka-note';
        message.textContent='로컬 복사본에는 원본 계정 서버가 연결되어 있지 않습니다. 공개 도구는 로그인 없이 사용할 수 있습니다.';
        view.prepend(message);view.querySelectorAll('input,form button').forEach(el=>el.disabled=true);
      }
    };
    new MutationObserver(explainLogin).observe(document.body,{childList:true,subtree:true});explainLogin();
  });
})();
