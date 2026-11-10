document.addEventListener('DOMContentLoaded',()=>{
  const year=document.querySelector('#year');if(year)year.textContent=new Date().getFullYear();
  const form=document.querySelector('#contactForm');
  if(form)form.addEventListener('submit',event=>{event.preventDefault();const name=form.querySelector('[name="name"]').value.trim();const message=document.querySelector('#formMessage');message.textContent=name?`Thanks, ${name}! This is a local demonstration; no message was sent.`:'Please enter your name.';if(name)form.reset();});
  const toggle=document.querySelector('#checklistBtn');if(toggle)toggle.addEventListener('click',()=>{const list=document.querySelector('#checklist');list.hidden=!list.hidden;toggle.textContent=list.hidden?'Show deployment checklist':'Hide deployment checklist';});
});
