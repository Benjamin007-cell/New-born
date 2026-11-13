"""Build an offline browser annotation worksheet from candidate JSONL."""
import argparse
import json
from pathlib import Path
from .core import read_records

TEMPLATE = r'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Disclosure review pilot</title>
<style>body{font:17px system-ui;background:#f3f5f8;color:#172234;max-width:1000px;margin:40px auto;padding:0 20px}main{background:white;padding:28px;border-radius:14px}h1{font-size:30px}button,select{font:inherit;padding:10px;margin:4px;border:1px solid #bcc9d8;border-radius:7px;background:white;cursor:pointer}button.primary{background:#154f86;color:white}#text{white-space:pre-wrap;line-height:1.8;padding:20px;background:#f7f9fc;border:1px solid #cbd5e1}li{margin:12px 0}small{color:#40546d}#status{font-weight:600}a{color:#154f86}</style>
<h1>Review financial disclosures</h1><p>Select a complete clause, choose its category and add the label. Check suggested spans against the filing. Remove incorrect suggestions. Mark negatives reviewed too.</p>
<p><b>This pilot is unreviewed.</b> It cannot establish model accuracy. Save a checkpoint before closing this page. Export reviewed data after checking it.</p>
<main><div id="status"></div><p id="source"></p><p id="text"></p><select id="category" aria-label="Disclosure category"><option>COVENANT</option><option>FX_SENSITIVITY</option><option>AUDIT_NOTE</option></select><button id="add">Add selected clause</button><ul id="entities"></ul><p id="message" role="status"></p>
<label><input id="reviewed" type="checkbox"> I checked this text and all labels against the source</label><p><button id="previous">Previous</button><button id="next">Next</button><button id="checkpoint">Save checkpoint</button><button id="export" class="primary">Export reviewed data</button></p><label>Restore a checkpoint <input id="restore" type="file" accept=".jsonl"></label></main>
<p>Label policy: covenants cover restrictions, thresholds, breaches and compliance; FX sensitivity requires a quantified financial effect; audit notes cover opinions, key/critical matters and material going-concern disclosures. Exclude whitespace; include clause punctuation. Table fragments need special care.</p>
<script>
const initial=__DATA__;let rows=structuredClone(initial),index=0,selected=null;
const $=id=>document.getElementById(id),labels=new Set(['COVENANT','FX_SENSITIVITY','AUDIT_NOTE']);
function codepoints(s){return Array.from(s).length;}
function show(){const r=rows[index];selected=null;$('status').textContent=`Record ${index+1} of ${rows.length} · ${rows.filter(x=>x.annotation_status==='reviewed').length} reviewed`;$('text').textContent=r.text;$('reviewed').checked=r.annotation_status==='reviewed';$('message').textContent='';$('source').replaceChildren();const a=document.createElement('a');a.textContent=`${r.issuer||r.source_document} · ${r.page?'PDF page '+r.page:'paragraph '+r.paragraph}`;if((r.source_url||'').startsWith('https://')){a.href=r.source_url;a.target='_blank';a.rel='noopener noreferrer';}$('source').append(a);$('entities').replaceChildren();r.entities.sort((a,b)=>a.start-b.start).forEach((e,i)=>{const li=document.createElement('li');li.textContent=e.label+': '+Array.from(r.text).slice(e.start,e.end).join('');const b=document.createElement('button');b.textContent='Remove';b.onclick=()=>{r.entities.splice(i,1);r.annotation_status='unreviewed';show()};li.append(b);$('entities').append(li)});}
document.addEventListener('selectionchange',()=>{const s=window.getSelection();const node=$('text').firstChild;if(!node||!s||s.isCollapsed||s.anchorNode!==node||s.focusNode!==node)return;const lo=Math.min(s.anchorOffset,s.focusOffset),hi=Math.max(s.anchorOffset,s.focusOffset);selected={start:codepoints(node.textContent.slice(0,lo)),end:codepoints(node.textContent.slice(0,hi))};});
$('add').onclick=()=>{if(!selected){$('message').textContent='Select text inside the paragraph first.';return}const r=rows[index],e={...selected,label:$('category').value};if(r.entities.some(x=>e.start<x.end&&e.end>x.start)){$('message').textContent='This overlaps an existing span. Remove that span first.';return}e.text=Array.from(r.text).slice(e.start,e.end).join('');r.entities.push(e);r.annotation_status='unreviewed';show()};
$('reviewed').onchange=()=>{rows[index].annotation_status=$('reviewed').checked?'reviewed':'unreviewed';rows[index].review_method='browser-self-attestation';show()};
$('previous').onclick=()=>{index=Math.max(0,index-1);show()};$('next').onclick=()=>{index=Math.min(rows.length-1,index+1);show()};
function save(data,name){const blob=new Blob([data.map(r=>JSON.stringify(r)).join('\n')+'\n'],{type:'application/x-ndjson'}),a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000)}
$('checkpoint').onclick=()=>save(rows,'review-checkpoint.jsonl');$('export').onclick=()=>{const reviewed=rows.filter(r=>r.annotation_status==='reviewed');if(!reviewed.length){$('message').textContent='No reviewed records yet.';return}save(reviewed,'reviewed-pilot.jsonl')};
$('restore').onchange=async event=>{try{const loaded=(await event.target.files[0].text()).trim().split('\n').map(JSON.parse);if(loaded.length!==initial.length)throw Error('Wrong record count');const originals=new Map(initial.map(r=>[r.id,r])),ids=new Set();for(const r of loaded){const original=originals.get(r.id);if(!original||ids.has(r.id)||r.text!==original.text||r.source_document!==original.source_document)throw Error('Changed source or duplicate record');ids.add(r.id);if(!Array.isArray(r.entities))throw Error('Invalid entities');let end=0;for(const e of [...r.entities].sort((a,b)=>a.start-b.start)){if(!Number.isInteger(e.start)||!Number.isInteger(e.end)||e.start<end||e.end<=e.start||e.end>codepoints(r.text)||!labels.has(e.label))throw Error('Invalid span');end=e.end;}Object.assign(r,Object.fromEntries(Object.entries(original).filter(([k])=>!['entities','annotation_status','review_method'].includes(k))));}rows=loaded;index=0;show()}catch(e){$('message').textContent='Cannot restore: '+e.message}};show();
</script></html>'''

def build(source, output):
    rows=read_records(source)
    if not rows: raise ValueError('No records to review')
    data=json.dumps(rows,ensure_ascii=True).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    Path(output).write_text(TEMPLATE.replace('__DATA__',data),encoding='utf-8')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('input');p.add_argument('output');a=p.parse_args();build(a.input,a.output)
if __name__=='__main__':main()
