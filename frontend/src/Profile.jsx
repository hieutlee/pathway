import React, {useEffect, useState} from 'react'
import {X, ChevronDown, ChevronUp, FileText, Lock, Languages, BriefcaseBusiness, Heart, Info, Pencil, RotateCcw, Database} from 'lucide-react'
import './profile.css'

const fmtYears=y=>{const m=Math.round((Number(y)||0)*12);if(!m) return 'None yet';const a=Math.floor(m/12),b=m%12;return [a?`${a} yr${a>1?'s':''}`:'',b?`${b} mo${b>1?'s':''}`:''].filter(Boolean).join(' ')}
const PARTNER_OPTS=[['','Select'],['single','Single'],['partner_citizen_pr','Partner is an Australian citizen or PR'],['partner_skilled','Partner: skilled (assessment + competent English)'],['partner_competent_english','Partner: competent English only'],['partner_other','Partner: none of the above']]
const ENG_OPTS=[['','Not tested'],['competent','Competent (IELTS 6 each)'],['proficient','Proficient (IELTS 7 each)'],['superior','Superior (IELTS 8 each)'],['vocational','Below competent']]
const SA_OPTS=[['','Select'],['none','Not started'],['submitted','Submitted'],['positive','Positive outcome']]
const YNM=[['','Select'],['yes','Yes'],['maybe','Maybe'],['no','No']]
const STATES=['QLD','NSW','VIC','SA','WA','TAS','ACT','NT']

function F({label,children,hint,missing}){return <label className={`pfField ${missing?'missing':''}`}><span>{label}{missing&&<em>Needed</em>}</span>{children}{hint&&<small>{hint}</small>}</label>}
function Sel({value,onChange,opts}){return <select value={value??''} onChange={e=>onChange(e.target.value)}>{opts.map(([v,l])=><option key={v} value={v}>{l}</option>)}</select>}
function Num({value,onChange,step=1}){return <input type="number" min={0} step={step} value={value??''} onChange={e=>onChange(e.target.value===''?'':Number(e.target.value))}/>}
function Toggle({value,onChange,label}){return <button type="button" className={`pfToggle ${value?'on':''}`} aria-pressed={!!value} onClick={()=>onChange(!value)}><i/>{label}</button>}

/* A right-side sheet. Escape and the backdrop close it. */
export function Sheet({open,onClose,title,children,wide}){
  useEffect(()=>{if(!open) return;const k=e=>e.key==='Escape'&&onClose();window.addEventListener('keydown',k);return ()=>window.removeEventListener('keydown',k)},[open,onClose])
  if(!open) return null
  return <div className="sheetBackdrop" onMouseDown={e=>e.target===e.currentTarget&&onClose()}><aside className={`sheet ${wide?'wide':''}`} role="dialog" aria-modal="true" aria-label={title}><button className="sheetClose" onClick={onClose} aria-label="Close"><X size={18}/></button>{children}</aside></div>
}

export function ProfileSheet({open,onClose,profile,setProfile,c,set,plan,onEditResume,onStartOver}){
  const [more,setMore]=useState(false)
  const miss=new Set((plan?.missing||[]).map(m=>m.field))
  const s=(k,v)=>set(prev=>({...prev,[k]:v}))
  const ctx=plan?.context||{}
  const employer=['yes','offer','sponsoring','interested'].includes(c.employer)?'yes':['no','none'].includes(c.employer)?'no':''
  const r=profile.resume
  const post=(Number(c.auExperienceYears)||0)+(Number(c.overseasExperienceYears)||0)
  return <Sheet open={open} onClose={onClose} title="Profile">
    <div className="pfHead"><div className="pfAvatar">{(profile.name||'P').charAt(0)}</div><div><h2>{profile.name||'Your profile'}</h2><p>{[profile.occupationTitle||profile.occupation,profile.location].filter(Boolean).join(' · ')}</p></div></div>

    <section className="pfCard">
      <div className="pfCardHead"><h3><FileText size={16}/>From your resume</h3><button className="pfLink" onClick={onEditResume}><Pencil size={13}/>Review details</button></div>
      <dl className="pfFacts">
        <div><dt>Occupation</dt><dd>{profile.occupationTitle||profile.occupation||'Not set'}</dd></div>
        {ctx.assessor?.name&&<div><dt>Assessed by</dt><dd>{ctx.assessor.name}</dd></div>}
        <div><dt>Relevant experience</dt><dd>{fmtYears(profile.experienceYears)}</dd></div>
        <div><dt>After graduating</dt><dd>{fmtYears(post)}</dd></div>
        <div><dt>Qualification</dt><dd>{profile.education||'Not set'}</dd></div>
        {r&&<div><dt>Projects</dt><dd>{r.projects?.length||0}</dd></div>}
        <div><dt>Visa</dt><dd>{profile.visa||'Not set'}</dd></div>
      </dl>
    </section>

    <section className="pfCard">
      <div className="pfCardHead"><h3><Lock size={16}/>Answers for your visa plan</h3>{(plan?.missing||[]).length>0&&<span className="pfBadge">{plan.missing.length} needed</span>}</div>
      <p className="pfIntro">Things a resume cannot show. Each answer updates your plan straight away and is saved on this device.</p>
      <div className="pfGroup"><h4>You</h4>
        <div className="pfTwo"><F label="Visa expiry" missing={miss.has('visaExpiry')}><input type="date" value={profile.visaExpiry||''} onChange={e=>setProfile(p=>({...p,visaExpiry:e.target.value}))}/></F><F label="Date of birth" missing={miss.has('dob')}><input type="date" value={c.dob||''} onChange={e=>s('dob',e.target.value)}/></F></div>
        <F label="Relationship" missing={miss.has('partner')}><Sel value={c.partner} onChange={v=>s('partner',v)} opts={PARTNER_OPTS}/></F>
        {c.partner==='partner_citizen_pr'&&<div className="pfTwo"><F label="Relationship type"><Sel value={c.partnerRelationship} onChange={v=>s('partnerRelationship',v)} opts={[['','Select'],['married','Married'],['registered','Registered'],['de_facto','De facto']]}/></F><F label="Months together"><Num value={c.relationshipMonths} onChange={v=>s('relationshipMonths',v)}/></F></div>}
      </div>
      <div className="pfGroup"><h4><Languages size={14}/>English and assessment</h4>
        <div className="pfTwo"><F label="English level" missing={miss.has('englishLevel')} hint="Your lowest band counts"><Sel value={c.englishLevel} onChange={v=>s('englishLevel',v)} opts={ENG_OPTS}/></F><F label="Skills assessment" missing={miss.has('skillsAssessment')} hint={ctx.assessor?.name}><Sel value={c.skillsAssessment==='planned'?'none':c.skillsAssessment} onChange={v=>s('skillsAssessment',v)} opts={SA_OPTS}/></F></div>
        <div className="pfToggles"><Toggle value={c.naati} onChange={v=>s('naati',v)} label="NAATI CCL passed"/>{ctx.pyEligible&&<Toggle value={c.professionalYear} onChange={v=>s('professionalYear',v)} label="Professional Year done"/>}</div>
      </div>
      <div className="pfGroup"><h4><BriefcaseBusiness size={14}/>Work and preferences</h4>
        <div className="pfTwo"><F label="An employer will sponsor you?" missing={miss.has('employer')}><Sel value={employer} onChange={v=>s('employer',v)} opts={[['','Select'],['yes','Yes'],['no','No']]}/></F><F label="Live regionally for 3+ years?" missing={miss.has('regional')}><Sel value={c.regional} onChange={v=>s('regional',v)} opts={YNM}/></F></div>
        <F label="States to target" hint="Up to two"><div className="pfStates">{STATES.map(st=>{const on=(c.preferredStates||[]).includes(st);return <button type="button" key={st} className={on?'on':''} onClick={()=>s('preferredStates',on?(c.preferredStates||[]).filter(x=>x!==st):[...(c.preferredStates||[]),st].slice(-2))}>{st}</button>})}</div></F>
      </div>
      <button className="pfMore" onClick={()=>setMore(!more)} aria-expanded={more}>{more?<ChevronUp size={15}/>:<ChevronDown size={15}/>}{more?'Hide optional details':'Optional details: test dates, passport, salary'}</button>
      {more&&<div className="pfGroup">
        <div className="pfTwo"><F label="English test date"><input type="date" value={c.englishTestDate||''} onChange={e=>s('englishTestDate',e.target.value)}/></F>{['submitted','positive'].includes(c.skillsAssessment)?<F label="Assessment date"><input type="date" value={c.skillsAssessmentDate||''} onChange={e=>s('skillsAssessmentDate',e.target.value)}/></F>:<span/>}</div>
        <F label="Passport country" hint="UK, US, Canada, NZ and Ireland passports are exempt from English tests"><input value={c.passport||''} onChange={e=>s('passport',e.target.value)}/></F>
        <div className="pfTwo"><F label="Months worked in target state" hint="20+ hours a week, after graduating"><Num value={c.stateEmploymentMonths} onChange={v=>s('stateEmploymentMonths',v)}/></F><F label="Months worked regionally"><Num value={c.regionalEmploymentMonths} onChange={v=>s('regionalEmploymentMonths',v)}/></F></div>
        {employer==='yes'&&<F label="Salary (AUD a year)"><Num value={c.salary} step={1000} onChange={v=>s('salary',v)}/></F>}
        {profile.visa?.includes('482')&&<F label="Months with your sponsor"><Num value={c.sponsorMonths} onChange={v=>s('sponsorMonths',v)}/></F>}
        <div className="pfToggles"><Toggle value={c.studyRegional==='yes'} onChange={v=>s('studyRegional',v?'yes':'no')} label="Studied at a regional campus"/><Toggle value={c.specialistEducation} onChange={v=>s('specialistEducation',v)} label="STEM research degree"/></div>
      </div>}
    </section>
    {(plan?.assumptions||[]).length>0&&<div className="pfNote"><Info size={14}/><div>{plan.assumptions.map((a,i)=><p key={i}>{a}</p>)}</div></div>}
    <button className="pfStartOver" onClick={onStartOver}><RotateCcw size={14}/>Start over with a different resume</button>
  </Sheet>
}

export function SourcesSheet({open,onClose,sources,renderInsight,renderBadge,onRefresh,busy}){
  return <Sheet open={open} onClose={onClose} title="Data sources">
    <div className="pfHead"><div className="pfAvatar src"><Database size={20}/></div><div><h2>Data sources</h2><p>Each source loads on its own. Failures stay visible instead of being filled with old or made-up numbers.</p></div></div>
    <div className="srcCards">{sources.map(s=><section key={s.id} className="pfCard"><div className="pfCardHead"><h3>{s.label}</h3>{renderBadge(s)}</div><p className="pfIntro">{s.detail}</p>{renderInsight(s)}</section>)}</div>
    <button className="primary pfRefresh" onClick={onRefresh} disabled={busy}>Refresh all sources</button>
  </Sheet>
}
