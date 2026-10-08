import React, {useEffect, useMemo, useRef, useState} from 'react'
import {UploadCloud, Compass, ShieldCheck, CircleCheck, ChevronRight, ChevronDown, ChevronUp, LoaderCircle, AlertTriangle, FileText, BriefcaseBusiness, GraduationCap, FolderKanban, Award, Wrench, Target, MapPin, Plus, X, Check, ArrowUpRight, ArrowLeft, Info, HeartHandshake, Sparkles, Route, Clock3, Trash2, Flag} from 'lucide-react'
import './review.css'

/* ---------- shared ---------- */
export const VISA_GROUPS = [
  {label:'Study and graduate', options:['Student visa (subclass 500)','Student Guardian visa (subclass 590)','Temporary Graduate visa (subclass 485)','Training visa (subclass 407)']},
  {label:'Working holiday', options:['Working Holiday visa (subclass 417)','Work and Holiday visa (subclass 462)']},
  {label:'Employer sponsored and temporary work', options:['Skills in Demand visa (subclass 482)','Employer Nomination Scheme visa (subclass 186)','Skilled Employer Sponsored Regional visa (subclass 494)','Temporary Work Short Stay Specialist visa (subclass 400)','Temporary Work International Relations visa (subclass 403)','Temporary Activity visa (subclass 408)']},
  {label:'Skilled migration', options:['Skilled Independent visa (subclass 189)','Skilled Nominated visa (subclass 190)','Skilled Work Regional Provisional visa (subclass 491)','Permanent Residence Skilled Regional visa (subclass 191)','National Innovation visa (subclass 858)']},
  {label:'Family and partner', options:['Partner visa onshore (subclass 820)','Partner visa permanent (subclass 801)','Partner visa provisional (subclass 309)','Partner visa migrant (subclass 100)','Prospective Marriage visa (subclass 300)','Sponsored Parent Temporary visa (subclass 870)']},
  {label:'Visitor and other temporary', options:['Visitor visa (subclass 600)','Electronic Travel Authority (subclass 601)','eVisitor (subclass 651)']},
  {label:'Bridging visas', options:['Bridging visa A','Bridging visa B','Bridging visa C','Bridging visa E']},
  {label:'Other status', options:['Australian citizen','Australian permanent resident','Offshore with no current Australian visa','Other Australian visa','Unsure of current visa or status']}
]
function Brand(){return <div className="brand"><div className="brandmark"><Compass size={20}/></div><span>Pathway</span><span className="beta">LIVE</span></div>}
const MONTHS=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
const ym=d=>d?d.slice(0,7):''
const monthLabel=d=>{if(!d) return '';const [y,m]=d.split('-');return `${MONTHS[Number(m)-1]} ${y}`}
const toIdx=d=>{const [y,m]=d.split('-').map(Number);return y*12+m}
export function fmtMonths(m){if(m==null) return 'Dates missing';const y=Math.floor(m/12),mo=m%12;return [y?`${y} yr${y>1?'s':''}`:'',mo?`${mo} mo${mo>1?'s':''}`:''].filter(Boolean).join(' ')||(m===0?'None yet':'Under 1 month')}
const todayIso=()=>new Date().toISOString().slice(0,10)
function roleMonths(r){if(!r.start) return null;const end=r.current||!r.end?todayIso():r.end;return Math.max(1,toIdx(end)-toIdx(r.start)+(r.current?0:1))}
export function unionMonths(items,from=null){
  const spans=items.filter(r=>r.start).map(r=>{let a=toIdx(r.start);const end=r.current||!r.end?todayIso():r.end;const b=toIdx(end)+(r.current?0:1);if(from){a=Math.max(a,toIdx(from)+1)}return [a,b]}).filter(([a,b])=>b>a).sort((x,y)=>x[0]-y[0])
  let total=0,ca=null,cb=null;for(const [a,b] of spans){if(cb==null||a>cb){if(cb!=null) total+=cb-ca;ca=a;cb=b}else cb=Math.max(cb,b)}if(cb!=null) total+=cb-ca;return total
}
const LEVEL_LABEL={doctorate:'Doctorate',masters_research:'Masters (research)',masters_coursework:'Masters (coursework)',bachelor:'Bachelor',diploma:'Diploma',trade:'Trade certificate',secondary:'Secondary school',other:'Other'}
const LEVEL_RANK={doctorate:6,masters_research:5,masters_coursework:4,bachelor:3,diploma:2,trade:1,other:0,secondary:-1}
const isRelevant=(role,occ)=>{if(!occ) return false;const t=(role.title||'').toLowerCase(),b=(role.bullets||[]).join(' ').toLowerCase(),k=occ.keywords||[];return t.includes(occ.title.toLowerCase().split(' ')[0])||k.some(w=>t.includes(w))||k.filter(w=>b.includes(w)).length>=3}
const FIELD_LABEL={engineering:'Engineering',ict:'IT, computing or data science',accounting:'Accounting or finance',nursing:'Nursing or midwifery',teaching:'Teaching',trades:'Trade',other:'Other'}
const ASSESSOR={engineering:'Engineers Australia',ict:'Australian Computer Society',accounting:'CPA Australia, CA ANZ or IPA',nursing:'ANMAC',teaching:'AITSL',trades:'Trades Recognition Australia',other:'VETASSESS'}
const GOALS=['Land a graduate or entry-level role','Grow in my current field','Secure permanent residence','Find an employer who sponsors','Change career direction']

/* ---------- landing ---------- */
const PARSE_STEPS=['Reading your document','Finding experience and dates','Separating volunteering and projects','Matching your occupation']
export function Landing({onFile,onDemo,busy,error,fileName,saved,onResume}){
  const [drag,setDrag]=useState(false)
  const [step,setStep]=useState(0)
  const input=useRef(null)
  useEffect(()=>{if(!busy){setStep(0);return}const t=setInterval(()=>setStep(s=>Math.min(PARSE_STEPS.length-1,s+1)),700);return ()=>clearInterval(t)},[busy])
  const take=f=>f&&!busy&&onFile(f)
  return <main className="landing2">
    <nav className="l2nav"><Brand/>{saved?.profile&&saved.profile.name&&!saved.isSample&&<button className="l2resume" onClick={onResume}>Continue as {saved.profile.name}<ArrowUpRight size={15}/></button>}</nav>
    <section className="l2hero">
      <div className="l2copy">
        <span className="l2kicker"><Sparkles size={14}/>For international students and graduates in Australia</span>
        <h1>Turn your resume into a plan to <em>work</em> and <em>stay</em> in Australia.</h1>
        <p>Upload your resume. Pathway reads your real experience, projects and qualifications, maps them to the occupation migration uses, and builds a dated plan with live jobs and a route to permanent residence.</p>
        <ol className="l2steps">
          <li><b>1</b><div><strong>Upload</strong><span>PDF, DOCX or TXT</span></div></li>
          <li><b>2</b><div><strong>Check what we found</strong><span>Edit anything before it is used</span></div></li>
          <li><b>3</b><div><strong>Get your plan</strong><span>Jobs, points and a PR roadmap</span></div></li>
        </ol>
      </div>
      <div className={`l2upload ${drag?'drag':''} ${busy?'busy':''}`} onDragOver={e=>{e.preventDefault();setDrag(true)}} onDragLeave={()=>setDrag(false)} onDrop={e=>{e.preventDefault();setDrag(false);take(e.dataTransfer.files?.[0])}}>
        {busy?<div className="l2parsing"><LoaderCircle className="spin" size={30}/><h2>Reading {fileName||'your resume'}</h2><ul>{PARSE_STEPS.map((s,i)=><li key={s} className={i<step?'done':i===step?'now':''}>{i<step?<Check size={14}/>:i===step?<LoaderCircle size={14} className="spin"/>:<span/>}{s}</li>)}</ul></div>:<>
          <div className="l2icon"><UploadCloud size={28}/></div>
          <h2>Drop your resume here</h2>
          <p>or choose a file. Your most recent resume works best.</p>
          <input ref={input} type="file" accept=".pdf,.docx,.txt" hidden onChange={e=>take(e.target.files?.[0])}/>
          <button className="primary l2choose" onClick={()=>input.current?.click()}><FileText size={17}/>Choose resume</button>
          <small>PDF, DOCX or TXT · scanned images cannot be read</small>
          {error&&<div className="l2error"><AlertTriangle size={15}/>{error}</div>}
          <button className="l2demo" onClick={onDemo}>No resume handy? Explore a sample profile<ChevronRight size={15}/></button>
        </>}
        <div className="l2privacy"><ShieldCheck size={14}/>Your resume stays between your browser and the Pathway server. Job searches send only the role and location.</div>
      </div>
    </section>
    <section className="l2what">
      <h3>What Pathway reads from your resume</h3>
      <div className="l2grid">
        <div><BriefcaseBusiness size={18}/><b>Experience, counted properly</b><p>Each role's own dates, paid work separated from volunteering, and what counts after graduation.</p></div>
        <div><GraduationCap size={18}/><b>Education with your major</b><p>Degree, major and Australian study, which decide the 485 and your assessing authority.</p></div>
        <div><FolderKanban size={18}/><b>Projects as evidence</b><p>For graduates, projects often carry the skills employers look for.</p></div>
        <div><Target size={18}/><b>Your occupation, mapped</b><p>We suggest the occupation migration uses and handle the ANZSCO code for you.</p></div>
      </div>
    </section>
  </main>
}

/* ---------- review ---------- */
function Section({icon:Icon,title,subtitle,count,children,right,id}){return <section className="rvCard" id={id}><header><span className="rvIcon"><Icon size={18}/></span><div><h2>{title}{count!=null&&<em>{count}</em>}</h2>{subtitle&&<p>{subtitle}</p>}</div>{right}</header>{children}</section>}
function Bullets({items,max=2}){const [all,setAll]=useState(false);if(!items?.length) return null;const shown=all?items:items.slice(0,max);return <><ul className="rvBullets">{shown.map((b,i)=><li key={i}>{b}</li>)}</ul>{items.length>max&&<button className="rvMore" onClick={()=>setAll(!all)}>{all?<><ChevronUp size={13}/>Show less</>:<><ChevronDown size={13}/>{items.length-max} more</>}</button>}</>}
function MonthInput({value,onChange,disabled}){return <input type="month" value={ym(value)} disabled={disabled} onChange={e=>onChange(e.target.value?`${e.target.value}-01`:null)}/>}
export function VisaSelect({value,onChange}){return <select value={value||''} onChange={e=>onChange(e.target.value)}><option value="">Select your current visa or status</option>{VISA_GROUPS.map(g=><optgroup key={g.label} label={g.label}>{g.options.map(o=><option key={o} value={o}>{o}</option>)}</optgroup>)}</select>}

export function ResumeReview({initialResume,profile,fileName,onBack,onConfirm,catalogue}){
  const [r,setR]=useState(()=>structuredClone(initialResume))
  const [about,setAbout]=useState({name:initialResume.name||profile.name||'',location:initialResume.location||profile.location||'',visa:profile.visa||'',visaExpiry:profile.visaExpiry||''})
  const [occ,setOcc]=useState(initialResume.suggestions?.[0]||null)
  const [custom,setCustom]=useState('')
  const [goals,setGoals]=useState(profile.goals||['Land a graduate or entry-level role','Secure permanent residence'])
  const [relevant,setRelevant]=useState(()=>initialResume.experience.map(e=>!!e.relevant))
  const [editing,setEditing]=useState(null)
  const patchRole=(i,k,v)=>setR(p=>({...p,experience:p.experience.map((e,j)=>j===i?{...e,[k]:v}:e)}))
  const removeRole=i=>{setR(p=>({...p,experience:p.experience.filter((_,j)=>j!==i)}));setRelevant(p=>p.filter((_,j)=>j!==i))}
  const addRole=()=>{setR(p=>({...p,experience:[{title:'',org:'',location:'',start:null,end:null,current:false,bullets:[],where:'unknown'},...p.experience]}));setRelevant(p=>[true,...p]);setEditing(0)}
  const toPaid=i=>{const v=r.volunteering[i];setR(p=>({...p,volunteering:p.volunteering.filter((_,j)=>j!==i),experience:[...p.experience,{...v,volunteer:false}].sort((a,b)=>(b.start||'').localeCompare(a.start||''))}));setRelevant(p=>[...p,false])}
  const pickOcc=o=>{setOcc(o);setCustom('');setRelevant(r.experience.map(e=>isRelevant(e,o)))}
  const highest=useMemo(()=>[...r.education].sort((a,b)=>(LEVEL_RANK[b.level]??0)-(LEVEL_RANK[a.level]??0))[0],[r.education])
  const gradDate=highest&&highest.level!=='secondary'?highest.end:null
  const roles=r.experience.map(e=>({...e,months:roleMonths(e)}))
  const relRoles=roles.filter((_,i)=>relevant[i])
  const totals={paid:unionMonths(roles),relevant:unionMonths(relRoles),post:gradDate?unionMonths(relRoles,gradDate):unionMonths(relRoles)}
  const postAU=gradDate?unionMonths(relRoles.filter(e=>e.where!=='overseas'),gradDate):0
  const postOS=gradDate?unionMonths(relRoles.filter(e=>e.where==='overseas'),gradDate):0
  const occTitle=custom||occ?.title||''
  const occField=occ?.field||'other'
  const occKeywords=occ?.keywords||[]
  const skills=r.skillGroups
  const removeSkill=(g,s)=>setR(p=>({...p,skillGroups:p.skillGroups.map((x,i)=>i===g?{...x,items:x.items.filter(y=>y!==s)}:x)}))
  const addSkill=(g,s)=>s&&setR(p=>({...p,skillGroups:p.skillGroups.map((x,i)=>i===g?{...x,items:[...x.items,s]}:x)}))
  const ready=about.name&&about.location&&about.visa&&occTitle
  function confirm(){
    const skillList=[...new Set([...r.skillGroups.flatMap(g=>g.items),...r.projects.flatMap(p=>p.tools||[])])].slice(0,48)
    const degree=highest?`${highest.degree}${highest.major?`, ${highest.major}`:''}`:''
    const candidates=[...new Set([occ?.searchTitle||occTitle,...(r.suggestions||[]).filter(s=>s.title!==occ?.title).map(s=>s.searchTitle),...relRoles.map(e=>e.title)].filter(Boolean))].slice(0,6)
    const profilePatch={name:about.name,location:about.location,visa:about.visa,detectedVisa:about.visa,visaExpiry:about.visaExpiry,occupation:occTitle,
      occupationTitle:occTitle,anzsco:custom?'':(occ?.anzsco||''),osca:'',careerFamily:FIELD_LABEL[occField],roleCandidates:candidates.map(t=>({title:t})),education:degree,
      experienceYears:Math.round(totals.relevant/12*10)/10,skills:skillList,goals,goal:goals.join('; '),resume:{...r,experience:r.experience.map((e,i)=>({...e,relevant:!!relevant[i]}))}}
    const hasCurrentRelevant=roles.some((e,i)=>relevant[i]&&e.current)
    const circ={fieldOfStudy:custom?'':occField,qualification:highest&&highest.level!=='secondary'?highest.level:'',auQualification:highest?!!highest.australian:null,institution:highest?.institution||'',
      studyState:highest?.state||'',studyRegional:['cat2','cat3'].includes(highest?.regionalCampus)?'yes':'no',courseCompletion:gradDate||'',auExperienceYears:Math.round(postAU/12*10)/10,
      overseasExperienceYears:Math.round(postOS/12*10)/10,employedInOccupation:hasCurrentRelevant?'yes':'no',preferredStates:highest?.state?[highest.state]:[]}
    onConfirm(profilePatch,circ)
  }
  return <main className="review">
    <nav className="rvNav"><Brand/><button className="ghost" onClick={onBack}><ArrowLeft size={15}/>Start over</button></nav>
    <div className="rvWrap">
      <div className="rvHead">
        <div className="rvSteps"><span className="done"><Check size={13}/>Upload</span><i/><span className="on">2 Check details</span><i/><span>3 Your plan</span></div>
        <h1>Check what we found{fileName?<> in <b>{fileName}</b></>:''}</h1>
        <p>Nothing is used until you confirm it. Fix anything that looks wrong; every total updates as you go.</p>
        {(r.warnings||[]).map((w,i)=><div key={i} className="rvWarn"><AlertTriangle size={15}/>{w}</div>)}
      </div>
      <div className="rvGrid">
        <div className="rvMain">
          <Section icon={MapPin} title="About you" subtitle="Location and visa decide which jobs and migration routes apply.">
            <div className="rvForm">
              <label>Name<input value={about.name} onChange={e=>setAbout({...about,name:e.target.value})}/></label>
              <label>Location in Australia<input value={about.location} placeholder="e.g. Brisbane, QLD" onChange={e=>setAbout({...about,location:e.target.value})}/>{r.locationBasis&&<small>Found from: {r.locationBasis}</small>}</label>
              <label>Current visa or status<VisaSelect value={about.visa} onChange={v=>setAbout({...about,visa:v})}/>{!about.visa&&<small className="need">Needed for your plan</small>}</label>
              <label>Visa expiry (if known)<input type="date" value={about.visaExpiry} onChange={e=>setAbout({...about,visaExpiry:e.target.value})}/></label>
            </div>
            {(r.contact?.email||r.contact?.phone)&&<p className="rvContact">{[r.contact.email,r.contact.phone,r.contact.linkedin].filter(Boolean).join(' · ')}</p>}
          </Section>

          <Section icon={Target} title="Your target occupation" subtitle="We suggest these from your degree, summary, roles and projects. You never need to know a code; we use it behind the scenes.">
            <div className="occGrid">{(r.suggestions||[]).map(s=><button key={s.title} className={`occCard ${occ?.title===s.title&&!custom?'on':''}`} onClick={()=>pickOcc(s)}>
              <div className="occTop"><span className="occRadio">{occ?.title===s.title&&!custom&&<Check size={12}/>}</span><b>{s.title}</b></div>
              <ul>{s.reasons.map(x=><li key={x}>{x}</li>)}</ul>
              <small>Assessed by {ASSESSOR[s.field]} · ANZSCO {s.anzsco}</small>
            </button>)}</div>
            <div className="occOther"><label>Or choose another<select value={!custom&&occ&&!(r.suggestions||[]).some(s=>s.title===occ.title)?occ.title:''} onChange={e=>{const o=catalogue.find(c=>c.title===e.target.value);o&&pickOcc(o)}}><option value="">Browse occupations</option>{catalogue.map(c=><option key={c.title} value={c.title}>{c.title}</option>)}</select></label><label>Not listed? Type it<input value={custom} placeholder="e.g. Biomedical Engineer" onChange={e=>setCustom(e.target.value)}/></label></div>
            {custom&&<p className="rvNote"><Info size={14}/>A typed occupation is used for job searches. Migration checks work best with a listed occupation, so pick the closest one if you can.</p>}
          </Section>

          <Section icon={BriefcaseBusiness} title="Work experience" count={roles.length} subtitle={`Tick the roles relevant to ${occTitle||'your occupation'}. Volunteering is listed separately and not counted.`} right={<button className="rvAdd" onClick={addRole}><Plus size={14}/>Add role</button>}>
            <div className="expTotals">
              <div><span>Paid experience</span><b>{fmtMonths(totals.paid)}</b><small>{roles.length} role{roles.length!==1?'s':''}, overlaps counted once</small></div>
              <div className="hl"><span>Relevant to {occTitle||'your occupation'}</span><b>{fmtMonths(totals.relevant)}</b><small>Used for job matching</small></div>
              <div><span>Relevant, after graduating</span><b>{fmtMonths(totals.post)}</b><small>{gradDate?`After ${monthLabel(gradDate)}; counts for migration points`:'Add your graduation date'}</small></div>
            </div>
            <div className="expList">{roles.map((e,i)=>{const pre=gradDate&&e.start&&(e.current?false:e.end&&e.end<=gradDate);const isEdit=editing===i;return <article key={i} className={`expRow ${relevant[i]?'rel':''}`}>
              <label className="expCheck" title="Relevant to your target occupation"><input type="checkbox" checked={!!relevant[i]} onChange={()=>setRelevant(p=>p.map((x,j)=>j===i?!x:x))}/></label>
              <div className="expBody">
                {isEdit?<div className="expEdit">
                  <input value={e.title} placeholder="Job title" onChange={ev=>patchRole(i,'title',ev.target.value)}/><input value={e.org} placeholder="Employer" onChange={ev=>patchRole(i,'org',ev.target.value)}/><input value={e.location} placeholder="Location" onChange={ev=>patchRole(i,'location',ev.target.value)}/>
                  <div className="expDates"><MonthInput value={e.start} onChange={v=>patchRole(i,'start',v)}/><span>to</span><MonthInput value={e.end} disabled={e.current} onChange={v=>patchRole(i,'end',v)}/><label><input type="checkbox" checked={!!e.current} onChange={ev=>patchRole(i,'current',ev.target.checked)}/>Current</label></div>
                  <select value={e.where||'unknown'} onChange={ev=>patchRole(i,'where',ev.target.value)}><option value="australia">In Australia</option><option value="remote">Remote</option><option value="overseas">Overseas</option><option value="unknown">Location unclear</option></select>
                  <button className="primary small" onClick={()=>setEditing(null)}><Check size={14}/>Done</button>
                </div>:<>
                  <div className="expTop"><div><b>{e.title||'Untitled role'}</b><span>{e.org}{e.location?` · ${e.location}`:''}</span></div><div className="expDur"><b>{fmtMonths(e.months)}</b><span>{e.start?`${monthLabel(e.start)} – ${e.current?'Present':monthLabel(e.end)}`:'No dates'}</span></div></div>
                  <div className="expTags">{e.current&&<span className="t now">Current</span>}{e.internship&&<span className="t">Internship</span>}{e.where==='overseas'&&<span className="t">Overseas</span>}{e.where==='remote'&&<span className="t">Remote</span>}{e.where==='australia'&&<span className="t">Australia</span>}{pre&&<span className="t muted">Before graduation</span>}{relevant[i]?<span className="t rel">Relevant</span>:<span className="t muted">Not counted as relevant</span>}</div>
                  <Bullets items={e.bullets}/>
                </>}
              </div>
              {!isEdit&&<div className="expActions"><button onClick={()=>setEditing(i)}>Edit</button><button onClick={()=>removeRole(i)} aria-label="Remove role"><Trash2 size={14}/></button></div>}
            </article>})}</div>
            {!roles.length&&<p className="rvEmpty">No paid roles found. Add them so experience can be counted.</p>}
          </Section>

          {r.volunteering.length>0&&<Section icon={HeartHandshake} title="Volunteering" count={r.volunteering.length} subtitle="Shown on your profile, but not counted as work experience.">
            <div className="volList">{r.volunteering.map((v,i)=><div key={i} className="volRow"><div><b>{v.title}</b><span>{v.org}{v.start?` · ${monthLabel(v.start)} – ${v.current?'Present':monthLabel(v.end)}`:''}</span></div><button className="rvLink" onClick={()=>toPaid(i)}>This was paid work</button></div>)}</div>
          </Section>}

          <Section icon={GraduationCap} title="Education" count={r.education.length} subtitle="Your highest Australian qualification drives the 485, Australian study points and the course completion date.">
            <div className="eduList">{r.education.map((e,i)=><article key={i} className={`eduRow ${e.level==='secondary'?'muted':''}`}>
              <div className="eduTop"><div><b>{e.degree}</b><span>{e.institution}{e.location?` · ${e.location}`:''}</span></div><span className="eduDates">{e.start?`${monthLabel(e.start)} – ${e.current?'Present':monthLabel(e.end)}`:''}</span></div>
              {e.level!=='secondary'&&<label className="eduMajor">Major or concentration<input value={e.major||''} placeholder="e.g. Mechatronics" onChange={ev=>setR(p=>({...p,education:p.education.map((x,j)=>j===i?{...x,major:ev.target.value}:x)}))}/></label>}
              <div className="expTags"><span className="t">{LEVEL_LABEL[e.level]||'Other'}</span>{e.honours&&<span className="t">Honours</span>}{e.australian&&e.level!=='secondary'&&<span className="t rel">Australian qualification</span>}{e===highest&&e.level!=='secondary'&&<span className="t now">Used for your plan</span>}{e.level==='secondary'&&<span className="t muted">Not used for migration</span>}</div>
              {e.achievements?.length>0&&<ul className="rvBullets">{e.achievements.map((a,j)=><li key={j}>{a}</li>)}</ul>}
            </article>)}</div>
          </Section>

          <Section icon={FolderKanban} title="Projects" count={r.projects.length} subtitle="Strong evidence for graduate and internship roles. Matching tools are highlighted.">
            <div className="prjGrid">{r.projects.map((p,i)=>{const hits=occKeywords.filter(k=>`${p.name} ${(p.tools||[]).join(' ')} ${(p.bullets||[]).join(' ')}`.toLowerCase().includes(k));return <article key={i} className="prjCard">
              <div className="prjTop"><b>{p.name}</b><button aria-label="Remove project" onClick={()=>setR(x=>({...x,projects:x.projects.filter((_,j)=>j!==i)}))}><X size={14}/></button></div>
              {p.tools?.length>0&&<div className="chips">{p.tools.map(t=><span key={t}>{t}</span>)}</div>}
              <Bullets items={p.bullets} max={1}/>
              {hits.length>0&&<p className="prjHit"><Check size={13}/>Evidence for {occTitle}: {hits.slice(0,4).join(', ')}</p>}
            </article>})}</div>
            {!r.projects.length&&<p className="rvEmpty">No projects found. Capstone, thesis and personal projects are valuable evidence; add them to your resume.</p>}
          </Section>

          <Section icon={Award} title="Achievements, publications and certifications" count={r.achievements.length+r.certifications.length}>
            {r.achievements.length>0&&<ul className="achList">{r.achievements.map((a,i)=><li key={i}><Flag size={14}/><div><span>{a.text}</span><small>{a.source}</small></div><button aria-label="Remove" onClick={()=>setR(x=>({...x,achievements:x.achievements.filter((_,j)=>j!==i)}))}><X size={13}/></button></li>)}</ul>}
            {r.certifications.length>0&&<div className="certList">{r.certifications.map((c,i)=><div key={i}><CircleCheck size={15}/><div><b>{c.name}</b><span>{[c.issuer,c.date].filter(Boolean).join(' · ')}</span></div></div>)}</div>}
            {(r.licences||[]).length>0&&<p className="rvMeta">{r.licences.join(' · ')}</p>}
          </Section>

          <Section icon={Wrench} title="Skills" count={skills.reduce((n,g)=>n+g.items.length,0)} subtitle="Used to match you with job adverts. Remove anything you would not want to be tested on.">
            <div className="skillGroups">{skills.map((g,gi)=><div key={gi} className="skillGroup"><span>{g.name}</span><div className="chips edit">{g.items.map(s=><span key={s}>{s}<button aria-label={`Remove ${s}`} onClick={()=>removeSkill(gi,s)}><X size={11}/></button></span>)}<input placeholder="Add" onKeyDown={e=>{if(e.key==='Enter'){addSkill(gi,e.currentTarget.value.trim());e.currentTarget.value=''}}}/></div></div>)}</div>
          </Section>

          <Section icon={Route} title="What do you want next?" subtitle="Optional. It shapes the order of your recommendations.">
            <div className="goalChips">{GOALS.map(g=><button key={g} className={goals.includes(g)?'on':''} onClick={()=>setGoals(p=>p.includes(g)?p.filter(x=>x!==g):[...p,g])}>{goals.includes(g)&&<Check size={13}/>}{g}</button>)}</div>
          </Section>
        </div>

        <aside className="rvSide">
          <div className="rvSnap">
            <span className="rvKicker">Your snapshot</span>
            <h3>{about.name||'Your name'}</h3>
            <dl>
              <div><dt>Target occupation</dt><dd>{occTitle||<em>Choose one</em>}</dd></div>
              {occ&&!custom&&<div><dt>Skills assessed by</dt><dd>{ASSESSOR[occField]}</dd></div>}
              <div><dt>Relevant experience</dt><dd>{fmtMonths(totals.relevant)}</dd></div>
              <div><dt>After graduating</dt><dd>{fmtMonths(totals.post)}</dd></div>
              <div><dt>Highest qualification</dt><dd>{highest?`${LEVEL_LABEL[highest.level]}${highest.major?`, ${highest.major}`:''}`:'Not found'}</dd></div>
              <div><dt>Projects</dt><dd>{r.projects.length}</dd></div>
              <div><dt>Location</dt><dd>{about.location||<em>Add location</em>}</dd></div>
              <div><dt>Visa</dt><dd>{about.visa||<em>Select visa</em>}</dd></div>
            </dl>
            <button className="primary rvGo" disabled={!ready} onClick={confirm}>Looks right, build my plan<ArrowUpRight size={17}/></button>
            {!ready&&<small className="need">Add name, location, visa and occupation to continue.</small>}
            <p className="rvFine"><Clock3 size={12}/>Experience comes only from each role's own dates. Experience before graduation helps job applications but does not earn migration points.</p>
          </div>
        </aside>
      </div>
    </div>
  </main>
}

/* ---------- sample for the demo path (fictional person) ---------- */
export const SAMPLE_RESUME={name:'Alex Nguyen',contact:{email:'alex.nguyen@example.com',phone:'',linkedin:''},location:'Brisbane, QLD',locationBasis:'Sample profile',summary:'Graduate Mechatronics Engineer focused on automation and embedded control.',
  education:[{degree:'Bachelor of Engineering (Honours)',major:'Mechatronics',honours:true,institution:'Queensland University of Technology',location:'Brisbane',level:'bachelor',start:'2022-02-01',end:'2026-11-01',current:false,australian:true,state:'QLD',regionalCampus:'no',achievements:['Capstone shortlisted for the engineering showcase']}],
  experience:[{title:'Undergraduate Automation Engineer',org:'Sample Controls Pty Ltd',location:'Brisbane',where:'australia',state:'QLD',start:'2025-11-01',end:'2026-02-01',current:false,bullets:['Wrote PLC logic for conveyor interlocks in TIA Portal.','Built HMI screens for alarm handling.'],volunteer:false,internship:true,relevant:true},
    {title:'Retail Assistant',org:'Sample Supermarket',location:'Brisbane',where:'australia',state:'QLD',start:'2023-03-01',end:'2025-10-01',current:false,bullets:['Customer service and stock control.'],volunteer:false,internship:false,relevant:false}],
  volunteering:[{title:'Volunteer Electrical Member',org:'University Racing Team',start:'2024-03-01',end:'2024-11-01',current:false,bullets:[],volunteer:true}],
  projects:[{name:'Conveyor sorting cell',tools:['TIA Portal','PLCSIM','WinCC'],bullets:['Sorted parts by colour with sensor validation and fault recovery.']},{name:'Balancing robot',tools:['C','FreeRTOS','ARM Cortex-M4'],bullets:['LQR balance controller with IMU fusion.']}],
  skillGroups:[{name:'Languages',items:['C/C++','Python','Structured Text']},{name:'Automation',items:['Siemens TIA Portal','PLC','HMI']},{name:'Tools',items:['MATLAB','Simulink','SolidWorks','Git']}],
  certifications:[],publications:[],achievements:[{text:'Capstone shortlisted for the engineering showcase',source:'Queensland University of Technology'}],licences:[],other:[],warnings:[],
  suggestions:[{title:'Mechatronics Engineer',anzsco:'233999',anzscoTitle:'Engineering Professionals nec',field:'engineering',searchTitle:'Mechatronics Engineer',reasons:['Your summary describes you this way','Matches your degree major'],keywords:['mechatronic','robotics','automation','control systems','plc','hmi','embedded','engineer','engineering']},
    {title:'Automation and Controls Engineer',anzsco:'233311',anzscoTitle:'Electrical Engineer',field:'engineering',searchTitle:'Controls Engineer',reasons:['Projects show plc, hmi'],keywords:['plc','scada','hmi','tia portal','commissioning','engineer','engineering']}]}
