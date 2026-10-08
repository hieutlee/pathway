import React from 'react'
import {BriefcaseBusiness, ExternalLink, AlertTriangle, ChevronRight, Clock3} from 'lucide-react'

export function dateLabel(value, withTime=false){
  if(!value) return 'Not recorded'
  const date=new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('en-AU', {day:'numeric',month:'short',year:'numeric',...(withTime?{hour:'2-digit',minute:'2-digit'}:{})})
}

export function SourceLink({source,children}){
  if(!source?.sourceUrl) return null
  return <a className="evidenceLink" href={source.sourceUrl} target="_blank" rel="noreferrer">{children||source.source||'Official source'}<ExternalLink size={12}/></a>
}

export function SourceFooter({source}){
  if(!source) return <p className="evidenceFoot">Waiting for source data</p>
  return <div className="evidenceFoot"><SourceLink source={source}/>{source.checkedAt&&<span>Retrieved {dateLabel(source.checkedAt,true)}{source.cached?' · cached response':''}</span>}</div>
}

export function JobResults({jobs,limit=4}){
  const roles=jobs?.roles||[]
  if(!roles.length){
    const title=!jobs?'Loading vacancies':jobs.status==='loading'?'Collecting adverts':jobs.status==='not_configured'?'Connect a job source':jobs.count===0?'No matches in this collection':'Vacancy results unavailable'
    return <div className="dataEmpty"><BriefcaseBusiness size={26}/><b>{title}</b><p>{jobs?.note||'Waiting for the job provider to respond.'}</p></div>
  }
  return <><div className="listingGrid">{roles.slice(0,limit).map((job,index)=><article className="realListing" key={job.url||index}>
    <div className="listingHeading"><div className="jobLogo">{job.company?.charAt(0)||'J'}</div><div><a href={job.url} target="_blank" rel="noreferrer">{job.title}<ExternalLink size={13}/></a><span>{job.company||'Employer not listed'} · {job.location}</span></div></div>
    <p className="listingReason">{job.reason}</p>
    {job.salary&&<span className="listingSalary">{job.salary}</span>}
    <small>{job.postedAt?`Advert date: ${dateLabel(job.postedAt)}`:'Advert date not supplied'}</small>
  </article>)}</div><p className="collectionNote">{jobs.note}</p></>
}

const fmt=(v,o={day:'numeric',month:'short',year:'numeric'})=>{if(!v) return '';const d=new Date(v.length===10?v+'T00:00:00':v);return Number.isNaN(d.getTime())?v:d.toLocaleDateString('en-AU',o)}

const listJoin=a=>a.length<2?a.join(''):`${a.slice(0,-1).join(', ')} and ${a[a.length-1]}`

function Tile({label,value,detail,onClick,tone}){return <button className={`homeTile ${tone||''}`} onClick={onClick}><span>{label}</span><strong>{value}</strong><small>{detail}</small><em>Open<ChevronRight size={13}/></em></button>}

export default function Home({data,profile,plan,planLoading,activeId,checks,toggleCheck,setActiveTab,onJobsAction,openProfile}){
  const strategy=plan?.strategies?.find(s=>s.id===activeId)||plan?.strategies?.[0]
  const pending=(strategy?.milestones||[]).filter(m=>m.status!=='done'&&!(m.tasks.length&&m.tasks.every(t=>checks[t.id])))
  const next=pending[0]
  const nextTask=next?.tasks.find(t=>!checks[t.id])
  const ctx=plan?.context||{}
  const expiry=ctx.visaExpiry||profile.visaExpiry||''
  const days=ctx.daysOnVisa!=null?ctx.daysOnVisa:expiry?Math.round((new Date(expiry+'T00:00:00')-new Date(new Date().toDateString()))/864e5):null
  const target=plan?.strategies?.find(s=>s.id==='189')?.points?.target
  const pts=plan?.points?.total
  const jobs=data?.jobs
  const jobsValue=typeof jobs?.count==='number'?String(jobs.count):jobs?.status==='loading'?'Collecting':'Not collected'
  const missing=plan?.missing||[]
  return <div className="homeView">
    {missing.length>0&&<button className="homeMissing" onClick={openProfile}><AlertTriangle size={16}/><span><b>{missing.length} answer{missing.length>1?'s':''} would sharpen your plan:</b> {missing.slice(0,3).map(m=>m.label.toLowerCase()).join(', ')}</span><em>Answer now<ChevronRight size={14}/></em></button>}

    <section className="homeNext">
      <span className="kicker">Your next step</span>
      {next?<>
        <h2>{next.title}</h2>
        <p className="homeWhen"><Clock3 size={14}/>{next.deadline?`Due ${fmt(next.deadline)}`:next.end!==next.start?`${fmt(next.start)} to ${fmt(next.end)}`:fmt(next.start)}{strategy&&<> · part of <b>{strategy.name}</b></>}</p>
        {nextTask&&<label className="homeTask"><input type="checkbox" checked={false} onChange={()=>toggleCheck(nextTask.id)}/><span>{nextTask.label}</span></label>}
        <div className="homeActions">{nextTask?.action?.type==='jobs'?<button className="primary" onClick={()=>onJobsAction(nextTask.action)}>Find roles<ChevronRight size={16}/></button>:nextTask?.link?<a className="primary" href={nextTask.link} target="_blank" rel="noreferrer">Open official page<ExternalLink size={14}/></a>:null}<button className="homeGhost" onClick={()=>setActiveTab('Visa')}>See your full plan</button></div>
      </>:<><h2>{planLoading?'Building your plan':ctx.settled?'You already hold permanent residence':'Your plan will appear here'}</h2><p className="homeWhen">{ctx.settled?'Focus on the roles in Jobs.':'Open Visa to choose a route.'}</p></>}
    </section>

    <div className="homeTiles">
      <Tile label="Visa days left" value={days!=null?Math.max(0,days):'Add expiry'} detail={expiry?`${(profile.visa||'Current visa').replace(/ visa \(subclass (\d+)\)/,' ($1)')} · ${fmt(expiry)}`:'Needed for visa-gap warnings'} tone={days!=null&&days<120?'warn':''} onClick={()=>expiry?setActiveTab('Visa'):openProfile()}/>
      <Tile label={plan?.points?.unknown?.length?'Points so far':'Points today'} value={pts??'–'} detail={plan?.points?.unknown?.length?`Incomplete: add ${listJoin(plan.points.unknown.map(u=>u==='English'?u:u.toLowerCase().replace('english','English')))}`:target?`Target ${target}`:'Pass mark 65 · no published minimum'} tone={pts!=null&&pts<(target||65)&&!plan?.points?.unknown?.length?'warn':''} onClick={()=>plan?.points?.unknown?.length?openProfile():setActiveTab('Visa')}/>
      <Tile label="Matching jobs" value={jobsValue} detail={jobs?.query?`${jobs.query.role} · ${(jobs.query.location||'').split(',')[0]}`:`${profile.occupationTitle||profile.occupation} roles`} onClick={()=>setActiveTab('Jobs')}/>
    </div>

    <div className="homeGrid">
      <section className="card homeSteps"><div className="cardHead"><div><span className="kicker">Coming up</span><h2>Next steps</h2></div><button className="textBtn" onClick={()=>setActiveTab('Visa')}>All steps<ChevronRight size={14}/></button></div>
        {pending.slice(0,3).map((m,i)=>{const done=m.tasks.filter(t=>checks[t.id]).length;return <div key={m.id} className={`homeStep ${i===0?'first':''}`}><span className="homeDate"><b>{fmt(m.deadline||m.start,{day:'numeric'})}</b>{fmt(m.deadline||m.start,{month:'short'})} {String(new Date((m.deadline||m.start)+'T00:00:00').getFullYear()).slice(2)}</span><div><b>{m.title}</b><small>{m.tasks.length?`${done} of ${m.tasks.length} tasks`:m.uncertain?'Estimated date':''}{m.deadline?' · deadline':''}</small></div></div>})}
        {!pending.length&&<p className="evidenceExplanation">{planLoading?'Loading your steps…':'No steps yet.'}</p>}
      </section>
      <section className="card homeJobs"><div className="cardHead"><div><span className="kicker">Top matches</span><h2>Roles for you</h2></div><button className="textBtn" onClick={()=>setActiveTab('Jobs')}>All jobs<ChevronRight size={14}/></button></div>
        <JobResults jobs={jobs} limit={3}/>
      </section>
    </div>
  </div>
}
