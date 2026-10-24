for(const button of document.querySelectorAll('.copy-code'))button.addEventListener('click',async()=>{
 const code=button.parentElement.querySelector('code');try{await navigator.clipboard.writeText(code.textContent);button.textContent='Copied';}catch{const selection=getSelection(),range=document.createRange();range.selectNodeContents(code);selection.removeAllRanges();selection.addRange(range);button.textContent='Selected';}setTimeout(()=>button.textContent='Copy',1800);
});
