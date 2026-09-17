"""Compact update controls; reading or polling never starts work."""
import json
from performance_reader import text,date


def panel(status,token):
    running=status.get('status')=='running'
    disabled=running or not status.get('configured') or status.get('status') in ('interrupted','unavailable')
    body='<div class="report-update" role="group" aria-label="Performance report update" style="margin:0"><button id="update-report"'+(' disabled' if disabled else '')+'>Update report</button>'
    message=status.get('message','' if status.get('configured') else 'Report updates are not configured on this installation.')
    body+='<span id="update-result" role="status" aria-live="polite" style="margin-left:12px">'+text(message)+'</span>'
    when=status.get('completed_at') or status.get('started_at')
    if when:body+='<p class="muted">Last update attempt: '+text(date(when))+'</p>'
    if status.get('collection_error') or status.get('collection_availability')=='unavailable':body+='<p>Collection status unavailable. The scientific report remains available.</p>'
    if status.get('error') or status.get('collection_error') or status.get('status') in ('interrupted','unavailable'):
        body+='<details><summary>Update details</summary><p>'+text(status.get('error') or status.get('collection_error') or 'An update did not record completion. Confirm no reporting process is running, inspect its retained log and selected report, then use the documented manual recovery procedure.')+'</p></details>'
    body+='</div>'
    body+='''<script>
const updateButton=document.getElementById('update-report'), updateResult=document.getElementById('update-result');
async function pollReportUpdate(){
 try {
  const response=await fetch('/api/mlb/performance/update');
  if(!response.ok)throw new Error('Could not read update status. Reload to check the saved outcome.');
  const value=await response.json();
  if(value.status==='running'){updateResult.textContent=value.message;setTimeout(pollReportUpdate,1500);}
  else {window.location.reload();}
 } catch(error){updateResult.textContent=error.message;}
}
updateButton.addEventListener('click',async()=>{
 updateButton.disabled=true;updateResult.textContent='Starting update…';
 try {
  const response=await fetch('/api/mlb/performance/update',{method:'POST',headers:{'Content-Type':'application/json','X-Pops-Token':TOKEN},body:'{}'});
  const value=await response.json();if(!response.ok)throw new Error(value.error||'Update could not start');
  updateResult.textContent=value.message;pollReportUpdate();
 }catch(error){updateResult.textContent=error.message+' Reload to check the saved outcome.';}
});
if(RUNNING)pollReportUpdate();
</script>'''.replace('TOKEN',json.dumps(token).replace('<','\\u003c')).replace('RUNNING','true' if running else 'false')
    return body
