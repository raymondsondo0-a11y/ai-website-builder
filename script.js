document.addEventListener('DOMContentLoaded',()=>{
  const filterButtons=document.querySelectorAll('.filter-btn');
  const practicals=document.querySelectorAll('.practical-item');
  filterButtons.forEach(button=>button.addEventListener('click',()=>{
    filterButtons.forEach(item=>item.classList.remove('active')); button.classList.add('active');
    const filter=button.dataset.filter;
    practicals.forEach(card=>{card.style.display=filter==='all'||card.dataset.category===filter?'block':'none';});
  }));
  const addDrop=document.getElementById('addDrop'), reset=document.getElementById('resetLab'), select=document.getElementById('chemicalSelect');
  const volumeRead=document.getElementById('volumeRead'), phRead=document.getElementById('phRead'), resultRead=document.getElementById('resultRead'), liquid=document.getElementById('simLiquid'), stage=document.querySelector('.beaker-stage'), state=document.getElementById('simState');
  let volume=0, acid=0, base=0;
  function update(){
    const ph=Math.max(0,Math.min(14,7+(base-acid)*0.65));
    volumeRead.textContent=volume+' mL'; phRead.textContent=ph.toFixed(1);
    resultRead.textContent=ph<6.5?'Acidic':ph>7.5?'Basic':'Neutral';
    resultRead.style.color=ph<6.5?'#f49aae':ph>7.5?'#78baff':'#73e5bd';
    liquid.style.height=Math.min(82,35+volume*2.2)+'%'; liquid.style.backgroundColor=ph<6.5?'#e88ba9aa':ph>7.5?'#77aeeaaa':'#69c9dcbb';
    state.textContent=volume===0?'READY':resultRead.textContent.toUpperCase();
  }
  addDrop.addEventListener('click',()=>{
    volume+=10; select.value==='acid'?acid++:base++; update();
    stage.classList.remove('reacting'); void stage.offsetWidth; stage.classList.add('reacting');
    setTimeout(()=>stage.classList.remove('reacting'),900);
  });
  reset.addEventListener('click',()=>{volume=0;acid=0;base=0;update();});
  update();
  document.querySelectorAll('.nav-link,.navbar-brand,.nav-cta').forEach(link=>link.addEventListener('click',()=>{const nav=document.getElementById('mainNav');if(nav.classList.contains('show')) bootstrap.Collapse.getOrCreateInstance(nav).hide();}));
});