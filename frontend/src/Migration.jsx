import React, {useMemo, useState} from 'react'
import {ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, ReferenceLine, CartesianGrid, BarChart, Bar, Legend} from 'recharts'
import {Route, GitBranch, Calculator, ListChecks, CalendarClock, Map as MapIcon, ShieldAlert, ChevronDown, ChevronUp, Download, Printer, Info, CircleCheck, CircleX, CircleHelp, Hourglass, GraduationCap, Languages, Award, Heart, Building2, MapPin, Scale, ArrowRight, Clock3, ExternalLink, BriefcaseBusiness, TriangleAlert, Target, Check, LoaderCircle, BadgeCheck, FileText, Layers, Flag, Wallet, Sparkles, SlidersHorizontal, Signpost, CalendarPlus, RefreshCw, Lock} from 'lucide-react'
import './migration.css'
import {VisaSelect} from './ResumeReview'

/* ---------- shared helpers ---------- */
export const fmtDate=(v,opts={month:'short',year:'numeric'})=>{if(!v) return 'Date unknown';const d=new Date(v+(v.length===10?'T00:00:00':''));return Number.isNaN(d.getTime())?v:d.toLocaleDateString('en-AU',opts)}
const fullDate=v=>fmtDate(v,{day:'numeric',month:'short',year:'numeric'})
const money=n=>n==null?'Check estimator':`$${Math.round(n).toLocaleString('en-AU')}`
const VISA_COLOR={'500':'#6b7fd7','485':'#2a9d8f','482':'#e4723b','186':'#0c6b58','189':'#0c6b58','190':'#0c6b58','191':'#0c6b58','801':'#0c6b58','858':'#0c6b58','491':'#b0648a','494':'#b0648a','820':'#d1495b','BVA':'#9aa6a2','current':'#6b7fd7'}
const visaColor=c=>VISA_COLOR[c]||'#7b8a86'
const LEVEL_CLASS={'Strong':'strong','Viable':'viable','Depends on employer':'employer','Stretch':'stretch','Needs evidence':'evidence','Long shot':'longshot','Not preferred':'muted','Not available':'blocked'}
export const LevelBadge=({level})=><span className={`lvl ${LEVEL_CLASS[level]||'muted'}`}>{level}</span>
export function RouteChips({route=[],compact=false}){return <div className={`routeChips ${compact?'compact':''}`}>{route.map((c,i)=><React.Fragment key={c+i}>{i>0&&<ArrowRight className="routeArrow"/>}<span className="visaChip" style={{'--c':visaColor(c)}}>{/^\d+$/.test(c)?c:c.toUpperCase()}</span></React.Fragment>)}</div>}
export const shortName=s=>{if(!s) return '';const st=s.state?` (${s.state})`:'';const k=s.id.split('-')[0];return ({'189':'189 Skilled Independent','190':`190 State nomination${st}`,'491':`491 Regional${st} then 191`,'482':'482 then 186 Transition','186':'186 Direct Entry','494':'494 Regional employer then 191','partner':'Partner 820 then 801'})[k]||s.name}
const KIND_ICON={study:GraduationCap,test:Languages,assessment:Award,apply:FileText,visa:BadgeCheck,work:BriefcaseBusiness,decision:Target,pr:Flag,prepare:ListChecks,step:Signpost}

const SUB_TABS=[
  {id:'plan',label:'My plan',icon:Route},
  {id:'routes',label:'Compare routes',icon:Layers},
  {id:'points',label:'Points',icon:Calculator},
  {id:'checks',label:'Checks & deadlines',icon:ListChecks},
  {id:'evidence',label:'States & evidence',icon:MapIcon},
]
const TRACKS=[
  {id:'independent',label:'Independent',icon:Target,blurb:'Points tested. No employer needed: 189, 190 and 491.'},
  {id:'sponsored',label:'Employer sponsored',icon:Building2,blurb:'An employer nominates you. Not points tested: 482 to 186, 494.'},
  {id:'family',label:'Partner',icon:Heart,blurb:'Through your Australian citizen or PR partner.'},
]

/* ---------- calendar export ---------- */
function icsDate(v){return v.replaceAll('-','')}
export function downloadIcs(events,name='pathway-migration.ics'){
  const esc=s=>String(s||'').replace(/[,;\\]/g,m=>'\\'+m).replace(/\n/g,'\\n')
  const lines=['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//Pathway//Migration roadmap//EN','CALSCALE:GREGORIAN']
  events.filter(e=>e.date).forEach((e,i)=>{const d=icsDate(e.date);const next=new Date(e.date+'T00:00:00');next.setDate(next.getDate()+1);const end=next.toISOString().slice(0,10).replaceAll('-','')
    lines.push('BEGIN:VEVENT',`UID:pathway-${i}-${d}@pathway.local`,`DTSTAMP:${new Date().toISOString().replace(/[-:]/g,'').slice(0,15)}Z`,`DTSTART;VALUE=DATE:${d}`,`DTEND;VALUE=DATE:${end}`,`SUMMARY:${esc(e.title)}`,`DESCRIPTION:${esc(e.detail)}`,'BEGIN:VALARM','TRIGGER:-P14D','ACTION:DISPLAY',`DESCRIPTION:${esc(e.title)}`,'END:VALARM','END:VEVENT')})
  lines.push('END:VCALENDAR')
  const url=URL.createObjectURL(new Blob([lines.join('\r\n')],{type:'text/calendar'}))
  const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)
}

/* ---------- main view ---------- */
export default function Migration({plan,loading,error,profile,setProfile,circumstances,setCircumstances,activeId,setActiveId,checks,toggleCheck,onJobsAction,jobs,onRefresh,sample,catalogue=[]}){
  const [tab,setTab]=useState('plan')
  const [compare,setCompare]=useState(null)
  if(!plan&&loading) return <div className="singleView"><MigrationSkeleton/></div>
  if(!plan) return <div className="singleView"><section className="card dataEmpty"><TriangleAlert/><b>The migration planner is unavailable</b><p>{error||'The planning service did not respond. Check that the backend is running, then retry.'}</p><button className="primary" onClick={onRefresh}><RefreshCw size={16}/>Retry</button></section></div>
  const strategies=plan.strategies||[]
  const active=strategies.find(s=>s.id===activeId)||strategies[0]
  const compared=(compare||strategies.slice(0,3).map(s=>s.id)).filter(id=>strategies.some(s=>s.id===id))
  const openPlan=id=>{setActiveId(id);setTab('plan');window.scrollTo?.({top:0,behavior:'smooth'})}
  return <div className="singleView migrationApp">
    <PrHero plan={plan} active={active} loading={loading}/>
    <Circumstances plan={plan} profile={profile} setProfile={setProfile} c={circumstances} set={setCircumstances} sample={sample} catalogue={catalogue}/>
    {plan.context?.settled?<section className="card settledCard"><BadgeCheck/><div><h3>{plan.headline?.title}</h3><p>{plan.headline?.detail}</p></div></section>:<>
      <nav className="subTabs" role="tablist">{SUB_TABS.map(t=><button key={t.id} role="tab" aria-selected={tab===t.id} className={tab===t.id?'on':''} onClick={()=>setTab(t.id)}><t.icon size={16}/>{t.label}{t.id==='checks'&&<em>{(plan.deadlines||[]).filter(d=>d.severity==='high').length}</em>}</button>)}</nav>
      {tab==='plan'&&active&&<PlanView plan={plan} strategy={active} strategies={strategies} setActiveId={setActiveId} checks={checks} toggleCheck={toggleCheck} onJobsAction={onJobsAction} goRoutes={()=>setTab('routes')}/>}
      {tab==='plan'&&!active&&<section className="card dataEmpty"><TriangleAlert/><b>No route can be estimated yet</b><p>Answer the questions above, or open Compare routes to see why routes were ruled out.</p></section>}
      {tab==='routes'&&<Routes plan={plan} strategies={strategies} activeId={active?.id} compared={compared} setCompare={setCompare} openPlan={openPlan}/>}
      {tab==='points'&&<PointsLab plan={plan} c={circumstances} set={setCircumstances}/>}
      {tab==='checks'&&<><Deadlines plan={plan} active={active}/><VisaChecks visas={plan.visas||[]}/></>}
      {tab==='evidence'&&<Evidence plan={plan} jobs={jobs} onJobsAction={onJobsAction} profile={profile}/>}
    </>}
    <footer className="migFoot"><Info size={14}/><span>Decision support, not migration advice. Rulebook {plan.rulebook?.version}, verified {fullDate(plan.rulebook?.verified)}. Confirm criteria with Home Affairs, the relevant state and a registered migration agent before lodging anything.</span></footer>
  </div>
}

function MigrationSkeleton(){return <><div className="prHero skeletonHero"><div className="skeleton" style={{height:160}}><div/><div/><div/></div></div><div className="skeleton" style={{height:420}}><div/><div/><div/></div></>}

/* ---------- hero ---------- */
function Ring({value,max,label,sub,tone}){const r=34,c=2*Math.PI*r,p=Math.max(0,Math.min(1,max?value/max:0));return <div className="ring"><svg viewBox="0 0 80 80" aria-hidden="true"><circle cx="40" cy="40" r={r} className="ringTrack"/><circle cx="40" cy="40" r={r} className={`ringValue ${tone||''}`} strokeDasharray={`${c*p} ${c}`} transform="rotate(-90 40 40)"/></svg><div><b>{label}</b><span>{sub}</span></div></div>}
function PrHero({plan,active,loading}){
  const ctx=plan.context||{},pts=plan.points||{}
  const days=ctx.daysOnVisa
  const target=active?.points?.target
  return <section className="prHero">
    <div className="heroGlow"/>
    <div className="heroMain">
      <span className="heroKicker"><Sparkles size={14}/>PR navigator {loading&&<LoaderCircle size={13} className="spin"/>}</span>
      <h2>{ctx.settled?'You are already settled.':<>Your road to permanent residence</>}</h2>
      {active&&<><p className="heroLead">Recommended now: <b>{active.name}</b>. {active.reasons?.[0]}</p><RouteChips route={active.route}/></>}
    </div>
    <div className="heroStats">
      <div className="heroStat"><Ring value={days!=null?Math.max(0,days):0} max={730} label={days!=null?`${Math.max(0,days)}`:'?'} sub="days" tone={days!=null&&days<120?'warn':''}/><div><span>Current visa</span><b>{ctx.visa&&ctx.visa!=='unknown'?(ctx.visaText||ctx.visa):'Not set'}</b><small>{ctx.visaExpiry?`Expires ${fullDate(ctx.visaExpiry)}`:'Add expiry for gap warnings'}</small></div></div>
      <div className="heroStat"><Ring value={pts.total||0} max={Math.max(100,target||0)} label={pts.total??'–'} sub="points" tone={(pts.total||0)>=65?'good':'warn'}/><div><span>Points today</span><b>{pts.total>=65?'Above the 65 pass mark':'Below the 65 pass mark'}</b><small>{target?`${active?.points?.targetBasis==='user'?'Your target':'Latest published minimum'}: ${target}`:'No published minimum for your occupation'}</small></div></div>
      <div className="heroStat wide"><div className="heroIcon"><Flag/></div><div><span>Earliest PR window for this route</span><b>{active?.prWindow?.label||'Not estimable yet'}</b><small>{active?.monthsToPr!=null?`About ${active.monthsToPr} months from today, if each step lands`:'Depends on an invitation or input still missing'}</small></div></div>
      <div className="heroStat wide"><div className="heroIcon"><Wallet/></div><div><span>Government charges on this route</span><b>{active?money(active.costs.government):'–'}</b><small>{active?`Plus about ${money(active.costs.otherLow)} to ${money(active.costs.otherHigh)} for tests, assessments and checks`:''}</small></div></div>
    </div>
    <div className="liveStrip">{(plan.liveSources||[]).map(s=><a key={s.id} className={`liveSrc ${s.status==='fresh'?'ok':s.status==='fallback'?'fb':'bad'}`} href={s.sourceUrl||undefined} target="_blank" rel="noreferrer" title={s.detail}><i/>{s.label}<small>{s.status==='fresh'?'live':s.status==='fallback'?'rulebook':s.status==='partial'?'partial':'unavailable'}</small></a>)}</div>
  </section>
}

/* ---------- circumstances ---------- */
const Q_OPTS=[['','Select'],['bachelor','Bachelor or honours'],['masters_coursework','Masters (coursework)'],['masters_research','Masters (research)'],['doctorate','Doctorate (PhD)'],['diploma','Diploma'],['trade','Trade qualification'],['other','Other']]
const ENG_OPTS=[['','Not tested'],['competent','Competent (IELTS 6 each)'],['proficient','Proficient (IELTS 7 each)'],['superior','Superior (IELTS 8 each)'],['vocational','Below competent']]
const SA_OPTS=[['','Select'],['none','Not started'],['submitted','Submitted'],['positive','Positive outcome']]
const PARTNER_OPTS=[['','Select'],['single','Single'],['partner_citizen_pr','Partner is an Australian citizen or PR'],['partner_skilled','Partner: skilled (assessment + competent English)'],['partner_competent_english','Partner: competent English only'],['partner_other','Partner: none of the above']]
const EMP_OPTS=[['','Select'],['yes','Yes'],['no','No']]
const YNM=[['','Select'],['yes','Yes'],['maybe','Maybe'],['no','No']]
const STATE_CODES=['QLD','NSW','VIC','SA','WA','TAS','ACT','NT']

function F({label,children,hint,missing}){return <label className={`mField ${missing?'missing':''}`}><span>{label}{missing&&<em>affects plan</em>}</span>{children}{hint&&<small>{hint}</small>}</label>}
function Sel({value,onChange,opts}){return <select value={value??''} onChange={e=>onChange(e.target.value)}>{opts.map(([v,l])=><option key={v} value={v}>{l}</option>)}</select>}
function Num({value,onChange,step=0.5,min=0}){return <input type="number" step={step} min={min} value={value??''} onChange={e=>onChange(e.target.value===''?'':Number(e.target.value))}/>}
function Toggle({value,onChange,label}){return <button type="button" className={`mToggle ${value?'on':''}`} aria-pressed={!!value} onClick={()=>onChange(!value)}><i/>{label}</button>}
function Circumstances({plan,profile,setProfile,c,set,sample,catalogue=[]}){
  const suggested=profile.resume?.suggestions||[]
  const allOcc=catalogue.length?catalogue:suggested
  const pickOcc=title=>{const o=[...suggested,...allOcc].find(x=>x.title===title);if(!o) return
    setProfile(p=>({...p,occupation:o.title,occupationTitle:o.title,anzsco:o.anzsco,occupationField:o.field,occupationSuggested:false}))
    set(prev=>({...prev,fieldOfStudy:o.field}))}
  const [open,setOpen]=useState(!!(plan.missing||[]).length)
  const [more,setMore]=useState(false)
  const miss=new Set((plan.missing||[]).map(m=>m.field))
  const s=(k,v)=>set(prev=>({...prev,[k]:v}))
  const ctx=plan.context||{}
  const field=c.fieldOfStudy||ctx.field||''
  const assessor=(ctx.fields||[]).find(f=>f.value===field)?.assessor
  const regionalStudy=['yes','cat2','cat3'].includes(c.studyRegional)?'yes':'no'
  const employer=['yes','offer','sponsoring','interested'].includes(c.employer)?'yes':['no','none'].includes(c.employer)?'no':''
  return <section className={`card circCard ${open?'open':''}`}>
    <button className="circHead" onClick={()=>setOpen(!open)} aria-expanded={open}>
      <div><span className="kicker">Your circumstances</span><h3>{(plan.missing||[]).length?`${plan.missing.length} answer${plan.missing.length>1?'s':''} would sharpen this plan`:'Your answers are complete'}</h3><p>{open?'Every change updates your plan straight away. Saved on this device.':'Tap to review or change your answers.'}</p></div>
      <div className="missChips">{(plan.missing||[]).slice(0,3).map(m=><span key={m.field} title={m.why}>{m.label}</span>)}</div>{open?<ChevronUp/>:<ChevronDown/>}
    </button>
    {open&&<>
      {sample&&<div className="sampleNote"><Info size={14}/>These are sample answers for the demo profile. Replace them with yours.</div>}
      <div className="circGrid four">
        <fieldset><legend><Lock size={14}/>You</legend>
          <F label="Current visa" missing={!profile.visa}><VisaSelect value={profile.visa} onChange={v=>setProfile(p=>({...p,visa:v,detectedVisa:v}))}/></F>
          <F label="Occupation for your visa plan" hint={`${profile.occupationSuggested?'Suggested from your resume. ':''}Decides your skills assessor and occupation lists. It does not limit your job search.`}><select value={profile.occupationTitle||profile.occupation||''} onChange={e=>pickOcc(e.target.value)}><option value="">Choose an occupation</option>{suggested.length>0&&<optgroup label="Suggested from your resume">{suggested.map(o=><option key={'s'+o.title} value={o.title}>{o.title}</option>)}</optgroup>}<optgroup label="All occupations">{allOcc.filter(o=>!suggested.some(x=>x.title===o.title)).map(o=><option key={o.title} value={o.title}>{o.title}</option>)}</optgroup></select></F>
          <F label="Visa expiry" missing={miss.has('visaExpiry')}><input type="date" value={profile.visaExpiry||''} onChange={e=>setProfile(p=>({...p,visaExpiry:e.target.value}))}/></F>
          <F label="Date of birth" missing={miss.has('dob')}><input type="date" value={c.dob||''} onChange={e=>s('dob',e.target.value)}/></F>
          <F label="Relationship" missing={miss.has('partner')}><Sel value={c.partner} onChange={v=>s('partner',v)} opts={PARTNER_OPTS}/></F>
          {c.partner==='partner_citizen_pr'&&<div className="two"><F label="Relationship type"><Sel value={c.partnerRelationship} onChange={v=>s('partnerRelationship',v)} opts={[['','Select'],['married','Married'],['registered','Registered'],['de_facto','De facto']]}/></F><F label="Months together"><Num value={c.relationshipMonths} step={1} onChange={v=>s('relationshipMonths',v)}/></F></div>}
        </fieldset>
        <fieldset><legend><GraduationCap size={14}/>Study</legend>
          <F label="Field of study" hint={assessor?`Skills assessed by ${assessor}`:'Decides your assessing authority'}><Sel value={field} onChange={v=>s('fieldOfStudy',v)} opts={[['','Select'],...(ctx.fields||[]).map(f=>[f.value,f.label])]}/></F>
          <F label="Highest qualification"><Sel value={c.qualification} onChange={v=>s('qualification',v)} opts={Q_OPTS}/></F>
          <div className="two"><F label="Study state"><Sel value={c.studyState} onChange={v=>s('studyState',v)} opts={[['','Select'],...STATE_CODES.map(x=>[x,x])]}/></F><F label="Regional campus?"><Sel value={regionalStudy} onChange={v=>s('studyRegional',v)} opts={[['no','No'],['yes','Yes']]}/></F></div>
          <F label="Course completion" missing={miss.has('courseCompletion')} hint="Date on your completion letter, actual or expected"><input type="date" value={c.courseCompletion||''} onChange={e=>s('courseCompletion',e.target.value)}/></F>
        </fieldset>
        <fieldset><legend><Languages size={14}/>English and skills</legend>
          <F label="English level" missing={miss.has('englishLevel')} hint="Lowest band counts"><Sel value={c.englishLevel} onChange={v=>s('englishLevel',v)} opts={ENG_OPTS}/></F>
          <F label="Skills assessment" missing={miss.has('skillsAssessment')} hint={assessor}><Sel value={c.skillsAssessment==='planned'?'none':c.skillsAssessment} onChange={v=>s('skillsAssessment',v)} opts={SA_OPTS}/></F>
          <div className="toggleRow"><Toggle value={c.naati} onChange={v=>s('naati',v)} label="NAATI CCL passed"/>{ctx.pyEligible&&<Toggle value={c.professionalYear} onChange={v=>s('professionalYear',v)} label="Professional Year done"/>}</div>
        </fieldset>
        <fieldset><legend><BriefcaseBusiness size={14}/>Work and preferences</legend>
          <F label="Working in your field now?" missing={miss.has('employedInOccupation')}><Sel value={c.employedInOccupation} onChange={v=>s('employedInOccupation',v)} opts={[['','Select'],['yes','Yes, 20+ hours a week'],['no','Not yet']]}/></F>
          <F label="An employer will sponsor you?" missing={miss.has('employer')} hint={employer==='no'?'Sponsored routes are hidden':'Yes shows 482 and 186 routes'}><Sel value={employer} onChange={v=>s('employer',v)} opts={EMP_OPTS}/></F>
          <F label="Live regionally for 3+ years?" missing={miss.has('regional')}><Sel value={c.regional} onChange={v=>s('regional',v)} opts={YNM}/></F>
          <F label="States to target"><div className="stateChips">{STATE_CODES.map(st=>{const on=(c.preferredStates||[]).includes(st);return <button type="button" key={st} className={on?'on':''} onClick={()=>s('preferredStates',on?(c.preferredStates||[]).filter(x=>x!==st):[...(c.preferredStates||[]),st].slice(-2))}>{st}</button>})}</div></F>
        </fieldset>
      </div>
      <button className="moreBtn" onClick={()=>setMore(!more)} aria-expanded={more}>{more?<ChevronUp size={15}/>:<ChevronDown size={15}/>}{more?'Hide extra details':'More details (optional): experience, dates, salary'}</button>
      {more&&<div className="circGrid four extra">
        <fieldset><F label="Australian skilled years"><Num value={c.auExperienceYears} onChange={v=>s('auExperienceYears',v)}/></F><F label="Overseas skilled years"><Num value={c.overseasExperienceYears} onChange={v=>s('overseasExperienceYears',v)}/></F></fieldset>
        <fieldset><F label="Months worked in target state" hint="20+ hours a week, after graduating"><Num value={c.stateEmploymentMonths} step={1} onChange={v=>s('stateEmploymentMonths',v)}/></F><F label="Months worked regionally"><Num value={c.regionalEmploymentMonths} step={1} onChange={v=>s('regionalEmploymentMonths',v)}/></F></fieldset>
        <fieldset><F label="English test date"><input type="date" value={c.englishTestDate||''} onChange={e=>s('englishTestDate',e.target.value)}/></F>{['submitted','positive'].includes(c.skillsAssessment)&&<F label="Assessment date"><input type="date" value={c.skillsAssessmentDate||''} onChange={e=>s('skillsAssessmentDate',e.target.value)}/></F>}<F label="Passport country" hint="UK, US, Canada, NZ and Ireland passports are exempt from English tests"><input value={c.passport||''} onChange={e=>s('passport',e.target.value)}/></F></fieldset>
        <fieldset>{employer==='yes'&&<F label="Salary (AUD a year)"><Num value={c.salary} step={1000} onChange={v=>s('salary',v)}/></F>}{profile.visa?.includes('482')&&<F label="Months with your sponsor"><Num value={c.sponsorMonths} step={1} onChange={v=>s('sponsorMonths',v)}/></F>}<div className="toggleRow"><Toggle value={c.auQualification!==false} onChange={v=>s('auQualification',v)} label="Australian degree"/><Toggle value={c.specialistEducation} onChange={v=>s('specialistEducation',v)} label="STEM research degree"/></div></fieldset>
      </div>}
      {(plan.assumptions||[]).length>0&&<div className="assumeNote"><Info size={14}/><div>{plan.assumptions.map((a,i)=><p key={i}>{a}</p>)}</div></div>}
    </>}
  </section>
}

/* ---------- routes ---------- */
function TrackCards({plan,strategies,activeId,onPick}){
  const ctx=plan.context||{}
  return <div className="trackGrid">{TRACKS.filter(t=>t.id!=='family'||plan.tracks?.family).map(t=>{
    const inTrack=strategies.filter(s=>s.track===t.id)
    const best=inTrack[0]
    const hidden=t.id==='sponsored'&&ctx.employer==='no'
    const on=inTrack.some(s=>s.id===activeId)
    return <button key={t.id} className={`trackCard ${on?'on':''} ${hidden||!best?'off':''}`} onClick={()=>best&&onPick(best.id)} disabled={!best}>
      <div className="trackTop"><span className="trackIcon"><t.icon size={17}/></span><b>{t.label}</b>{best&&<LevelBadge level={best.level}/>}</div>
      <p>{t.blurb}</p>
      {best?<><RouteChips route={best.route} compact/><div className="trackFacts"><span>Best: <b>{shortName(best)}</b></span><span>PR <b>{best.prWindow.from?fmtDate(best.prWindow.from):'not estimable'}</b></span></div></>:<em className="trackOff">{hidden?'Hidden: you answered No to employer sponsorship.':'No route available with your answers.'}</em>}
    </button>})}</div>
}
function Routes({plan,strategies,activeId,compared,setCompare,openPlan}){
  const toggle=id=>setCompare(compared.includes(id)?compared.filter(x=>x!==id):[...compared,id].slice(-4))
  const rows=strategies.filter(s=>compared.includes(s.id))
  const [showTree,setShowTree]=useState(false)
  return <>
    {TRACKS.map(t=>{const list=strategies.filter(s=>s.track===t.id);if(!list.length) return null;return <section key={t.id} className="trackSection">
      <div className="trackHead"><span className="trackIcon"><t.icon size={17}/></span><div><h3>{t.label}</h3><p>{t.blurb}</p></div></div>
      <div className="routeRows">{list.map(s=><article key={s.id} className={`routeRow ${s.id===activeId?'active':''}`}>
        <div className="rrMain"><div className="rrTitle"><b>{shortName(s)}</b><LevelBadge level={s.level}/>{s.id===activeId&&<span className="myPlan"><Check size={12}/>My plan</span>}</div><RouteChips route={s.route} compact/><p>{s.reasons[0]}</p></div>
        <dl className="rrFacts"><div><dt>PR window</dt><dd>{s.prWindow.label}</dd></div><div><dt>Gov. charges</dt><dd>{money(s.costs.government)}</dd></div></dl>
        <div className="rrActions"><button className="primary small" onClick={()=>openPlan(s.id)}>{s.id===activeId?'View plan':'Use this route'}<ArrowRight size={14}/></button><label className="cmp"><input type="checkbox" checked={compared.includes(s.id)} onChange={()=>toggle(s.id)}/>Compare</label></div>
      </article>)}</div>
    </section>})}
    {(plan.ruledOut||[]).length>0&&<section className="card ruledCard"><div className="cardHead"><div><span className="kicker">Not shown</span><h3>Routes ruled out for you</h3></div><CircleX/></div>{plan.ruledOut.map(r=><div key={r.id} className="ruledRow"><div><b>{r.name}</b>{r.route&&<RouteChips route={r.route} compact/>}</div><p>{r.reason}</p></div>)}</section>}
    {rows.length>=2&&<section className="card compareCard"><div className="cardHead"><div><span className="kicker">Side by side</span><h3>Compare {rows.length} routes</h3></div><Scale/></div>
      <div className="compareScroll"><table className="compareTable"><thead><tr><th/>{rows.map(s=><th key={s.id}><b>{s.name}</b><LevelBadge level={s.level}/></th>)}</tr></thead><tbody>
        <tr><th>Route</th>{rows.map(s=><td key={s.id}><RouteChips route={s.route} compact/></td>)}</tr>
        <tr><th>Earliest PR</th>{rows.map(s=><td key={s.id}><b>{s.prWindow.label}</b>{s.monthsToPr!=null&&<small>about {s.monthsToPr} months</small>}</td>)}</tr>
        <tr><th>Government charges</th>{rows.map(s=><td key={s.id}>{money(s.costs.government)}</td>)}</tr>
        <tr><th>Depends on</th>{rows.map(s=><td key={s.id}><ul>{s.dependencies.map(d=><li key={d}>{d}</li>)}</ul></td>)}</tr>
        <tr><th>Obligation</th>{rows.map(s=><td key={s.id}>{s.obligation||'None'}</td>)}</tr>
        <tr><th>Main risk</th>{rows.map(s=><td key={s.id}>{s.risks[0]?.title||'None flagged'}</td>)}</tr>
      </tbody></table></div></section>}
    <button className="moreBtn standalone" onClick={()=>setShowTree(!showTree)}>{showTree?<ChevronUp size={15}/>:<GitBranch size={15}/>}{showTree?'Hide the decision tree':'How your answers lead to these routes (decision tree)'}</button>
    {showTree&&<DecisionTree tree={plan.tree} strategies={strategies} openRoadmap={openPlan}/>}
  </>
}

/* ---------- plan and roadmap ---------- */
function Gantt({strategy,deadlines,today}){
  const items=[...strategy.lanes.flatMap(l=>[l.start,l.end]),...strategy.milestones.flatMap(m=>[m.start,m.end])].filter(Boolean).map(d=>new Date(d+'T00:00:00').getTime())
  const t0=new Date(today+'T00:00:00').getTime()
  const min=Math.min(t0,...items),max=Math.max(...items,t0+365*864e5)+120*864e5
  const W=1000,L=96,R=16
  const x=d=>L+(new Date(d+'T00:00:00').getTime()-min)/(max-min)*(W-L-R)
  const lanes=[...new Map(strategy.lanes.map(l=>[l.code+l.kind,l])).values()]
  const laneRows=[]
  lanes.forEach(l=>{let row=laneRows.findIndex(r=>r.every(o=>o.end<=l.start||o.start>=l.end));if(row<0){laneRows.push([]);row=laneRows.length-1}laneRows[row].push(l)})
  const ms=strategy.milestones
  const top=34,laneH=30,mTop=top+Math.max(1,laneRows.length)*laneH+18,mH=22
  const H=mTop+ms.length*mH+30
  const years=[];for(let y=new Date(min).getFullYear();y<=new Date(max).getFullYear()+1;y++){const d=`${y}-01-01`;const xx=x(d);if(xx>=L&&xx<=W-R)years.push([y,xx])}
  return <div className="ganttWrap"><svg viewBox={`0 0 ${W} ${H}`} className="gantt" role="img" aria-label={`Timeline for ${strategy.name}`}>
    {years.map(([y,xx])=><g key={y}><line x1={xx} x2={xx} y1={20} y2={H-10} className="gGrid"/><text x={xx+4} y={16} className="gYear">{y}</text></g>)}
    <text x={8} y={top+16} className="gLabel">Visa status</text>
    {laneRows.map((row,ri)=>row.map(l=><g key={l.code+l.start}><rect x={x(l.start)} y={top+ri*laneH} width={Math.max(4,x(l.end)-x(l.start))} height={laneH-8} rx={6} fill={visaColor(l.code)} className={`gBar ${l.kind}`}/>{x(l.end)-x(l.start)>46&&<text x={x(l.start)+8} y={top+ri*laneH+15} className="gBarText">{l.code==='BVA'?'Bridging':l.code}</text>}<title>{`${l.label}: ${fullDate(l.start)} to ${fullDate(l.end)}${l.note?` · ${l.note}`:''}`}</title></g>))}
    <text x={8} y={mTop-6} className="gLabel">Milestones</text>
    {ms.map((m,i)=>{const y=mTop+i*mH;const x1=x(m.start),x2=x(m.end);const pr=m.kind==='pr';return <g key={m.id} className={`gMs ${m.status} ${pr?'pr':''}`}><line x1={L} x2={W-R} y1={y+8} y2={y+8} className="gRowLine"/>{x2-x1>6?<rect x={x1} y={y+2} width={x2-x1} height={12} rx={6} className={`gMsBar ${m.uncertain?'unc':''}`}/>:<rect x={x1-6} y={y+2} width={12} height={12} rx={2} transform={`rotate(45 ${x1} ${y+8})`} className="gMsDot"/>}<text x={Math.min(x2+8,W-220)} y={y+12} className="gMsText">{m.title.length>44?m.title.slice(0,42)+'…':m.title}</text><title>{`${m.title}: ${fullDate(m.start)}${m.end!==m.start?` to ${fullDate(m.end)}`:''}`}</title></g>})}
    {deadlines.filter(d=>d.severity==='high').map(d=>{const xx=x(d.date);return xx>L&&xx<W-R?<g key={d.date+d.title}><line x1={xx} x2={xx} y1={top-6} y2={H-12} className="gDeadline"/><title>{`${d.title}: ${fullDate(d.date)}`}</title></g>:null})}
    <line x1={x(today)} x2={x(today)} y1={20} y2={H-8} className="gToday"/><text x={x(today)+4} y={H-12} className="gTodayText">Today</text>
  </svg><div className="ganttLegend"><span><i className="lg held"/>Visa held or projected</span><span><i className="lg processing"/>Processing (bridging visa)</span><span><i className="lg ms"/>Milestone window</span><span><i className="lg unc"/>Estimate depends on an invitation or decision</span><span><i className="lg dl"/>Hard deadline</span></div></div>
}
function MilestoneItem({m,open,onToggle,checks,toggleCheck,onJobsAction,last}){
  const Icon=KIND_ICON[m.kind]||Signpost
  const doneCount=m.tasks.filter(t=>checks[t.id]).length
  const complete=m.tasks.length>0&&doneCount===m.tasks.length
  return <article className={`msCard ${m.status} ${complete?'complete':''} ${m.kind==='pr'?'prMs':''} ${open?'open':''}`}>
    <div className="msRail"><span className="msIcon" style={m.visa?{'--c':visaColor(m.visa)}:undefined}>{complete?<Check size={16}/>:<Icon size={16}/>}</span>{!last&&<i/>}</div>
    <div className="msBody">
      <button className="msHead" onClick={onToggle} aria-expanded={open}>
        <div><span className="msDate">{fullDate(m.start)}{m.end!==m.start?` → ${fullDate(m.end)}`:''}</span><h4>{m.title}</h4></div>
        <div className="msTags">{m.status==='now'&&<span className="nowTag">Now</span>}{m.deadline&&<span className="dlTag"><Clock3 size={11}/>Due {fmtDate(m.deadline,{day:'numeric',month:'short'})}</span>}{m.uncertain&&<span className="estTag">Estimate</span>}{m.tasks.length>0&&<span className="taskCount">{doneCount}/{m.tasks.length}</span>}{open?<ChevronUp size={16}/>:<ChevronDown size={16}/>}</div>
      </button>
      {open&&<div className="msDetail"><p>{m.detail}</p>
        {m.tasks.length>0&&<ul className="taskList">{m.tasks.map(t=><li key={t.id} className={checks[t.id]?'checked':''}><label><input type="checkbox" checked={!!checks[t.id]} onChange={()=>toggleCheck(t.id)}/><span>{t.label}</span></label>{t.link&&<a href={t.link} target="_blank" rel="noreferrer" className="taskLink">Official page<ExternalLink size={11}/></a>}{t.action?.type==='jobs'&&<button className="taskAction" onClick={()=>onJobsAction(t.action)}><BriefcaseBusiness size={12}/>Find {t.action.location?.split(',')[0]} roles</button>}</li>)}</ul>}
        <div className="msFoot">{m.cost?.amount!=null&&<span className="msCost"><Wallet size={12}/>{m.cost.approx?'About ':''}{money(m.cost.amount)} · {m.cost.label}</span>}{m.sources.map(s=><a key={s.url} href={s.url} target="_blank" rel="noreferrer">{s.label}<ExternalLink size={11}/></a>)}</div>
      </div>}
    </div></article>
}
function PlanView({plan,strategy,strategies,setActiveId,checks,toggleCheck,onJobsAction,goRoutes}){
  const ms=strategy.milestones
  const allTasks=ms.flatMap(m=>m.tasks)
  const done=allTasks.filter(t=>checks[t.id]).length
  const pending=ms.filter(m=>m.status!=='done'&&!(m.tasks.length&&m.tasks.every(t=>checks[t.id])))
  const nextIds=pending.slice(0,3).map(m=>m.id)
  const [openIds,setOpenIds]=useState(()=>new Set(nextIds.slice(0,1)))
  const [showAll,setShowAll]=useState(false)
  const toggle=id=>setOpenIds(prev=>{const n=new Set(prev);n.has(id)?n.delete(id):n.add(id);return n})
  const events=[...ms.map(m=>({date:m.deadline||m.start,title:`${m.deadline?'Deadline: ':''}${m.title}`,detail:m.detail})),...(plan.deadlines||[]).map(d=>({date:d.date,title:d.title,detail:d.detail}))]
  const visible=showAll?ms:ms.filter(m=>nextIds.includes(m.id))
  const sameTrack=strategies.filter(s=>s.track===strategy.track&&s.id!==strategy.id)
  return <>
    <TrackCards plan={plan} strategies={strategies} activeId={strategy.id} onPick={setActiveId}/>
    <section className="card planHead">
      <div className="phTop"><div><span className="kicker">{TRACKS.find(t=>t.id===strategy.track)?.label} route</span><h3>{shortName(strategy)}</h3><RouteChips route={strategy.route}/></div><LevelBadge level={strategy.level}/></div>
      <p className="phWhy">{strategy.reasons[0]}</p>
      {sameTrack.length>0&&<div className="altRoutes"><span>Other {TRACKS.find(t=>t.id===strategy.track)?.label.toLowerCase()} routes:</span>{sameTrack.map(s=><button key={s.id} onClick={()=>setActiveId(s.id)}>{shortName(s)}</button>)}<button className="linkish" onClick={goRoutes}>Compare all</button></div>}
      <div className="roadMeta"><div><span>PR window</span><b>{strategy.prWindow.label}</b></div><div><span>Government charges</span><b>{money(strategy.costs.government)}</b><small>+ about {money(strategy.costs.otherLow)} to {money(strategy.costs.otherHigh)} other</small></div><div><span>Your progress</span><b>{done} of {allTasks.length} tasks</b><div className="prog"><i style={{width:`${allTasks.length?done/allTasks.length*100:0}%`}}/></div></div></div>
    </section>
    <div className="roadGrid">
      <section className="msList">
        <div className="msListHead"><h3>{showAll?`All ${ms.length} steps`:'Your next steps'}</h3><div className="roadActions"><button className="ghostSmall" onClick={()=>downloadIcs(events,`pathway-${strategy.id}.ics`)}><CalendarPlus size={15}/>Add to calendar</button><button className="ghostSmall" onClick={()=>window.print()}><Printer size={15}/>Print</button></div></div>
        {visible.map((m,i)=><MilestoneItem key={m.id} m={m} open={openIds.has(m.id)} onToggle={()=>toggle(m.id)} checks={checks} toggleCheck={toggleCheck} onJobsAction={onJobsAction} last={i===visible.length-1}/>)}
        <button className="moreBtn standalone" onClick={()=>setShowAll(!showAll)}>{showAll?<ChevronUp size={15}/>:<ChevronDown size={15}/>}{showAll?'Show only the next steps':`Show all ${ms.length} steps to permanent residence`}</button>
        {showAll&&<section className="card"><div className="cardHead"><div><span className="kicker">Timeline</span><h3>From today to permanent residence</h3></div></div><Gantt strategy={strategy} deadlines={plan.deadlines||[]} today={plan.today}/></section>}
      </section>
      <div className="roadSide">
        <section className="card"><span className="kicker">Watch out for</span>{strategy.risks.length?strategy.risks.slice(0,3).map((r,i)=><div key={i} className={`riskItem ${r.level}`}><TriangleAlert size={15}/><div><b>{r.title}</b><p>{r.detail}</p></div></div>):<p className="muted">No specific risks flagged for this route.</p>}</section>
        <section className="card"><span className="kicker">It depends on</span><ul className="sideList dep">{strategy.dependencies.map(d=><li key={d}>{d}</li>)}</ul></section>
        <details className="card costDetails"><summary><span className="kicker">Cost breakdown</span><b>{money(strategy.costs.government)} in government charges</b></summary><table className="costTable"><tbody>{strategy.costs.items.map((c,i)=><tr key={i}><td>{c.label}<small>{c.basis==='live'?`Live from Home Affairs · ${fullDate(c.checkedAt?.slice(0,10))}`:c.note}</small></td><td>{c.amountHigh?`${money(c.amount)}–${money(c.amountHigh)}`:money(c.amount)}</td></tr>)}</tbody></table><p className="fine">Primary applicant only. Employer-paid costs are not included.</p></details>
      </div>
    </div>
  </>
}

/* ---------- decision tree ---------- */
function layoutTree(root){
  const nodes=[],edges=[];let leaf=0
  const walk=(n,depth,path,lit)=>{
    const id=nodes.length;const node={...n,id,depth,lit};nodes.push(node)
    if(n.type==='question'){const xs=[];n.branches.forEach(b=>{const on=lit&&(n.answer==null||n.answer===b.value);const cid=walk(b.child,depth+1,[...path,b.value],on);edges.push({from:id,to:cid,label:b.label,on,chosen:lit&&n.answer===b.value,open:lit&&n.answer==null});xs.push(nodes[cid].x)});node.x=(Math.min(...xs)+Math.max(...xs))/2}
    else{node.x=leaf++}
    return id}
  walk(root,0,[],true)
  return {nodes,edges,leaves:leaf,depth:Math.max(...nodes.map(n=>n.depth))}
}
function DecisionTree({tree,strategies,openRoadmap}){
  const {nodes,edges,leaves,depth}=useMemo(()=>layoutTree(tree),[tree])
  const CW=178,RH=128,NW=164,W=leaves*CW+20,H=(depth+1)*RH+20
  const px=n=>10+n.x*CW+CW/2,py=n=>16+n.depth*RH
  const byId=Object.fromEntries(nodes.map(n=>[n.id,n]))
  return <>
    <div className="sectionIntro"><div><span className="kicker">Decision tree</span><h3>How your answers lead to each route</h3><p>Solid green branches follow your answers. Dashed branches are still open because a question is unanswered. Click a destination to open its roadmap.</p></div></div>
    <section className="card treeCard"><div className="treeScroll"><svg viewBox={`0 0 ${W} ${H}`} style={{minWidth:Math.max(760,W*0.68)}} className="tree">
      {edges.map((e,i)=>{const a=byId[e.from],b=byId[e.to];const x1=px(a),y1=py(a)+64,x2=px(b),y2=py(b);const my=(y1+y2)/2;return <g key={i} className={`tEdge ${e.chosen?'chosen':e.open?'open':e.on?'on':''}`}><path d={`M${x1},${y1} C${x1},${my} ${x2},${my} ${x2},${y2}`}/><rect x={(x1+x2)/2-17} y={my-10} width={34} height={18} rx={9}/><text x={(x1+x2)/2} y={my+3}>{e.label}</text></g>})}
      {nodes.map(n=>{const x=px(n)-NW/2,y=py(n);if(n.type==='question') return <foreignObject key={n.id} x={x} y={y} width={NW} height={64}><div className={`tQ ${n.lit?'lit':''}`}><span>{n.label}</span>{n.answer&&<em>You: {n.answer==='yes'?'Yes':'No'}</em>}</div></foreignObject>
        const s=strategies.find(st=>st.id===n.strategy);return <foreignObject key={n.id} x={x} y={y} width={NW} height={74}><button className={`tOut ${n.lit?'lit':''} ${LEVEL_CLASS[n.level]||''}`} onClick={()=>s&&openRoadmap(s.id)} disabled={!s}><b>{n.label}</b><span>{n.level}{s?.prWindow?.from?` · PR ${fmtDate(s.prWindow.from)}`:''}</span></button></foreignObject>})}
    </svg></div></section>
  </>
}

/* ---------- points lab ---------- */
function PointsLab({plan,c,set}){
  const base=plan.points
  const opts=(plan.pointsOptions||[]).filter(o=>o.available!==false)
  const rowPts=Object.fromEntries(base.rows.map(r=>[r.id,r.points]))
  const initial=()=>Object.fromEntries(opts.map(o=>[o.id,o.current]))
  const [sel,setSel]=useState(initial)
  const choiceOf=(o,v)=>o.choices.find(ch=>ch.value===v)
  let total=base.total;const changes=[]
  opts.forEach(o=>{const v=sel[o.id];if(v===undefined||v===o.current) return;const ch=choiceOf(o,v);if(!ch) return;const was=o.factor?(rowPts[o.factor]??0):0;const d=ch.points-was;total+=d;if(d) changes.push(`${o.label}: ${ch.label} (${d>0?'+':''}${d})`)})
  const s189=plan.strategies?.find(s=>s.id==='189')
  const target=s189?.points?.target,basis=s189?.points?.targetBasis
  const round=plan.round
  const colors=['#0c6b58','#2a9d8f','#6b7fd7','#e4723b','#b0648a','#d1495b','#8ab17d','#e9c46a','#577590','#9aa6a2']
  return <div className="pointsGrid">
    <section className="card"><div className="cardHead"><div><span className="kicker">From your answers</span><h3>{base.total} points today</h3></div><Calculator/></div>
      <div className="stackBar">{base.rows.filter(r=>r.points>0).map((r,i)=><i key={r.id} style={{flex:r.points,background:colors[i%colors.length]}} title={`${r.label}: ${r.points}`}/>)}<b style={{left:`${Math.min(100,65/Math.max(100,base.total)*100)}%`}}>65</b></div>
      <div className="ptRows">{base.rows.filter(r=>r.points>0||r.status==='unknown'||r.improve).map(r=><div key={r.id} className={`ptRow ${r.status}`}><div><b>{r.label}</b><span>{r.basis}</span>{r.improve&&<em>{r.improve}</em>}</div><strong>{r.status==='unknown'?'?':r.points}<small>/{r.max}</small></strong></div>)}</div>
      {base.unknown?.length>0&&<p className="evidenceCaution">Still unknown: {base.unknown.join(', ')}.</p>}
      <p className="reformNote"><TriangleAlert size={14}/>{plan.rulebook?.reformNote}</p>
    </section>
    <section className="card"><div className="cardHead"><div><span className="kicker">What if</span><h3>{total===base.total?<>{base.total} points</>:<>{base.total} → <span className={total>base.total?'good':'warn'}>{total}</span> points</>}</h3></div><SlidersHorizontal/></div>
      <p className="whatIfIntro">Starts from your saved answers. Change anything to see the effect; your answers stay as they are.</p>
      {opts.map(o=><div key={o.id} className="whatIf"><span>{o.label}</span><div className="seg">{o.choices.map(ch=>{const on=sel[o.id]===ch.value;return <button key={String(ch.value)} className={`${on?'on':''} ${o.current===ch.value?'saved':''}`} onClick={()=>setSel(p=>({...p,[o.id]:ch.value}))} title={ch.detail}>{ch.label}<small>{ch.points}</small></button>})}</div></div>)}
      <div className="whatIfFoot">{changes.length?<p>{changes.join(' · ')}</p>:<p className="muted">No changes yet.</p>}<button className="ghostSmall" onClick={()=>setSel(initial())}>Reset</button></div>
      <div className="targetBox"><div><span className="kicker">189 target</span><b>{target?`${target} (${basis==='user'?'your target':'latest published minimum'})`:'No published minimum for your occupation'}</b><small>{round?.date?`Latest round ${round.date}`:'Round data unavailable right now'}</small></div><label>Set my own target<input type="number" min={65} max={140} step={5} value={c.targetPoints||''} placeholder="e.g. 90" onChange={e=>set(p=>({...p,targetPoints:e.target.value===''?null:Number(e.target.value)}))}/></label></div>
    </section>
    <section className="card wideCard"><div className="cardHead"><div><span className="kicker">Points over time</span><h3>How age and experience move your score</h3></div><Hourglass/></div>
      <div className="chart tall"><ResponsiveContainer width="100%" height="100%"><AreaChart data={plan.pointsTimeline||[]} margin={{top:10,right:20,bottom:0,left:-10}}><defs><linearGradient id="pg" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#0c6b58" stopOpacity={0.35}/><stop offset="100%" stopColor="#0c6b58" stopOpacity={0.02}/></linearGradient></defs><CartesianGrid vertical={false} stroke="rgba(20,30,35,.08)"/><XAxis dataKey="label" tickLine={false} axisLine={false} fontSize={11} interval={3}/><YAxis domain={[40,'dataMax+10']} tickLine={false} axisLine={false} fontSize={11}/><Tooltip formatter={(v,n)=>[v,n==='points'?'189 (no nomination)':n==='with190'?'With 190 nomination':'With 491 nomination']}/><Area isAnimationActive={false} type="stepAfter" dataKey="with491" stroke="#b0648a" fill="none" strokeDasharray="4 4"/><Area isAnimationActive={false} type="stepAfter" dataKey="with190" stroke="#2a9d8f" fill="none" strokeDasharray="4 4"/><Area isAnimationActive={false} type="stepAfter" dataKey="points" stroke="#0c6b58" strokeWidth={2.5} fill="url(#pg)"/><ReferenceLine y={65} stroke="#e4723b" strokeDasharray="3 3" label={{value:'Pass mark 65',position:'insideTopLeft',fontSize:11,fill:'#b45a2c'}}/>{target&&<ReferenceLine y={target} stroke="#132522" strokeDasharray="6 3" label={{value:`Target ${target}`,position:'insideTopRight',fontSize:11}}/>}</AreaChart></ResponsiveContainer></div>
      <p className="fine">Assumes skilled work from {fullDate(plan.context?.workStart)} with no other changes. Dashed lines add 190 (+5) or 491 (+15) nomination points.</p>
    </section>
  </div>
}

/* ---------- visa checks ---------- */
const CHECK_ICON={met:CircleCheck,unmet:CircleX,unknown:CircleHelp,later:Hourglass}
function VisaChecks({visas}){
  const [openCode,setOpen]=useState(visas[0]?.code)
  return <>
    <div className="sectionIntro"><div><span className="kicker">Criteria, checked against your answers</span><h3>Visa checks</h3><p><span className="ck met"><CircleCheck size={13}/>met</span> <span className="ck later"><Hourglass size={13}/>a later step</span> <span className="ck unknown"><CircleHelp size={13}/>needs an answer</span> <span className="ck unmet"><CircleX size={13}/>not met today</span></p></div></div>
    <div className="visaGrid">{visas.map(v=><article key={v.code} className={`visaCard ${openCode===v.code?'open':''}`}>
      <button className="visaHead" onClick={()=>setOpen(openCode===v.code?null:v.code)}><span className="visaCode" style={{'--c':visaColor(v.code)}}>{v.code}</span><div><b>{v.name}</b><span>{v.kind} · {money(v.fee)}{v.feeBasis==='live'?' · live':''}</span></div><div className="ckCounts">{['met','later','unknown','unmet'].map(k=>v.counts[k]>0&&<span key={k} className={`ck ${k}`}>{v.counts[k]}</span>)}</div>{openCode===v.code?<ChevronUp size={16}/>:<ChevronDown size={16}/>}</button>
      {openCode===v.code&&<div className="visaBody">
        <ul className="checkList">{v.checks.map(ch=>{const I=CHECK_ICON[ch.state]||CircleHelp;return <li key={ch.id} className={ch.state}><I size={16}/><div><b>{ch.label}</b>{ch.detail&&<span>{ch.detail}</span>}{ch.fix&&ch.state!=='met'&&<em>{ch.fix}</em>}</div></li>})}</ul>
        <dl className="visaFacts"><div><dt>Stay</dt><dd>{v.stay}</dd></div><div><dt>Rights</dt><dd>{v.rights}</dd></div><div><dt>Processing</dt><dd>{v.processing}</dd></div><div><dt>Charge</dt><dd>{money(v.fee)} {v.feeBasis==='live'?`(live, ${fullDate(v.feeCheckedAt?.slice(0,10))})`:`(rulebook${v.feeNote?`: ${v.feeNote}`:', from 1 July 2026'})`}</dd></div></dl>
        <div className="condList">{v.keyConditions.map(k=><span key={k}>{k}</span>)}</div>
        {v.notes.map((n,i)=><p key={i} className="evidenceCaution">{n}</p>)}
        {v.url&&<a className="evidenceLink" href={v.url} target="_blank" rel="noreferrer">Official subclass {v.code} page<ExternalLink size={12}/></a>}
      </div>}
    </article>)}</div>
  </>
}

/* ---------- deadlines ---------- */
function Deadlines({plan,active}){
  const items=plan.deadlines||[]
  const msItems=(active?.milestones||[]).filter(m=>m.deadline).map(m=>({date:m.deadline,title:m.title,detail:m.detail,severity:'high',kind:'deadline'}))
  const all=[...items,...msItems.filter(m=>!items.some(i=>i.date===m.date))].sort((a,b)=>a.date.localeCompare(b.date))
  const byYear=all.reduce((acc,d)=>{const y=d.date.slice(0,4);(acc[y]=acc[y]||[]).push(d);return acc},{})
  return <>
    <div className="sectionIntro"><div><span className="kicker">Deadline register</span><h3>Dates that change your options</h3><p>Visa expiry, application windows, age thresholds and document validity. Add them to your calendar with a reminder 14 days before each.</p></div><button className="primary small" onClick={()=>downloadIcs(all)}><Download size={15}/>Download .ics</button></div>
    <section className="card deadlineCard">{Object.entries(byYear).map(([y,list])=><div key={y} className="dlYear"><h4>{y}</h4>{list.map((d,i)=><div key={i} className={`dlItem ${d.severity}`}><div className="dlDate"><b>{fmtDate(d.date,{day:'numeric'})}</b><span>{fmtDate(d.date,{month:'short'})}</span></div><div><b>{d.title}</b><p>{d.detail}</p></div><span className="dlAway">{d.daysAway!=null?(d.daysAway<=0?'Today':d.daysAway<60?`${d.daysAway} days`:d.daysAway<730?`${Math.round(d.daysAway/30.4)} months`:`${(d.daysAway/365).toFixed(1)} years`):''}</span></div>)}</div>)}{!all.length&&<p className="muted">No dated deadlines yet. Add your visa expiry, date of birth and course completion date.</p>}</section>
  </>
}

/* ---------- states & evidence ---------- */
function Evidence({plan,jobs,onJobsAction,profile}){
  const wr=jobs?.market?.all?.workRights
  const plan2=plan.rulebook?.planning||{}
  const planningData=[['Employer','employer'],['189','189'],['190','190'],['491','491'],['Talent','talent'],['Partner','partner']].map(([l,k])=>({name:l,'2025-26':plan2.previous?.[k],'2026-27':plan2[k]}))
  const wrLabels={citizen_pr:'Citizens or PR only',clearance:'Security clearance',no_sponsorship:'No sponsorship',sponsorship:'Sponsorship mentioned',work_rights:'Work rights required',not_stated:'Not stated'}
  return <div className="evidenceGrid">
    <section className="card wideCard"><div className="cardHead"><div><span className="kicker">State and territory nomination</span><h3>Where 190 and 491 programs stand</h3></div><MapPin/></div>
      <div className="stateGrid">{(plan.states||[]).map(s=><article key={s.code} className={`stateCard ${(plan.context?.states||[]).includes(s.code)?'pref':''}`}><div className="stateTop"><b>{s.code}</b><span>{s.name}</span>{(plan.context?.states||[]).includes(s.code)&&<em>Targeted</em>}</div><p className="stateStatus">{s.status}</p><small>{s.statusBasis==='live'?`Live excerpt · ${fullDate(s.statusCheckedAt?.slice(0,10))}`:`Rulebook · verified ${fullDate(plan.rulebook?.stateStatusVerified)}`}</small>{s.shortage&&<p className="stateShort">JSA rating for {profile.occupation}: <b>{s.shortage}</b></p>}<details><summary>Streams and regional areas</summary><ul>{s.streams.map(x=><li key={x}>{x}</li>)}</ul><p>{s.regional}</p></details><a className="evidenceLink" href={s.url} target="_blank" rel="noreferrer">Official program<ExternalLink size={12}/></a></article>)}</div>
    </section>
    <section className="card"><div className="cardHead"><div><span className="kicker">From your Jobs collection</span><h3>Work rights employers ask for</h3></div><BriefcaseBusiness/></div>
      {wr?<><div className="wrBars">{Object.entries(wr.counts).filter(([,v])=>v>0).map(([k,v])=><div key={k} className={`wr ${k}`}><span>{wrLabels[k]}</span><div><i style={{width:`${v/jobs.count*100}%`}}/></div><b>{v}/{jobs.count}</b></div>)}</div>
        {wr.examples.slice(0,3).map((e,i)=><a key={i} className="jobEvidenceLink" href={e.url} target="_blank" rel="noreferrer"><span>{e.evidence}</span><small>{e.label} · {e.title}<ExternalLink size={12}/></small></a>)}
        <p className="fine">Quoted advert text from one sample of {jobs.count} adverts for {jobs.query?.role}. Silence about sponsorship does not mean an employer will not sponsor.</p></>
        :<div className="dataEmpty"><BriefcaseBusiness/><b>No adverts collected yet</b><p>Run a Jobs search to see how many employers restrict roles to citizens or PR, need clearances or mention sponsorship.</p></div>}
      <button className="ghostSmall" onClick={()=>onJobsAction({type:'jobs',role:profile.occupation,location:profile.location})}><BriefcaseBusiness size={14}/>Open Jobs for {profile.occupation}</button>
    </section>
    <section className="card"><div className="cardHead"><div><span className="kicker">Migration program planning levels</span><h3>Where the places are in 2026-27</h3></div><Layers/></div>
      <div className="chart"><ResponsiveContainer width="100%" height="100%"><BarChart data={planningData} margin={{top:6,right:6,bottom:0,left:-14}}><CartesianGrid vertical={false} stroke="rgba(20,30,35,.08)"/><XAxis dataKey="name" tickLine={false} axisLine={false} fontSize={11}/><YAxis tickLine={false} axisLine={false} fontSize={11} tickFormatter={v=>`${v/1000}k`}/><Tooltip formatter={v=>v?.toLocaleString?.()}/><Legend iconType="circle" wrapperStyle={{fontSize:11}}/><Bar dataKey="2025-26" fill="#c9d6d0" radius={[4,4,0,0]}/><Bar dataKey="2026-27" fill="#0c6b58" radius={[4,4,0,0]}/></BarChart></ResponsiveContainer></div>
      <p className="fine">Employer sponsored places rose to {plan2.employer?.toLocaleString()} while 491 fell to {plan2['491']?.toLocaleString()}. Planning levels are ceilings for the year, not your chance of an invitation.</p>
    </section>
    <section className="card"><div className="cardHead"><div><span className="kicker">Income thresholds from 1 July 2026</span><h3>Employer route salary floors</h3></div><Wallet/></div>
      <dl className="evidenceFacts"><div><dt>Core Skills (CSIT) · 482 Core, 186</dt><dd>{money(plan.rulebook?.thresholds?.CSIT)}</dd></div><div><dt>Specialist Skills (SSIT) · 482</dt><dd>{money(plan.rulebook?.thresholds?.SSIT)}</dd></div><div><dt>TSMIT · 494</dt><dd>{money(plan.rulebook?.thresholds?.TSMIT)}</dd></div></dl>
      <p className="fine">Salary must also meet the annual market salary rate for the role and location.</p>
    </section>
    <section className="card"><div className="cardHead"><div><span className="kicker">Provenance</span><h3>Sources behind this plan</h3></div><FileText/></div>
      <ul className="srcList">{(plan.liveSources||[]).map(s=><li key={s.id}><i className={s.status==='fresh'?'ok':s.status==='fallback'?'fb':'bad'}/><div><b>{s.label}</b><span>{s.detail}{s.checkedAt?` · checked ${new Date(s.checkedAt).toLocaleString('en-AU',{day:'numeric',month:'short',hour:'2-digit',minute:'2-digit'})}`:''}</span></div></li>)}</ul>
      <details className="ratingDetails"><summary>Rulebook sources ({plan.rulebook?.sources?.length})</summary><ul className="srcLinks">{(plan.rulebook?.sources||[]).map(s=><li key={s.url}><a href={s.url} target="_blank" rel="noreferrer">{s.label}<ExternalLink size={11}/></a></li>)}</ul></details>
    </section>
  </div>
}

/* ---------- compact card for Overview ---------- */
export function MigrationSummaryCard({plan,activeId,onOpen,loading}){
  const s=plan?.strategies?.find(x=>x.id===activeId)||plan?.strategies?.[0]
  const next=s?.milestones?.find(m=>m.status!=='done')
  const ctx=plan?.context||{}
  return <section className="card migSummary"><div className="cardHead"><div><span className="kicker">Permanent residence roadmap</span><h2>{ctx.settled?'No migration pathway needed':s?.name||(loading?'Building your roadmap':'Roadmap unavailable')}</h2></div><Route/></div>
    {s&&<><RouteChips route={s.route}/><div className="migSumFacts"><div><span>Status</span><LevelBadge level={s.level}/></div><div><span>PR window</span><b>{s.prWindow.label}</b></div><div><span>Visa days left</span><b>{ctx.daysOnVisa!=null?Math.max(0,ctx.daysOnVisa):'Add expiry'}</b></div><div><span>Points today</span><b>{plan.points?.total}</b></div></div>
      {next&&<div className="migNext"><Signpost size={16}/><div><b>Next: {next.title}</b><span>{fullDate(next.start)}{next.deadline?` · deadline ${fullDate(next.deadline)}`:''}</span></div></div>}</>}
    <button className="textBtn" onClick={onOpen}>Open migration roadmap<ArrowRight size={14}/></button>
  </section>
}

export function MigrationMilestones({plan,activeId,checks}){
  const s=plan?.strategies?.find(x=>x.id===activeId)||plan?.strategies?.[0]
  if(!s) return null
  return <section className="card"><div className="cardHead"><div><span className="kicker">Migration milestones · {s.name}</span><h2>Your visa steps alongside your career</h2></div><RouteChips route={s.route} compact/></div>
    <div className="timeline msTimeline">{s.milestones.map(m=>{const done=m.tasks.length>0&&m.tasks.every(t=>checks[t.id]);return <div key={m.id} className={m.status==='now'?'now':done?'complete':''}><span>{done?'DONE':m.status==='now'?'NOW':fmtDate(m.start,{month:'short'}).toUpperCase()}</span><div><b>{m.title}</b><p>{m.detail}</p></div><small>{fmtDate(m.start)}</small></div>})}</div></section>
}
